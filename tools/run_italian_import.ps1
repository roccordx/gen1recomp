[CmdletBinding()]
param(
  [ValidateSet('Start', 'Status', 'Wait', 'Worker', 'SelfTest', 'Preflight', 'RegisterTransferred', 'ReconcileLocal')]
  [string]$Action = 'Start',
  [string]$RunId,
  [string]$RunDir,
  [string]$ExpectedStatusHash,
  [string]$TransferReason,
  [ValidateRange(1, 30)]
  [int]$PollSeconds = 2
)

$ErrorActionPreference = 'Stop'
$script:Repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$script:LogRoot = 'C:\gen1recomp\AItest\ROM-TestLogs'
$script:LoveExe = 'C:\Program Files\LOVE\lovec.exe'
$script:Identity = 'test-italian-run'
$script:AppData = Join-Path $script:Repo 'test-italian-run\cache-temp'
$script:Utf8NoBom = [System.Text.UTF8Encoding]::new($false)
$script:CaptureHelper = Join-Path $PSScriptRoot 'capture_import_window.ps1'
$script:ImportMutexName = 'Global\Gen1RecompItalianImport'
$machineGuid = (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Cryptography' -Name MachineGuid).MachineGuid
$script:MachineId = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($machineGuid)))
$script:Computer = [Environment]::MachineName

# Classifications are observations, never replacements for recorded test states.
function Get-RunClassification($Fields, [bool]$Transferred, [string]$Worker, [string]$Love) {
  if ($Fields['MACHINE_ID'] -eq $script:MachineId -and
      ($Worker -eq 'ACTIVE' -or $Love -eq 'ACTIVE')) { return 'ACTIVE_LOCAL' }
  if ($Fields['STATE'] -in @('FINISHED', 'REFUSED_ACTIVE_IMPORT')) { return 'HISTORICAL_CONCLUDED' }
  if ($Fields['MACHINE_ID'] -and $Fields['MACHINE_ID'] -ne $script:MachineId) { return 'STALE_REMOTE' }
  if (-not $Fields['MACHINE_ID'] -and $Transferred) { return 'HISTORICAL_UNRESOLVED_REMOTE' }
  return 'LOCAL_OR_UNKNOWN_UNRESOLVED'
}

function Get-LocalReconciliationPath([string]$Dir) {
  Join-Path $script:LogRoot ("reconciliation-{0}-{1}.json" -f (Split-Path $Dir -Leaf), $script:MachineId)
}

function Get-OriginalLogHashes([string]$Dir) {
  $hashes = @{}
  foreach ($name in @('status.txt', 'stdout.log', 'stderr.log')) {
    $path = Join-Path $Dir $name
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Original run file missing: $path" }
    $hashes[$name] = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
  }
  return $hashes
}

function Test-LocalReconciliation($Note, [string]$Dir, $Fields, [string]$Worker, [string]$Love) {
  if (-not $Note -or $Note.RunId -ne (Split-Path $Dir -Leaf) -or
      $Note.MachineId -ne $script:MachineId -or $Fields['MACHINE_ID'] -ne $script:MachineId -or
      $Fields['STATE'] -ne 'RUNNING' -or $Note.OriginalState -ne 'RUNNING' -or
      $Note.OperationalState -ne 'INACTIVE' -or
      $Note.DiagnosticOutcome -ne 'INTERRUPTED_UNVERIFIED' -or
      $Worker -notin @('NOT_VISIBLE_OR_ABSENT', 'PID_REUSED') -or
      $Love -notin @('NOT_VISIBLE_OR_ABSENT', 'PID_REUSED')) { return $false }
  try {
    $hashes = Get-OriginalLogHashes $Dir
    foreach ($name in $hashes.Keys) {
      if ($Note.OriginalHashes.$name -ne $hashes[$name]) { return $false }
    }
  } catch { return $false }
  return $true
}

function Get-ClassificationPath([string]$Dir) {
  Join-Path $script:LogRoot ("classification-{0}-{1}.json" -f (Split-Path $Dir -Leaf), $script:MachineId)
}

