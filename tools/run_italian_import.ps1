[CmdletBinding()]
param(
  [ValidateSet('Start', 'Status', 'Wait', 'Worker', 'SelfTest')]
  [string]$Action = 'Start',
  [string]$RunId,
  [string]$RunDir,
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
  }
  return $fields
}

function Get-ProcessState([string]$IdText, [string]$ExpectedName, [string]$StartText) {
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
      if ([Math]::Abs(($p.StartTime.ToUniversalTime() - $expected).TotalSeconds) -gt 20) { return 'PID_REUSED' }
    } catch { return 'UNKNOWN' }
  }
  return 'ACTIVE'
}

function Get-TestSummary([string]$Dir) {
  $stdout = Read-SharedText (Join-Path $Dir 'stdout.log')
  $stderr = Read-SharedText (Join-Path $Dir 'stderr.log')
  $combined = $stdout + "`n" + $stderr
  $testStatus = if ($combined -match 'TEST A:\s*PASS') { 'PASS' }
    elseif ($combined -match 'TEST A FAIL') { 'FAIL' } else { 'NOT_REPORTED' }
  $errorLine = @($combined -split "`r?`n" | Where-Object {
    $_ -match '\[TEST A FAIL\]|unsupported text command|missing dynamic text substitution|import coroutine error:'
  } | Select-Object -First 1)
  $lastText = @($stdout -split "`r?`n" | Where-Object { $_ -match '\[ITALIAN TEXT\] end .*result=' } | Select-Object -Last 1)
  $fields = Get-RunFields (Join-Path $Dir 'status.txt')
  $marker = $fields['MARKER_PATH']
  if (-not $marker) { $marker = Join-Path $script:AppData 'LOVE\test-italian-run\red_ita\rom-cache.complete' }
  [pscustomobject]@{
    Test = $testStatus
    Error = if ($errorLine.Count) { $errorLine[0] } else { '' }
    LastText = if ($lastText.Count) { $lastText[0] } else { '' }
    Marker = (Test-Path -LiteralPath $marker -PathType Leaf)
    Fields = $fields
  }
}

function Show-RunStatus([string]$Dir) {
  if (-not (Test-Path -LiteralPath $Dir -PathType Container)) { throw "Run directory not found: $Dir" }
  $statusPath = Join-Path $Dir 'status.txt'
  $f = Get-RunFields $statusPath
  $loveState = Get-ProcessState $f['LOVE_PID'] 'lovec' $f['LOVE_STARTED']
  $workerState = Get-ProcessState $f['WORKER_PID'] 'pwsh' $f['WORKER_STARTED']
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
  "OBSERVED_STATE=$observed"
  "WORKER_PROCESS=$workerState PID=$($f['WORKER_PID'])"
  "LOVE_PROCESS=$loveState PID=$($f['LOVE_PID'])"
  "EXIT_CODE=$($f['LOVE_EXIT_CODE'])"
  "TEST_A=$($summary.Test)"
  "LAST_TEXT_DIAGNOSTIC=$($summary.LastText)"
  "FIRST_ERROR_EVIDENCE=$($summary.Error)"
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
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr hWnd, IntPtr hdc, uint flags);
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
    return pid == expectedPid && PostMessage(h, 0x0010, IntPtr.Zero, IntPtr.Zero);
  }
}
'@
}

function Get-FailureEvidence([string]$Dir) {
  $all = (Read-SharedText (Join-Path $Dir 'stdout.log')) + "`n" + (Read-SharedText (Join-Path $Dir 'stderr.log'))
  return @($all -split "`r?`n" | Where-Object {
    $_ -match '\[TEST A FAIL\]|unsupported text command|missing dynamic text substitution|import coroutine error:'
  } | Select-Object -First 1)
}

