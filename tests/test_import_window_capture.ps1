# Harmless GUI integration checks; never launches LOVE or touches existing run logs.
[CmdletBinding()]
param([string]$LogRoot = 'C:\gen1recomp\AItest\ROM-TestLogs')
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\tools\run_italian_import.ps1') -Action SelfTest
$testDir = Join-Path $LogRoot ('runner-selftests\capture-' + [guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($testDir)
"SELFTEST_DIR=$testDir"
$fixtureCode = @'
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
$form = [Windows.Forms.Form]::new()
$form.Text = 'GEN1RECOMP screenshot self-test ' + $PID
$form.Width = 400
$form.Height = 160
$label = [Windows.Forms.Label]::new()
$label.Text = 'Disposable runner test window. No user document.'
$label.AutoSize = $true
$label.Left = 15
$label.Top = 30
$form.Controls.Add($label)
$form.Show()
[Windows.Forms.Application]::DoEvents()
[IO.File]::WriteAllText((Join-Path $env:CAPTURE_TEST_DIR 'ready.txt'), [string]$form.Handle.ToInt64())
try {
  while (-not $form.IsDisposed) {
    if ($env:CAPTURE_TEST_BLOCKED -ne '1' -or (Test-Path (Join-Path $env:CAPTURE_TEST_DIR 'release.txt'))) {
      [Windows.Forms.Application]::DoEvents()
    }
    Start-Sleep -Milliseconds 20
  }
} finally { $form.Dispose() }
'@
function Start-Fixture([string]$Name, [bool]$Blocked) {
  $dir = Join-Path $testDir $Name
  [void][IO.Directory]::CreateDirectory($dir)
  $info = [Diagnostics.ProcessStartInfo]::new((Join-Path $PSHOME 'pwsh.exe'))
  $info.UseShellExecute = $false
  $info.CreateNoWindow = $true
  $info.Environment['CAPTURE_TEST_DIR'] = $dir
  $info.Environment['CAPTURE_TEST_BLOCKED'] = if ($Blocked) { '1' } else { '0' }
  foreach ($arg in @('-NoProfile', '-STA', '-EncodedCommand', [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($fixtureCode)))) {
    $info.ArgumentList.Add($arg)
  }
  $p = [Diagnostics.Process]::Start($info)
  $fixture = [pscustomobject]@{ Process=$p; Dir=$dir; Handle=[IntPtr]::Zero }
  $script:fixtures.Add($fixture)
  $deadline = [DateTime]::UtcNow.AddSeconds(20)
  $ready = Join-Path $dir 'ready.txt'
  while (-not (Test-Path $ready)) {
    if ($p.HasExited -or [DateTime]::UtcNow -gt $deadline) { throw "Fixture did not become ready: $Name PID=$($p.Id)" }
    Start-Sleep -Milliseconds 50
  }
  $fixture.Handle = [IntPtr]::new([long](Get-Content $ready -Raw))
  return $fixture
}
$script:fixtures = [Collections.Generic.List[object]]::new()
try {
  $normal = Start-Fixture 'responsive' $false
  $blocked = Start-Fixture 'blocked' $true
  $dir = $normal.Dir
  [IO.File]::WriteAllText((Join-Path $dir 'stdout.log'), 'Original test stdout')
  [IO.File]::WriteAllText((Join-Path $dir 'stderr.log'), 'Original test stderr')
  [IO.File]::WriteAllText((Join-Path $dir 'exit-code.txt'), '1')
  $hashes = @{}
  foreach ($name in @('stdout.log','stderr.log','exit-code.txt')) { $hashes[$name] = (Get-FileHash (Join-Path $dir $name)).Hash }
  $result = Invoke-BoundedWindowCapture $normal.Process $normal.Handle $dir
  if ($result -ne 'CAPTURED') { throw "Responsive PrintWindow capture failed: $result" }
  $png = Get-ChildItem $dir -Filter '*.png' | Select-Object -First 1
  $image = [Drawing.Image]::FromFile($png.FullName)
  try { if ($image.Width -le 0 -or $image.Height -le 0) { throw 'Invalid screenshot dimensions' } }
  finally { $image.Dispose() }
  'REAL_CAPTURE=PASS (PrintWindow, valid PNG)'
  # PrintWindow can use the compositor even when a window does not pump messages.
  # Inject a non-returning child at the same process boundary to test the watchdog deterministically.
  $originalHelper = $script:CaptureHelper
  $fixtureHelper = Join-Path $blocked.Dir 'blocked-capture-fixture.ps1'
  [IO.File]::WriteAllText($fixtureHelper, '[IO.File]::WriteAllText((Join-Path $PSScriptRoot "blocked-entered.txt"), "SIMULATED_BLOCKED_CAPTURE"); [Threading.Thread]::Sleep([Threading.Timeout]::Infinite)')
  $clock = [Diagnostics.Stopwatch]::StartNew()
  try {
    $script:CaptureHelper = $fixtureHelper
    $result = Invoke-BoundedWindowCapture $blocked.Process $blocked.Handle $blocked.Dir
  } finally { $script:CaptureHelper = $originalHelper; $clock.Stop() }
  if ($result -ne 'TIMEOUT' -or $clock.Elapsed.TotalSeconds -gt 12) { throw "Blocked capture was not bounded: $result $($clock.Elapsed)" }
  if (-not (Test-Path (Join-Path $blocked.Dir 'blocked-entered.txt'))) { throw 'Blocked fixture did not execute' }
  if ($blocked.Process.HasExited -or $normal.Process.HasExited) { throw 'Capture terminated a fixture process' }
  $fields = Get-RunFields (Join-Path $blocked.Dir 'status.txt')
  if (Get-Process -Id ([int]($fields['SCREENSHOT_HELPER_PID'] -split ' ')[0]) -ErrorAction SilentlyContinue) {
    throw 'Blocked screenshot helper is still alive'
  }
  "SIMULATED_BLOCKED_CAPTURE=PASS SCREENSHOT_TIMEOUT ELAPSED_SECONDS=$($clock.Elapsed.TotalSeconds) TARGET_STILL_ALIVE=True"
  if ([ItalianImportNative]::CloseOwnedWindow($normal.Handle, $blocked.Process.Id)) { throw 'Foreign window accepted' }
  if ($normal.Process.HasExited) { throw 'Foreign window was closed' }
  if (Capture-AndCloseErrorWindow $normal.Process $normal.Dir) { throw 'Window closed without recorded LOVE identity and error' }
  'FOREIGN_WINDOW_AND_MISSING_EVIDENCE=PASS (close refused)'
  foreach ($name in $hashes.Keys) {
    if ((Get-FileHash (Join-Path $dir $name)).Hash -ne $hashes[$name]) { throw "Original log changed: $name" }
  }
  'ORIGINAL_LOGS_AND_EXIT_CODE=PASS (hashes unchanged)'
} finally {
  foreach ($fixture in $script:fixtures) {
    [IO.File]::WriteAllText((Join-Path $fixture.Dir 'release.txt'), 'Allow fixture UI message processing')
    if (-not $fixture.Process.HasExited -and $fixture.Handle -ne [IntPtr]::Zero) {
      [void][ItalianImportNative]::CloseOwnedWindow($fixture.Handle, $fixture.Process.Id)
    }
    if (-not $fixture.Process.WaitForExit(5000)) { throw "Fixture remains active; no force termination: PID=$($fixture.Process.Id)" }
    $fixture.Process.Dispose()
  }
}
'FIXTURE_NORMAL_CLOSE=PASS'
'SCREENSHOT_SELFTEST=PASS'