function Observe-Run([string]$Dir) {
  $path = Join-Path $Dir 'status.txt'
  $f = Get-RunFields $path
  $transferred = $false
  $note = Get-ClassificationPath $Dir
  if (Test-Path -LiteralPath $note) {
    $n = Read-SharedText $note | ConvertFrom-Json
    $transferred = $n.MachineId -eq $script:MachineId -and $n.RunId -eq (Split-Path $Dir -Leaf) -and
      $n.Classification -eq 'HISTORICAL_UNRESOLVED_REMOTE' -and
      $n.StatusHash -eq (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
  }
  $w = Get-ProcessState $f['WORKER_PID'] 'pwsh' $f['WORKER_STARTED'] $f['WORKER_EXE'] $f['WORKER_SESSION']
  $l = Get-ProcessState $f['LOVE_PID'] 'lovec' $f['LOVE_STARTED'] $f['LOVE_EXE'] $f['LOVE_SESSION']
  $localNote = Get-LocalReconciliationPath $Dir
  if (Test-Path -LiteralPath $localNote -PathType Leaf) {
    try {
      $reconciled = Read-SharedText $localNote | ConvertFrom-Json
      if (Test-LocalReconciliation $reconciled $Dir $f $w $l) { return 'HISTORICAL_INTERRUPTED_LOCAL' }
    } catch { } # A damaged or stale note cannot release the import lock.
  }
  Get-RunClassification $f $transferred $w $l
}

function Enter-ImportGate([bool]$WaitForGate) {
  $mutex = [Threading.Mutex]::new($false, $script:ImportMutexName)
  $held = $false
  $file = $null
  try {
    try { $held = if ($WaitForGate) { $mutex.WaitOne() } else { $mutex.WaitOne(0) } }
    catch [Threading.AbandonedMutexException] { $held = $true }
    if (-not $held) { throw 'Another import operation holds the machine mutex' }
    $file = [IO.File]::Open((Join-Path $script:LogRoot 'italian-import.active.lock'),
      [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
    return [pscustomobject]@{ Mutex=$mutex; File=$file }
  } catch {
    if ($file) { $file.Dispose() }
    if ($held) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
    throw
  }
}

function Exit-ImportGate($Gate) {
  if ($Gate) {
    $Gate.File.Dispose()
    $Gate.Mutex.ReleaseMutex()
    $Gate.Mutex.Dispose()
  }
}

function Assert-NoLocalImport {
  # Access denied is a blocking error, not evidence that no process exists.
  $processes = @(Get-CimInstance Win32_Process -ErrorAction Stop)
  $busy = @($processes | Where-Object {
    $_.ProcessId -ne $PID -and
    ($_.Name -in @('love.exe', 'lovec.exe') -or
     ($_.Name -in @('pwsh.exe', 'powershell.exe') -and
      $_.CommandLine -match 'run[-_]italian[-_]import\.ps1' -and
      $_.CommandLine -match '(?i)-Action\s+Worker'))
  })
  if ($busy.Count) { throw "Local import/process present; refusing duplicate: $($busy.ProcessId -join ',')" }
}

function Assert-Ready([string]$ExcludeRunId = '') {
  Assert-NoLocalImport
  $blocked = @()
  foreach ($d in Get-ChildItem -LiteralPath $script:LogRoot -Directory) {
    if (-not (Test-Path -LiteralPath (Join-Path $d.FullName 'status.txt'))) { continue }
    if ($ExcludeRunId -and $d.Name -eq $ExcludeRunId) {
      $self = Get-RunFields (Join-Path $d.FullName 'status.txt')
      if ($self['RUN_ID'] -ne $ExcludeRunId -or $self['MACHINE_ID'] -ne $script:MachineId -or
          $self['WORKER_PID'] -ne [string]$PID -or
          (Get-ProcessState $self['WORKER_PID'] 'pwsh' $self['WORKER_STARTED'] $self['WORKER_EXE'] $self['WORKER_SESSION']) -ne 'ACTIVE') {
        throw 'Worker identity does not match the newly created run'
      }
      continue
    }
    $classification = Observe-Run $d.FullName
    if ($classification -in @('ACTIVE_LOCAL', 'LOCAL_OR_UNKNOWN_UNRESOLVED')) {
      $blocked += "$($d.Name): $classification"
    }
  }
  if ($blocked.Count) { throw "Unresolved local import records: $($blocked -join '; ')" }
}

function Assert-HarnessSource {
  if (-not (Test-Path -LiteralPath $script:CaptureHelper -PathType Leaf)) {
    throw 'Screenshot helper is missing: capture_import_window.ps1'
  }
  $source = Join-Path $script:Repo $script:Identity
  if (-not (Test-Path -LiteralPath (Join-Path $source 'main.lua') -PathType Leaf)) {
    throw "LÖVE source has no main.lua: $source"
  }
  foreach ($name in @('assets', 'tools')) {
    $link = Join-Path $source $name
    $expected = Join-Path $script:Repo $name
    $item = Get-Item -LiteralPath $link -ErrorAction Stop
    if ($item.LinkType -ne 'Junction' -or
        [IO.Path]::GetFullPath([string]$item.Target) -ine [IO.Path]::GetFullPath($expected)) {
      throw "Harness $name junction does not target the canonical project directory: $link"
    }
  }
  foreach ($relative in @('assets\logo\logo.png', 'assets\logo\bcg.png',
                         'tools\rom_variants\red_ita_manifest.json')) {
    if (-not (Test-Path -LiteralPath (Join-Path $source $relative) -PathType Leaf)) {
      throw "Required file is not visible from LÖVE source: $relative"
    }
  }
  foreach ($relative in @('red-ita.gb', 'src\import\RomImporter.lua',
                         'src\import\RomManifest.lua', 'src\core\GameVersion.lua',
                         'src\link\Json.lua', 'tests\test_import_italian_rom.lua')) {
    if (-not (Test-Path -LiteralPath (Join-Path $script:Repo $relative) -PathType Leaf)) {
      throw "Required project file is missing: $relative"
    }
  }
}

function Add-Line([string]$Path, [string]$Line) {
  [IO.File]::AppendAllText($Path, $Line + [Environment]::NewLine, $script:Utf8NoBom)
}

function Read-SharedText([string]$Path) {
  if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return '' }
  $stream = [IO.File]::Open($Path, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::ReadWrite)
  try {
    $reader = [IO.StreamReader]::new($stream, [Text.Encoding]::UTF8, $true)
    try { return $reader.ReadToEnd() } finally { $reader.Dispose() }
  } finally { $stream.Dispose() }
}

function Get-RunFields([string]$Path) {
  $fields = @{}
  foreach ($line in (Read-SharedText $Path) -split "`r?`n") {
    $at = $line.IndexOf('=')
    if ($at -gt 0) { $fields[$line.Substring(0, $at)] = $line.Substring($at + 1) }
    elseif ($line -in @('RUNNING', 'FINISHED')) { $fields['STATE'] = $line }
  }
  return $fields
}

function Get-ProcessState([string]$IdText, [string]$ExpectedName, [string]$StartText, [string]$ExpectedPath, [string]$ExpectedSession) {
  if (-not $IdText -or $IdText -notmatch '^\d+$') { return 'NOT_RECORDED' }
  try { $p = Get-Process -Id ([int]$IdText) -ErrorAction Stop }
  catch {
    if ($_.FullyQualifiedErrorId -match 'CannotFindProcess|NoProcessFound') { return 'NOT_VISIBLE_OR_ABSENT' }
    return 'UNKNOWN'
  }
  if ($ExpectedName -and $p.ProcessName -ine $ExpectedName) { return 'PID_REUSED' }
  if ($StartText) {
    try {
      $expected = [DateTimeOffset]::Parse($StartText).UtcDateTime
      if ([Math]::Abs(($p.StartTime.ToUniversalTime() - $expected).TotalMilliseconds) -gt 1) { return 'PID_REUSED' }
    } catch { return 'UNKNOWN' }
  }
  if (-not $StartText -or -not $ExpectedPath -or -not $ExpectedSession) { return 'UNKNOWN' }
  try {
    if ($p.Path -ine $ExpectedPath -or [string]$p.SessionId -ne $ExpectedSession) { return 'PID_REUSED' }
  } catch { return 'UNKNOWN' }
  return 'ACTIVE'
}

function Invoke-LocalReconciliation([string]$Id) {
  if ($Id -notmatch '^italian-[A-Za-z0-9-]+$') { throw 'Invalid run ID' }
  $gate = Enter-ImportGate $false
  try {
    $dir = Join-Path $script:LogRoot $Id
    if (-not (Test-Path -LiteralPath $dir -PathType Container)) { throw "Run not found: $Id" }
    $statusPath = Join-Path $dir 'status.txt'
    $fields = Get-RunFields $statusPath
    if ($fields['RUN_ID'] -ne $Id -or $fields['MACHINE_ID'] -ne $script:MachineId -or
        $fields['STATE'] -ne 'RUNNING') { throw 'Only an unresolved run from this machine can be reconciled' }
    foreach ($key in @('WORKER_PID', 'WORKER_STARTED', 'WORKER_EXE', 'WORKER_SESSION',
                       'LOVE_PID', 'LOVE_STARTED', 'LOVE_EXE', 'LOVE_SESSION')) {
      if ([string]::IsNullOrWhiteSpace($fields[$key])) { throw "Incomplete process identity: $key" }
    }
    if ($fields['LOVE_EXE'] -ine $script:LoveExe -or
        $fields['WORKER_EXE'] -ine (Join-Path $PSHOME 'pwsh.exe')) {
      throw 'Recorded executable identity does not match this runner'
    }
    $worker = Get-ProcessState $fields['WORKER_PID'] 'pwsh' $fields['WORKER_STARTED'] $fields['WORKER_EXE'] $fields['WORKER_SESSION']
    $love = Get-ProcessState $fields['LOVE_PID'] 'lovec' $fields['LOVE_STARTED'] $fields['LOVE_EXE'] $fields['LOVE_SESSION']
    if ($worker -notin @('NOT_VISIBLE_OR_ABSENT', 'PID_REUSED') -or
        $love -notin @('NOT_VISIBLE_OR_ABSENT', 'PID_REUSED')) {
      throw "Recorded process remains active or uncertain: worker=$worker LOVE=$love"
    }
    # An inaccessible process list, any other import worker or any LOVE process blocks recovery.
    Assert-NoLocalImport
    $notePath = Get-LocalReconciliationPath $dir
    if (Test-Path -LiteralPath $notePath) {
      $existing = Read-SharedText $notePath | ConvertFrom-Json
      if (-not (Test-LocalReconciliation $existing $dir $fields $worker $love)) {
        throw 'Existing local reconciliation note is invalid; manual review required'
      }
      "RECONCILIATION=ALREADY_RECORDED"
      "CLASSIFICATION=$(Observe-Run $dir)"
      "RECONCILIATION_FILE=$notePath"
      return
    }
    $hashes = Get-OriginalLogHashes $dir
    $summary = Get-TestSummary $dir
    if ($summary.Test -ne 'NOT_REPORTED' -or $summary.Marker -or
        (Test-Path -LiteralPath (Join-Path $dir 'exit-code.txt'))) {
      throw 'Run has result evidence; interrupted classification requires manual review'
    }
    $data = [ordered]@{
      RunId=$Id; MachineId=$script:MachineId; Computer=$script:Computer
      OriginalState=$fields['STATE']; OperationalState='INACTIVE'
      DiagnosticOutcome='INTERRUPTED_UNVERIFIED'
      WorkerProcess=$worker; LoveProcess=$love
      WorkerPid=$fields['WORKER_PID']; LovePid=$fields['LOVE_PID']
      LastHeartbeat=$fields['HEARTBEAT']; RecordedAt=[DateTimeOffset]::Now.ToString('o')
      OriginalHashes=$hashes
    } | ConvertTo-Json -Depth 4
    $stream = [IO.File]::Open($notePath, [IO.FileMode]::CreateNew,
      [IO.FileAccess]::Write, [IO.FileShare]::Read)
    try { $bytes = $script:Utf8NoBom.GetBytes($data); $stream.Write($bytes, 0, $bytes.Length) }
    finally { $stream.Dispose() }
    "RECONCILIATION=RECORDED"
    "CLASSIFICATION=$(Observe-Run $dir)"
    "RECONCILIATION_FILE=$notePath"
  } finally { Exit-ImportGate $gate }
}

function Get-TestSummary([string]$Dir) {
  $stdout = Read-SharedText (Join-Path $Dir 'stdout.log')
  $stderr = Read-SharedText (Join-Path $Dir 'stderr.log')
  $combined = $stdout + "`n" + $stderr
  $testStatus = if ($combined -match 'TEST A:\s*PASS') { 'PASS' }
    elseif ($combined -match 'TEST A FAIL') { 'FAIL' } else { 'NOT_REPORTED' }
  $errorLine = @(Get-FailureLines $combined | Select-Object -First 1)
  $errorPhase = Get-ErrorPhase $combined $errorLine
  $lastText = @($stdout -split "`r?`n" | Where-Object { $_ -match '\[ITALIAN TEXT\] end .*result=' } | Select-Object -Last 1)
  $fields = Get-RunFields (Join-Path $Dir 'status.txt')
  $marker = $fields['MARKER_PATH']
  if (-not $marker) { $marker = Join-Path $script:AppData 'LOVE\test-italian-run\red_ita\rom-cache.complete' }
  [pscustomobject]@{
    Test = $testStatus
    Error = if ($errorLine.Count) { $errorLine[0] } else { '' }
    ErrorPhase = $errorPhase
    LastText = if ($lastText.Count) { $lastText[0] } else { '' }
    Marker = (Test-Path -LiteralPath $marker -PathType Leaf)
    Fields = $fields
  }
}

function Show-RunStatus([string]$Dir) {
  if (-not (Test-Path -LiteralPath $Dir -PathType Container)) { throw "Run directory not found: $Dir" }
  $statusPath = Join-Path $Dir 'status.txt'
  $f = Get-RunFields $statusPath
  $loveState = Get-ProcessState $f['LOVE_PID'] 'lovec' $f['LOVE_STARTED'] $f['LOVE_EXE'] $f['LOVE_SESSION']
  $workerState = Get-ProcessState $f['WORKER_PID'] 'pwsh' $f['WORKER_STARTED'] $f['WORKER_EXE'] $f['WORKER_SESSION']
  $summary = Get-TestSummary $Dir
  $state = $f['STATE']
  $observed = $state
  $activity = @('status.txt', 'stdout.log', 'stderr.log' | ForEach-Object {
    $p = Join-Path $Dir $_
    if (Test-Path -LiteralPath $p -PathType Leaf) { (Get-Item -LiteralPath $p).LastWriteTimeUtc }
  } | Sort-Object -Descending | Select-Object -First 1)
  $activityAge = if ($activity.Count) { [Math]::Round(([DateTime]::UtcNow - $activity[0]).TotalSeconds, 1) } else { 'NA' }
  if ($state -in @('START_REQUESTED', 'RUNNING', 'ERROR_RECORDED', 'ERROR_WINDOW_CLOSE_REQUESTED') -and
      $loveState -eq 'NOT_VISIBLE_OR_ABSENT' -and $workerState -eq 'NOT_VISIBLE_OR_ABSENT') {
    $observed = 'RECORDED_RUNNING_PROCESSES_NOT_VISIBLE_TO_THIS_QUERY'
  }
  "RUN_ID=$($f['RUN_ID'])"
  "RECORDED_STATE=$state"
  "CLASSIFICATION=$(Observe-Run $Dir)"
  "OBSERVED_STATE=$observed"
  "WORKER_PROCESS=$workerState PID=$($f['WORKER_PID'])"
  "LOVE_PROCESS=$loveState PID=$($f['LOVE_PID'])"
  "EXIT_CODE=$($f['LOVE_EXIT_CODE'])"
  "TEST_A=$($summary.Test)"
  "LAST_TEXT_DIAGNOSTIC=$($summary.LastText)"
  "FIRST_ERROR_EVIDENCE=$($summary.Error)"
  "ERROR_PHASE=$($summary.ErrorPhase)"
  "ROM_CACHE_COMPLETE=$($summary.Marker)"
  "LAST_LOG_ACTIVITY_AGE_SECONDS=$activityAge"
  "RUN_DIR=$Dir"
  '--- STDOUT TAIL ---'
  ((Read-SharedText (Join-Path $Dir 'stdout.log')) -split "`r?`n" | Select-Object -Last 12)
  '--- STDERR TAIL ---'
  ((Read-SharedText (Join-Path $Dir 'stderr.log')) -split "`r?`n" | Select-Object -Last 12)
}

function Add-NativeWindowType {
  if ('ItalianImportNative' -as [type]) { return }
  Add-Type -AssemblyName System.Drawing
  Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;
public static class ItalianImportNative {
  public struct WindowInfo { public IntPtr Handle; public int ProcessId; public string Title; public string ClassName; public bool Visible; }
  public struct RECT { public int Left, Top, Right, Bottom; }
  private delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
  [DllImport("user32.dll")] private static extern bool EnumWindows(EnumWindowsProc callback, IntPtr extra);
  [DllImport("user32.dll")] private static extern uint GetWindowThreadProcessId(IntPtr hWnd, out int processId);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] private static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int max);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] private static extern int GetClassName(IntPtr hWnd, StringBuilder text, int max);
  [DllImport("user32.dll")] private static extern bool IsWindowVisible(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);
  [DllImport("user32.dll")] private static extern bool PostMessage(IntPtr hWnd, uint message, IntPtr wParam, IntPtr lParam);
  public static WindowInfo[] GetWindows(int targetPid) {
    var rows = new List<WindowInfo>();
    EnumWindows((h, x) => {
      int pid; GetWindowThreadProcessId(h, out pid);
      if (pid == targetPid) {
        var title = new StringBuilder(1024); GetWindowText(h, title, title.Capacity);
        var cls = new StringBuilder(256); GetClassName(h, cls, cls.Capacity);
        rows.Add(new WindowInfo { Handle=h, ProcessId=pid, Title=title.ToString(), ClassName=cls.ToString(), Visible=IsWindowVisible(h) });
      }
      return true;
    }, IntPtr.Zero);
    return rows.ToArray();
  }
  public static bool CloseOwnedWindow(IntPtr h, int expectedPid) {
    int pid; GetWindowThreadProcessId(h, out pid);
    return expectedPid > 0 && pid == expectedPid && PostMessage(h, 0x0010, IntPtr.Zero, IntPtr.Zero);
  }
}
'@
}