function Capture-AndCloseErrorWindow($Process, [string]$Dir) {
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
  $capture = Join-Path $Dir ("love-error-{0}.png" -f (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
  try {
    Add-Type -AssemblyName System.Drawing.Common
    $rect = New-Object ItalianImportNative+RECT
    $hasRect = [ItalianImportNative]::GetWindowRect($target.Handle, [ref]$rect)
    $width = $rect.Right - $rect.Left
    $height = $rect.Bottom - $rect.Top
    if ($hasRect -and $width -gt 0 -and $height -gt 0) {
      $bitmap = [System.Drawing.Bitmap]::new($width, $height)
      $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
      $hdc = $graphics.GetHdc()
      try { $captured = [ItalianImportNative]::PrintWindow($target.Handle, $hdc, 2) }
      finally { $graphics.ReleaseHdc($hdc) }
      if ($captured) { $bitmap.Save($capture, [System.Drawing.Imaging.ImageFormat]::Png) }
      $graphics.Dispose()
      $bitmap.Dispose()
    } else { $captured = $false }
    if ($captured) {
      Add-Line (Join-Path $Dir 'status.txt') "ERROR_WINDOW_CAPTURE=$capture"
    } else {
      Add-Line (Join-Path $Dir 'status.txt') 'ERROR_WINDOW_CAPTURE=PrintWindow or GetWindowRect returned false'
    }
  } catch {
    Add-Line (Join-Path $Dir 'status.txt') "ERROR_WINDOW_CAPTURE_EXCEPTION=$($_.Exception.Message)"
  }
  $closed = [ItalianImportNative]::CloseOwnedWindow($target.Handle, $Process.Id)
  Add-Line (Join-Path $Dir 'status.txt') "ERROR_WINDOW_WM_CLOSE_POSTED=$closed HANDLE=$($target.Handle) PID=$($Process.Id)"
  if ($closed) { Add-Line (Join-Path $Dir 'status.txt') 'STATE=ERROR_WINDOW_CLOSE_REQUESTED' }
  return $closed
}

function Start-Worker([string]$Dir) {
  if (-not (Test-Path -LiteralPath $script:Repo -PathType Container)) { throw "Repository not found: $script:Repo" }
  if (-not (Test-Path -LiteralPath $script:LogRoot -PathType Container)) { throw "Persistent log directory not found: $script:LogRoot" }
  if (-not (Test-Path -LiteralPath $script:LoveExe -PathType Leaf)) { throw "LOVE executable not found: $script:LoveExe" }
  $active = @()
  foreach ($oldDir in (Get-ChildItem -LiteralPath $script:LogRoot -Directory -ErrorAction SilentlyContinue)) {
    $oldStatus = Join-Path $oldDir.FullName 'status.txt'
    if (-not (Test-Path -LiteralPath $oldStatus -PathType Leaf)) { continue }
    $old = Get-RunFields $oldStatus
    if ($old['STATE'] -notin @('START_REQUESTED', 'RUNNING', 'ERROR_RECORDED', 'ERROR_WINDOW_CLOSE_REQUESTED', 'WORKER_ERROR_WAITING_FOR_LOVE')) { continue }
    $loveState = Get-ProcessState $old['LOVE_PID'] 'lovec' $old['LOVE_STARTED']
    $workerState = Get-ProcessState $old['WORKER_PID'] 'pwsh' $old['WORKER_STARTED']
    if ($loveState -notin @('PID_REUSED') -or $workerState -notin @('PID_REUSED')) {
      $active += "$($old['RUN_ID']): worker=$workerState love=$loveState"
    }
  }
  if ($active.Count) { throw "Refusing to start while a prior import may still be active: $($active -join '; ')" }
  $runId = Split-Path $Dir -Leaf
  [IO.Directory]::CreateDirectory($Dir) | Out-Null
  $status = Join-Path $Dir 'status.txt'
  Add-Line $status "RUN_ID=$runId"
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
  $lock = $null
  $process = $null
  $finished = $false
  try {
    try {
      $lock = [IO.File]::Open((Join-Path $script:LogRoot 'italian-import.active.lock'), [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
    } catch {
      Add-Line $status "REFUSED=$($_.Exception.Message)"
      Add-Line $status 'STATE=REFUSED_ACTIVE_IMPORT'
      return
    }
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
    $lastHeartbeat = [DateTimeOffset]::UtcNow
    $failureEvidence = $false
    $failureAt = $null
    $windowClosePosted = $false
    $lastWindowCheck = [DateTimeOffset]::MinValue
    $windowMissingLogged = $false
    while (-not $process.WaitForExit(500)) {
      if (-not $failureEvidence) {
        $evidence = Get-FailureEvidence $Dir
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
    $finalEvidence = Get-FailureEvidence $Dir
    if ($finalEvidence.Count -and -not $failureEvidence) {
      Add-Line $status "TEST_ERROR_EVIDENCE_AFTER_PROCESS_EXIT=$($finalEvidence[0])"
      Add-Line $status 'ERROR_WINDOW_ACTION=NOT_APPLICABLE_PROCESS_ALREADY_EXITED'
    }
    $code | Set-Content -LiteralPath $exitFile -Encoding ascii
    $summary = Get-TestSummary $Dir
    $checked = Get-Date
    @("CHECKED_AT=$($checked.ToString('o'))", "MARKER_PATH=$marker", "MARKER_EXISTS=$($summary.Marker)", "TEST_A=$($summary.Test)", "FIRST_ERROR=$($summary.Error)") | Set-Content -LiteralPath $markerFile -Encoding utf8
    Add-Line $status "LOVE_EXIT_CODE=$code"
    Add-Line $status "TEST_A=$($summary.Test)"
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
    if ($lock) { $lock.Dispose() }
  }
  if (-not $finished -and $process) {
    try { $process.Refresh(); Add-Line $status "LOVE_EXITED_AFTER_WORKER_ERROR=$(-not $process -or $process.HasExited)" } catch { }
  }
}

switch ($Action) {
  'Start' {
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $id = "italian-$stamp-$([guid]::NewGuid().ToString('N').Substring(0,8))"
    Start-Worker (Join-Path $script:LogRoot $id)
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
      $ws = Get-ProcessState $f['WORKER_PID'] 'pwsh' $f['WORKER_STARTED']
      $ls = Get-ProcessState $f['LOVE_PID'] 'lovec' $f['LOVE_STARTED']
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
    Add-NativeWindowType
    $mine = @([ItalianImportNative]::GetWindows($PID))
    "SYNTAX=PASS"
    "WINDOW_ENUMERATION=PASS PID=$PID WINDOWS=$($mine.Count)"
    "LOG_ROOT_EXISTS=$(Test-Path -LiteralPath $script:LogRoot -PathType Container)"
    "REPO_EXISTS=$(Test-Path -LiteralPath $script:Repo -PathType Container)"
    "LOVE_EXISTS=$(Test-Path -LiteralPath $script:LoveExe -PathType Leaf)"
  }
}
