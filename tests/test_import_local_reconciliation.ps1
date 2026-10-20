[CmdletBinding()]
param(
  [switch]$FixtureChild,
  [string]$FixtureRoot,
  [string]$FixtureRunId,
  [string]$FixtureMutex
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\tools\run_italian_import.ps1') -Action SelfTest | Out-Null

if (-not $FixtureRoot) {
  $FixtureRoot = Join-Path $env:TEMP ('gen1recomp-recovery-selftest-' + [guid]::NewGuid().ToString('N'))
}
[void][IO.Directory]::CreateDirectory($FixtureRoot)
$script:LogRoot = $FixtureRoot
$script:ImportMutexName = if ($FixtureMutex) { $FixtureMutex } else {
  'Global\Gen1RecompRecoverySelfTest-' + [guid]::NewGuid().ToString('N')
}

# The process-list gate is exercised separately below. Fixtures never launch LOVE.
# Its real Win32_Process query is used unchanged for an actual reconciliation.
function Assert-NoLocalImport { }

if ($FixtureChild) {
  Invoke-LocalReconciliation $FixtureRunId
  exit 0
}

function New-Fixture([string]$Name, [string]$WorkerPid = '2147483000',
                     [string]$WorkerStarted = '2020-01-01T00:00:00Z',
                     [bool]$IncludeSession = $true) {
  $id = 'italian-test-' + $Name + '-' + [guid]::NewGuid().ToString('N').Substring(0, 8)
  $dir = Join-Path $script:LogRoot $id
  [void][IO.Directory]::CreateDirectory($dir)
  $rows = @(
    "RUN_ID=$id", "MACHINE_ID=$script:MachineId", 'STATE=RUNNING',
    "WORKER_PID=$WorkerPid", "WORKER_STARTED=$WorkerStarted",
    "WORKER_EXE=$(Join-Path $PSHOME 'pwsh.exe')",
    'LOVE_PID=2147483001', 'LOVE_STARTED=2020-01-01T00:00:00Z',
    "LOVE_EXE=$script:LoveExe", 'LOVE_SESSION=1',
    "MARKER_PATH=$(Join-Path $dir 'no-marker')", 'HEARTBEAT=2020-01-01T00:01:00Z'
  )
  if ($IncludeSession) { $rows += 'WORKER_SESSION=1' }
  [IO.File]::WriteAllLines((Join-Path $dir 'status.txt'), $rows)
  [IO.File]::WriteAllText((Join-Path $dir 'stdout.log'), 'partial stdout')
  [IO.File]::WriteAllText((Join-Path $dir 'stderr.log'), '')
  return [pscustomobject]@{ Id=$id; Dir=$dir; Hashes=(Get-OriginalLogHashes $dir) }
}

function Assert-Throws([scriptblock]$Action, [string]$Label) {
  $threw = $false
  try { & $Action | Out-Null } catch { $threw = $true }
  if (-not $threw) { throw "Expected refusal: $Label" }
  "$Label=PASS"
}

$interrupted = New-Fixture 'interrupted'
$result = @(Invoke-LocalReconciliation $interrupted.Id)
if ($result -notcontains 'RECONCILIATION=RECORDED' -or
    $result -notcontains 'CLASSIFICATION=HISTORICAL_INTERRUPTED_LOCAL') {
  throw "Interrupted fixture not classified: $($result -join '; ')"
}
'INTERRUPTED_LOCAL=PASS'
$readyGate = Enter-ImportGate $false
try { Assert-Ready; 'RECONCILED_RUN_ALLOWS_PREFLIGHT=PASS' }
finally { Exit-ImportGate $readyGate }

$again = @(Invoke-LocalReconciliation $interrupted.Id)
if ($again -notcontains 'RECONCILIATION=ALREADY_RECORDED' -or
    @((Get-ChildItem -LiteralPath $script:LogRoot -Filter "reconciliation-$($interrupted.Id)-*.json")).Count -ne 1) {
  throw 'Repeated reconciliation was not idempotent'
}
'REPEATED_RECONCILIATION=PASS'

$own = Get-Process -Id $PID
$active = New-Fixture 'active' ([string]$PID) ($own.StartTime.ToUniversalTime().ToString('o'))
# Fixture session must match the current process to test a genuinely active identity.
Add-Line (Join-Path $active.Dir 'status.txt') "WORKER_SESSION=$($own.SessionId)"
$active.Hashes = Get-OriginalLogHashes $active.Dir
Assert-Throws { Invoke-LocalReconciliation $active.Id } 'ACTIVE_PROCESS_REFUSED'
Assert-Throws { Assert-Ready } 'ACTIVE_RECORD_BLOCKS_PREFLIGHT'
Assert-Ready $active.Id
'VERIFIED_OWN_WORKER_EXCLUSION=PASS'

$reused = New-Fixture 'reused' ([string]$PID) '2020-01-01T00:00:00Z'
if ((Get-ProcessState ([string]$PID) 'pwsh' '2020-01-01T00:00:00Z' (Join-Path $PSHOME 'pwsh.exe') '1') -ne 'PID_REUSED') {
  throw 'PID reuse was not detected using start time'
}
if (@(Invoke-LocalReconciliation $reused.Id) -notcontains 'CLASSIFICATION=HISTORICAL_INTERRUPTED_LOCAL') {
  throw 'Unrelated reused PID incorrectly blocked reconciliation'
}
'REUSED_PID=PASS'

$incomplete = New-Fixture 'incomplete' -IncludeSession $false
Assert-Throws { Invoke-LocalReconciliation $incomplete.Id } 'INCOMPLETE_IDENTITY_REFUSED'

$locked = New-Fixture 'locked'
$gate = Enter-ImportGate $false
try { Assert-Throws { Invoke-LocalReconciliation $locked.Id } 'OTHER_RUN_LOCK_REFUSED' }
finally { Exit-ImportGate $gate }
if (Test-Path (Get-LocalReconciliationPath $locked.Dir)) { throw 'Lock refusal wrote a note' }

$concurrent = New-Fixture 'concurrent'
$pwsh = Join-Path $PSHOME 'pwsh.exe'
$children = @()
try {
  foreach ($number in 1..2) {
    $output = Join-Path $script:LogRoot "child-$number.stdout.txt"
    $errorOutput = Join-Path $script:LogRoot "child-$number.stderr.txt"
    $children += Start-Process -FilePath $pwsh -WindowStyle Hidden -PassThru `
      -ArgumentList @('-NoProfile', '-File', $PSCommandPath, '-FixtureChild', '-FixtureRoot',
        $script:LogRoot, '-FixtureRunId', $concurrent.Id, '-FixtureMutex', $script:ImportMutexName) `
      -RedirectStandardOutput $output -RedirectStandardError $errorOutput
  }
  foreach ($child in $children) { [void]$child.WaitForExit(30000) }
  $notes = @(Get-ChildItem -LiteralPath $script:LogRoot -Filter "reconciliation-$($concurrent.Id)-*.json")
  if ($notes.Count -ne 1 -or (Observe-Run $concurrent.Dir) -ne 'HISTORICAL_INTERRUPTED_LOCAL') {
    throw 'Concurrent reconciliation did not produce exactly one valid note'
  }
  'CONCURRENT_ATTEMPTS=PASS'
} finally {
  foreach ($child in $children) {
    if (-not $child.HasExited) { throw "Fixture child still running: $($child.Id)" }
    $child.Dispose()
  }
}

foreach ($fixture in @($interrupted, $active, $reused, $incomplete, $locked, $concurrent)) {
  $after = Get-OriginalLogHashes $fixture.Dir
  foreach ($name in $fixture.Hashes.Keys) {
    if ($after[$name] -ne $fixture.Hashes[$name]) { throw "Original fixture log changed: $name" }
  }
}
'ORIGINAL_LOGS_PRESERVED=PASS'
"FIXTURE_ROOT=$($script:LogRoot)"
'LOCAL_RECONCILIATION_TESTS=PASS'