function Get-FailureLines([string]$All) {
  @($All -split "`r?`n" | Where-Object {
    $_ -match '^Error:\s+|\[TEST A FAIL\]|unsupported text command|missing dynamic text substitution|import coroutine error:'
  })
}

function Get-ErrorPhase([string]$Output, [array]$ErrorLines) {
  if (-not $ErrorLines.Count) { return 'NONE' }
  if ($Output -match 'ROM import metadata is missing|RomManifest\.lua:') { return 'MANIFEST_LOADING' }
  if ($Output -match '\[ITALIAN TEXT\] begin|unsupported text command|Running import coroutine') {
    return 'ROM_EXTRACTION'
  }
  if ($Output -match 'Creating RomImporter') { return 'IMPORTER_INITIALIZATION' }
  return 'LOVE_INITIALIZATION'
}

function Get-FailureEvidence([string]$Dir) {
  $all = (Read-SharedText (Join-Path $Dir 'stdout.log')) + "`n" + (Read-SharedText (Join-Path $Dir 'stderr.log'))
  return @(Get-FailureLines $all | Select-Object -First 1)
}

function Invoke-BoundedWindowCapture($Process, [IntPtr]$Handle, [string]$Dir, [int]$TimeoutMilliseconds = 5000) {
  # Only this disposable child can block in PrintWindow. Never kill the test process.
  $capture = Join-Path $Dir ("love-error-{0}.png" -f [guid]::NewGuid().ToString('N'))
  $info = [Diagnostics.ProcessStartInfo]::new((Join-Path $PSHOME 'pwsh.exe'))
  $info.UseShellExecute = $false
  $info.CreateNoWindow = $true
  $info.RedirectStandardOutput = $true
  $info.RedirectStandardError = $true
  foreach ($arg in @('-NoProfile', '-File', $script:CaptureHelper,
      '-TargetPid', [string]$Process.Id, '-TargetStarted', $Process.StartTime.ToUniversalTime().ToString('o'),
      '-TargetPath', $Process.Path, '-TargetSession', [string]$Process.SessionId,
      '-WindowHandle', [string]$Handle.ToInt64(), '-OutputPath', $capture)) {
    $info.ArgumentList.Add($arg)
  }
  $child = $null
  try {
    $child = [Diagnostics.Process]::Start($info)
    $outTask = $child.StandardOutput.ReadToEndAsync()
    $errTask = $child.StandardError.ReadToEndAsync()
    Add-Line (Join-Path $Dir 'status.txt') "SCREENSHOT_HELPER_PID=$($child.Id) STARTED=$($child.StartTime.ToUniversalTime().ToString('o'))"
    if (-not $child.WaitForExit($TimeoutMilliseconds)) {
      Add-Line (Join-Path $Dir 'status.txt') "SCREENSHOT_TIMEOUT LIMIT_MS=$TimeoutMilliseconds HELPER_PID=$($child.Id)"
      # Process owns the original child handle, so a reused PID is never selected.
      try {
        $child.Kill()
        if (-not $child.WaitForExit(2000)) {
          Add-Line (Join-Path $Dir 'status.txt') 'SCREENSHOT_HELPER_EXIT_UNCONFIRMED'
        }
      } catch { Add-Line (Join-Path $Dir 'status.txt') "SCREENSHOT_HELPER_STOP_EXCEPTION=$($_.Exception.Message)" }
      return 'TIMEOUT'
    }
    Add-Line (Join-Path $Dir 'status.txt') "SCREENSHOT_HELPER_EXIT_CODE=$($child.ExitCode)"
    if ($outTask.IsCompletedSuccessfully) { Add-Line (Join-Path $Dir 'status.txt') "SCREENSHOT_HELPER_OUTPUT=$($outTask.Result.Trim())" }
    if ($errTask.IsCompletedSuccessfully -and $errTask.Result) { Add-Line (Join-Path $Dir 'status.txt') "SCREENSHOT_HELPER_ERROR=$($errTask.Result.Trim())" }
    if ($child.ExitCode -eq 0 -and (Test-Path -LiteralPath $capture -PathType Leaf)) {
      Add-Line (Join-Path $Dir 'status.txt') "ERROR_WINDOW_CAPTURE=$capture"
      return 'CAPTURED'
    }
    return 'FAILED'
  } catch {
    Add-Line (Join-Path $Dir 'status.txt') "SCREENSHOT_EXCEPTION=$($_.Exception.Message)"
    return 'FAILED'
  } finally {
    if ($child) {
      try {
        if (-not $child.HasExited) { $child.Kill(); [void]$child.WaitForExit(2000) }
      } catch { Add-Line (Join-Path $Dir 'status.txt') "SCREENSHOT_HELPER_CLEANUP_EXCEPTION=$($_.Exception.Message)" }
      $child.Dispose()
    }
  }
}

function Test-RecordedErrorProcess($Process, [string]$Dir) {
  $f = Get-RunFields (Join-Path $Dir 'status.txt')
  if ($f['LOVE_PID'] -ne [string]$Process.Id -or $f['LOVE_EXE'] -ine $script:LoveExe -or
      $f['MACHINE_ID'] -ne $script:MachineId -or @(Get-FailureEvidence $Dir).Count -eq 0) { return $false }
  $state = Get-ProcessState $f['LOVE_PID'] 'lovec' $f['LOVE_STARTED'] $f['LOVE_EXE'] $f['LOVE_SESSION']
  return $state -eq 'ACTIVE'
}

function Capture-AndCloseErrorWindow($Process, [string]$Dir) {
  if (-not (Test-RecordedErrorProcess $Process $Dir)) { return $false }
  Add-NativeWindowType
  $Process.Refresh()
  $all = @([ItalianImportNative]::GetWindows($Process.Id))
  $visible = @($all | Where-Object { $_.Visible })
  foreach ($w in $all) {
    Add-Line (Join-Path $Dir 'status.txt') "ERROR_WINDOW PID=$($w.ProcessId) HANDLE=$($w.Handle) VISIBLE=$($w.Visible) CLASS=$($w.ClassName) TITLE=$($w.Title)"
  }
  $target = $null
  if ($Process.MainWindowHandle -ne [IntPtr]::Zero) {
    $target = $visible | Where-Object { $_.Handle -eq $Process.MainWindowHandle } | Select-Object -First 1
  }
  if (-not $target -and $visible.Count -eq 1) { $target = $visible[0] }
  if (-not $target) {
    return $false
  }
  Add-Line (Join-Path $Dir 'status.txt') "ERROR_WINDOW_EVIDENCE=$(@(Get-FailureEvidence $Dir)[0])"
  $captureResult = Invoke-BoundedWindowCapture $Process $target.Handle $Dir
  Add-Line (Join-Path $Dir 'status.txt') "SCREENSHOT_RESULT=$captureResult"
  # Revalidate after the helper wait, including handle ownership and class.
  if (-not (Test-RecordedErrorProcess $Process $Dir)) { return $false }
  $current = @([ItalianImportNative]::GetWindows($Process.Id) | Where-Object {
    $_.Handle -eq $target.Handle -and $_.Visible -and $_.ClassName -eq $target.ClassName
  })
  if ($current.Count -ne 1) { return $false }
  $closed = [ItalianImportNative]::CloseOwnedWindow($target.Handle, $Process.Id)
  Add-Line (Join-Path $Dir 'status.txt') "ERROR_WINDOW_WM_CLOSE_POSTED=$closed HANDLE=$($target.Handle) PID=$($Process.Id)"
  if ($closed) { Add-Line (Join-Path $Dir 'status.txt') 'STATE=ERROR_WINDOW_CLOSE_REQUESTED' }
  return $closed
}

function Start-Worker([string]$Dir) {
  if (-not (Test-Path -LiteralPath $script:Repo -PathType Container)) { throw "Repository not found: $script:Repo" }
  if (-not (Test-Path -LiteralPath $script:LogRoot -PathType Container)) { throw "Persistent log directory not found: $script:LogRoot" }
  if (-not (Test-Path -LiteralPath $script:LoveExe -PathType Leaf)) { throw "LOVE executable not found: $script:LoveExe" }
  Assert-Ready
  Assert-HarnessSource
  $runId = Split-Path $Dir -Leaf
  [IO.Directory]::CreateDirectory($Dir) | Out-Null
  $status = Join-Path $Dir 'status.txt'
  Add-Line $status "RUN_ID=$runId"
  Add-Line $status "MACHINE_ID=$script:MachineId"
  Add-Line $status "COMPUTER_NAME=$script:Computer"
  Add-Line $status "CREATED=$([DateTimeOffset]::Now.ToString('o'))"
  Add-Line $status 'STATE=START_REQUESTED'
  Add-Line $status "REPO=$script:Repo"
  Add-Line $status "LOVE_EXE=$script:LoveExe"
  $pwsh = Join-Path $PSHOME 'pwsh.exe'
  if (-not (Test-Path -LiteralPath $pwsh -PathType Leaf)) { throw "PowerShell 7 executable not found: $pwsh" }
  $args = '-NoProfile -File "{0}" -Action Worker -RunDir "{1}"' -f $PSCommandPath, $Dir
  $worker = Start-Process -FilePath $pwsh -ArgumentList $args -WorkingDirectory $script:Repo -WindowStyle Hidden -PassThru
  Add-Line $status "LAUNCHER_PID=$PID"
  Add-Line $status "WORKER_PID=$($worker.Id)"
  Add-Line $status "WORKER_STARTED=$($worker.StartTime.ToUniversalTime().ToString('o'))"
  Add-Line $status "WORKER_EXE=$pwsh"
  Add-Line $status "WORKER_SESSION=$($worker.SessionId)"
  "RUN_ID=$runId"
  "RUN_DIR=$Dir"
  "WORKER_PID=$($worker.Id)"
}

function Invoke-Worker([string]$Dir) {
  $status = Join-Path $Dir 'status.txt'
  $stdout = Join-Path $Dir 'stdout.log'
  $stderr = Join-Path $Dir 'stderr.log'
  $exitFile = Join-Path $Dir 'exit-code.txt'
  $exceptionFile = Join-Path $Dir 'powershell-exception.txt'
  $markerFile = Join-Path $Dir 'rom-cache-marker.txt'
  $gate = $null
  $process = $null
  $finished = $false
  try {
    # Start releases this gate after recording worker identity. Recheck all other
    # records while holding it, before the ROM process can be launched.
    $gate = Enter-ImportGate $true
    Assert-Ready (Split-Path $Dir -Leaf)
    Set-Location -LiteralPath $script:Repo
    $env:POKEPORT_NO_THREAD = '1'
    $env:POKEPORT_ITALIAN_IMPORT_DIAGNOSTICS = '1'
    $env:POKEPORT_IDENTITY = $script:Identity
    $env:APPDATA = $script:AppData
    [IO.Directory]::CreateDirectory($env:APPDATA) | Out-Null
    [IO.File]::WriteAllText($stdout, '', $script:Utf8NoBom)
    [IO.File]::WriteAllText($stderr, '', $script:Utf8NoBom)
    $marker = Join-Path $env:APPDATA 'LOVE\test-italian-run\red_ita\rom-cache.complete'
    Add-Line $status "APPDATA=$env:APPDATA"
    Add-Line $status "MARKER_PATH=$marker"
    Add-Line $status 'STATE=RUNNING'
    Add-Line $status "LOVE_START_REQUESTED=$([DateTimeOffset]::Now.ToString('o'))"
    $process = Start-Process -FilePath $script:LoveExe -ArgumentList $script:Identity -WorkingDirectory $script:Repo -WindowStyle Normal -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    $process.Refresh()
    Add-Line $status "LOVE_PID=$($process.Id)"
    Add-Line $status "LOVE_STARTED=$($process.StartTime.ToUniversalTime().ToString('o'))"
    Add-Line $status "LOVE_SESSION=$($process.SessionId)"
    $lastHeartbeat = [DateTimeOffset]::UtcNow
    $failureEvidence = $false
    $failureAt = $null
    $windowClosePosted = $false
    $lastWindowCheck = [DateTimeOffset]::MinValue
    $windowMissingLogged = $false
    while (-not $process.WaitForExit(500)) {
      if (-not $failureEvidence) {
        $evidence = @(Get-FailureEvidence $Dir)
        if ($evidence.Count) {
          Add-Line $status "TEST_ERROR_EVIDENCE=$($evidence[0])"
          Add-Line $status 'STATE=ERROR_RECORDED'
          $failureEvidence = $true
          $failureAt = [DateTimeOffset]::UtcNow
        }
      }
      if ($failureEvidence -and -not $windowClosePosted -and
          ([DateTimeOffset]::UtcNow - $lastWindowCheck).TotalSeconds -ge 1) {
        $lastWindowCheck = [DateTimeOffset]::UtcNow
        try {
          $windowClosePosted = Capture-AndCloseErrorWindow $process $Dir
          if (-not $windowClosePosted -and -not $windowMissingLogged -and
              ([DateTimeOffset]::UtcNow - $failureAt).TotalSeconds -ge 5) {
            Add-Line $status 'ERROR_WINDOW_NOT_CLOSED=No unique visible window owned by test PID; process remains running'
            $windowMissingLogged = $true
          }
        } catch { Add-Line $status "ERROR_WINDOW_HANDLING_EXCEPTION=$($_.Exception.Message)" }
      }
      if ($windowClosePosted) {
        Add-Line $status 'STATE=ERROR_WINDOW_CLOSE_REQUESTED'
        $failureEvidence = $false
        $windowClosePosted = $true
        # Keep waiting for the normal process exit; never force-terminate LOVE.
        while (-not $process.WaitForExit(500)) {
          if (([DateTimeOffset]::UtcNow - $lastHeartbeat).TotalSeconds -ge 30) {
            Add-Line $status "HEARTBEAT=$([DateTimeOffset]::Now.ToString('o')) ERROR_WINDOW_CLOSE_PENDING"
            $lastHeartbeat = [DateTimeOffset]::UtcNow
          }
        }
      }
      if (([DateTimeOffset]::UtcNow - $lastHeartbeat).TotalSeconds -ge 30) {
        $summary = Get-TestSummary $Dir
        Add-Line $status "HEARTBEAT=$([DateTimeOffset]::Now.ToString('o')) LAST_TEXT=$($summary.LastText)"
        $lastHeartbeat = [DateTimeOffset]::UtcNow
      }
    }
    $process.WaitForExit()
    $code = $process.ExitCode
    $finished = $true
    $finalEvidence = @(Get-FailureEvidence $Dir)
    if ($finalEvidence.Count -and -not $failureEvidence) {
      Add-Line $status "TEST_ERROR_EVIDENCE_AFTER_PROCESS_EXIT=$($finalEvidence[0])"
      Add-Line $status 'ERROR_WINDOW_ACTION=NOT_APPLICABLE_PROCESS_ALREADY_EXITED'
    }
    $code | Set-Content -LiteralPath $exitFile -Encoding ascii
    $summary = Get-TestSummary $Dir
    $checked = Get-Date
    @("CHECKED_AT=$($checked.ToString('o'))", "MARKER_PATH=$marker", "MARKER_EXISTS=$($summary.Marker)", "TEST_A=$($summary.Test)", "FIRST_ERROR=$($summary.Error)", "ERROR_PHASE=$($summary.ErrorPhase)") | Set-Content -LiteralPath $markerFile -Encoding utf8
    Add-Line $status "LOVE_EXIT_CODE=$code"
    Add-Line $status "TEST_A=$($summary.Test)"
    Add-Line $status "ERROR_PHASE=$($summary.ErrorPhase)"
    Add-Line $status "MARKER_EXISTS=$($summary.Marker)"
    if ($summary.Error) { Add-Line $status "FIRST_ERROR=$($summary.Error)" }
    Add-Line $status "FINISHED=$([DateTimeOffset]::Now.ToString('o'))"
    Add-Line $status 'STATE=FINISHED'
  } catch {
    @("TIME=$([DateTimeOffset]::Now.ToString('o'))", "EXCEPTION_TYPE=$($_.Exception.GetType().FullName)", "MESSAGE=$($_.Exception.Message)", "DETAILS=$($_ | Out-String)") | Set-Content -LiteralPath $exceptionFile -Encoding utf8
    Add-Line $status "WORKER_EXCEPTION=$($_.Exception.Message)"
    if ($process) {
      try {
        $process.Refresh()
        if (-not $process.HasExited) {
          Add-Line $status 'STATE=WORKER_ERROR_WAITING_FOR_LOVE'
          # Retain the single-import lock until the child exits normally.
          $process.WaitForExit()
          $process.Refresh()
          $process.ExitCode | Set-Content -LiteralPath $exitFile -Encoding ascii
          Add-Line $status "LOVE_EXIT_CODE=$($process.ExitCode)"
        }
      } catch { Add-Line $status "WORKER_ERROR_WAIT_EXCEPTION=$($_.Exception.Message)" }
    }
    Add-Line $status 'STATE=WORKER_ERROR'
  } finally {
    Exit-ImportGate $gate
  }
  if (-not $finished -and $process) {
    try { $process.Refresh(); Add-Line $status "LOVE_EXITED_AFTER_WORKER_ERROR=$(-not $process -or $process.HasExited)" } catch { }
  }
}

switch ($Action) {
  'Preflight' {
    $gate = Enter-ImportGate $false
    try { Assert-Ready; Assert-HarnessSource; 'PREFLIGHT=PASS (no import launched)' }
    finally { Exit-ImportGate $gate }
  }
  'ReconcileLocal' {
    Invoke-LocalReconciliation $RunId
  }
  'RegisterTransferred' {
    if ($RunId -notmatch '^italian-[A-Za-z0-9-]+$' -or $ExpectedStatusHash -notmatch '^[A-Fa-f0-9]{64}$' -or
        [string]::IsNullOrWhiteSpace($TransferReason)) { throw 'Provide RunId, ExpectedStatusHash and explicit transfer provenance in TransferReason.' }
    $dir = Join-Path $script:LogRoot $RunId
    $path = Join-Path $dir 'status.txt'
    $fields = Get-RunFields $path
    if ($fields['MACHINE_ID']) { throw 'Only legacy records without machine identity need explicit transfer registration.' }
    $hash = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
    if ($hash -ne $ExpectedStatusHash) { throw 'Original status changed; transfer registration refused.' }
    $note = Get-ClassificationPath $dir
    $data = [ordered]@{ RunId=$RunId; MachineId=$script:MachineId; Computer=$script:Computer;
      Classification='HISTORICAL_UNRESOLVED_REMOTE'; StatusHash=$hash;
      RegisteredAt=[DateTimeOffset]::Now.ToString('o'); Provenance=$TransferReason;
      OriginalState=$fields['STATE'] } | ConvertTo-Json
    # CreateNew never overwrites an earlier observation or an original log.
    $stream = [IO.File]::Open($note, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::Read)
    try { $bytes = $script:Utf8NoBom.GetBytes($data); $stream.Write($bytes, 0, $bytes.Length) }
    finally { $stream.Dispose() }
    "CLASSIFICATION_FILE=$note"
    "CLASSIFICATION=$(Observe-Run $dir)"
  }
  'Start' {
    $gate = Enter-ImportGate $false
    try {
      $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
      $id = "italian-$stamp-$([guid]::NewGuid().ToString('N').Substring(0,8))"
      Start-Worker (Join-Path $script:LogRoot $id)
    } finally { Exit-ImportGate $gate }
  }
  'Status' {
    if (-not $RunId) { throw 'Pass -RunId from the Start output.' }
    Show-RunStatus (Join-Path $script:LogRoot $RunId)
  }
  'Wait' {
    if (-not $RunId) { throw 'Pass -RunId from the Start output.' }
    $dir = Join-Path $script:LogRoot $RunId
    while ($true) {
      $f = Get-RunFields (Join-Path $dir 'status.txt')
      $state = $f['STATE']
      if ($state -in @('FINISHED', 'WORKER_ERROR', 'REFUSED_ACTIVE_IMPORT')) { Show-RunStatus $dir; break }
      $ws = Get-ProcessState $f['WORKER_PID'] 'pwsh' $f['WORKER_STARTED'] $f['WORKER_EXE'] $f['WORKER_SESSION']
      $ls = Get-ProcessState $f['LOVE_PID'] 'lovec' $f['LOVE_STARTED'] $f['LOVE_EXE'] $f['LOVE_SESSION']
      if ($ws -eq 'UNKNOWN' -or $ls -eq 'UNKNOWN') { Write-Output 'PROCESS_STATE=UNKNOWN; runner is not declared finished'; Start-Sleep -Seconds $PollSeconds; continue }
      $recentFiles = @('status.txt', 'stdout.log', 'stderr.log' | ForEach-Object {
        $p = Join-Path $dir $_
        if (Test-Path -LiteralPath $p -PathType Leaf) { (Get-Item -LiteralPath $p).LastWriteTimeUtc }
      } | Sort-Object -Descending | Select-Object -First 1)
      if ($recentFiles.Count -and ([DateTime]::UtcNow - $recentFiles[0]).TotalSeconds -gt 180 -and
          $ws -eq 'NOT_VISIBLE_OR_ABSENT' -and $ls -eq 'NOT_VISIBLE_OR_ABSENT') {
        Show-RunStatus $dir
        'WAIT_RESULT=INDETERMINATE_STALE_ACTIVITY; no process was terminated'
        break
      }
      Start-Sleep -Seconds $PollSeconds
    }
  }
  'Worker' { if (-not $RunDir) { throw '-RunDir is required for Worker.' }; Invoke-Worker $RunDir }
  'SelfTest' {
    $tokens = $null; $parseErrors = $null
    [void][Management.Automation.Language.Parser]::ParseFile($PSCommandPath, [ref]$tokens, [ref]$parseErrors)
    if ($parseErrors.Count) { $parseErrors | ForEach-Object { Write-Error $_ }; exit 1 }
    $fixture = 'Creating RomImporter...' + [Environment]::NewLine + 'Error: ./src/import/RomImporter.lua:1746: Could not open file assets/logo/logo.png.'
    $fixtureError = @(Get-FailureLines $fixture | Select-Object -First 1)
    if ($fixtureError.Count -ne 1 -or $fixtureError[0] -notmatch '^Error:.*Could not open file') {
      throw 'SelfTest: LÖVE initialization error was not detected'
    }
    if (@(Get-FailureLines 'ordinary status message').Count -ne 0) { throw 'SelfTest: ordinary output marked as failure' }
    if ((Get-ErrorPhase $fixture $fixtureError) -ne 'IMPORTER_INITIALIZATION') { throw 'SelfTest: importer initialization phase' }
    $manifestFixture = 'Running import coroutine...' + [Environment]::NewLine +
      'Error: [TEST A FAIL] import coroutine error: RomManifest.lua:14: ROM import metadata is missing'
    if ((Get-ErrorPhase $manifestFixture @(Get-FailureLines $manifestFixture)) -ne 'MANIFEST_LOADING') {
      throw 'SelfTest: manifest loading phase'
    }
    $textFixture = '[ITALIAN TEXT] begin _GreatlyRoseText' + [Environment]::NewLine +
      'Error: _GreatlyRoseText: unsupported text command $AC'
    if ((Get-ErrorPhase $textFixture @(Get-FailureLines $textFixture)) -ne 'ROM_EXTRACTION') {
      throw 'SelfTest: ROM extraction phase'
    }
    if ((Get-ErrorPhase 'Error: failed before importer' @('Error: failed before importer')) -ne 'LOVE_INITIALIZATION') {
      throw 'SelfTest: LÖVE initialization phase'
    }
    'LOVE_ERROR_DETECTION=PASS (startup error and ordinary output)'
    $self = Get-Process -Id $PID
    $start = $self.StartTime.ToUniversalTime().ToString('o')
    $live = Get-ProcessState ([string]$PID) $self.ProcessName $start $self.Path ([string]$self.SessionId)
    if ($live -ne 'ACTIVE') { throw 'SelfTest: actual local process identity not verified' }
    $f = @{ STATE='RUNNING'; MACHINE_ID=$script:MachineId }
    if ((Get-RunClassification $f $false $live 'NOT_RECORDED') -ne 'ACTIVE_LOCAL') { throw 'SelfTest: local active run must block' }
    $wrong = Get-ProcessState ([string]$PID) $self.ProcessName ([DateTimeOffset]::Parse($start).AddDays(-1).ToString('o')) $self.Path ([string]$self.SessionId)
    if ($wrong -ne 'PID_REUSED') { throw 'SelfTest: reused PID accepted' }
    $wrongPath = Get-ProcessState ([string]$PID) $self.ProcessName $start 'C:\not-the-worker.exe' ([string]$self.SessionId)
    if ($wrongPath -ne 'PID_REUSED') { throw 'SelfTest: unrelated executable accepted' }
    if ((Get-RunClassification $f $false 'UNKNOWN' 'NOT_VISIBLE_OR_ABSENT') -ne 'LOCAL_OR_UNKNOWN_UNRESOLVED') { throw 'SelfTest: uncertain local record must block' }
    $f.MACHINE_ID = 'different-computer'
    if ((Get-RunClassification $f $false 'UNKNOWN' 'UNKNOWN') -ne 'STALE_REMOTE') { throw 'SelfTest: remote record' }
    $f.Remove('MACHINE_ID')
    if ((Get-RunClassification $f $true 'UNKNOWN' 'UNKNOWN') -ne 'HISTORICAL_UNRESOLVED_REMOTE') { throw 'SelfTest: transferred legacy record' }
    if ((Get-RunClassification $f $false 'PID_REUSED' 'PID_REUSED') -ne 'LOCAL_OR_UNKNOWN_UNRESOLVED') { throw 'SelfTest: unknown provenance must block' }
    $f.STATE = 'FINISHED'
    if ((Get-RunClassification $f $false 'UNKNOWN' 'UNKNOWN') -ne 'HISTORICAL_CONCLUDED') { throw 'SelfTest: concluded history' }
    'IDENTITY_AND_CLASSIFICATION=PASS (actual current process, reused PID, local uncertainty, remote and legacy records)'
    # A harmless second PowerShell process verifies exclusion across processes.
    # This uses a unique test mutex, not the import mutex, and never launches LOVE.
    $testMutexName = 'Global\Gen1RecompSelfTest-' + [guid]::NewGuid().ToString('N')
    $testMutex = [Threading.Mutex]::new($true, $testMutexName)
    try {
      $info = [Diagnostics.ProcessStartInfo]::new((Join-Path $PSHOME 'pwsh.exe'))
      $info.UseShellExecute = $false
      $info.CreateNoWindow = $true
      $info.ArgumentList.Add('-NoProfile')
      $info.ArgumentList.Add('-Command')
      $info.ArgumentList.Add((' $m=[Threading.Mutex]::new($false,''{0}''); try {{ if($m.WaitOne(0)) {{ $m.ReleaseMutex(); exit 23 }}; exit 0 }} finally {{ $m.Dispose() }} ' -f $testMutexName))
      $child = [Diagnostics.Process]::Start($info)
      $child.WaitForExit()
      if ($child.ExitCode -ne 0) { throw 'SelfTest: cross-process lock failed' }
      $child.Dispose()
    } finally { $testMutex.ReleaseMutex(); $testMutex.Dispose() }
    'CROSS_PROCESS_EXCLUSION=PASS (harmless child, no LOVE)'
    Add-NativeWindowType
    $mine = @([ItalianImportNative]::GetWindows($PID))
    "SYNTAX=PASS"
    "WINDOW_ENUMERATION=PASS PID=$PID WINDOWS=$($mine.Count)"
    "LOG_ROOT_EXISTS=$(Test-Path -LiteralPath $script:LogRoot -PathType Container)"
    "REPO_EXISTS=$(Test-Path -LiteralPath $script:Repo -PathType Container)"
    "LOVE_EXISTS=$(Test-Path -LiteralPath $script:LoveExe -PathType Leaf)"
    Assert-HarnessSource
    'HARNESS_SOURCE=PASS'
  }
}
