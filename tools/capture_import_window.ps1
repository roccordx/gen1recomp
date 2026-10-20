# Disposable screenshot child. It never sends input, closes windows, or edits import logs.
[CmdletBinding()]
param(
  [Parameter(Mandatory)][int]$TargetPid,
  [Parameter(Mandatory)][string]$TargetStarted,
  [Parameter(Mandatory)][string]$TargetPath,
  [Parameter(Mandatory)][int]$TargetSession,
  [Parameter(Mandatory)][long]$WindowHandle,
  [Parameter(Mandatory)][string]$OutputPath
)
$ErrorActionPreference = 'Stop'
try {
  $process = Get-Process -Id $TargetPid -ErrorAction Stop
  if ($process.Path -ine $TargetPath -or $process.SessionId -ne $TargetSession -or
      $process.StartTime.ToUniversalTime() -ne [DateTimeOffset]::Parse($TargetStarted).UtcDateTime) {
    throw 'Screenshot target process identity changed'
  }
  Add-Type -AssemblyName System.Drawing.Common
  Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class ImportScreenshotNative {
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out int pid);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT rect);
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr dc, uint flags);
}
'@
  $handle = [IntPtr]::new($WindowHandle)
  $owner = 0
  [void][ImportScreenshotNative]::GetWindowThreadProcessId($handle, [ref]$owner)
  if ($owner -ne $TargetPid) { throw 'Screenshot window belongs to another process' }
  $rect = [ImportScreenshotNative+RECT]::new()
  if (-not [ImportScreenshotNative]::GetWindowRect($handle, [ref]$rect)) { throw 'GetWindowRect failed' }
  $width = $rect.Right - $rect.Left
  $height = $rect.Bottom - $rect.Top
  if ($width -le 0 -or $height -le 0) { throw 'Empty window rectangle' }
  $bitmap = [Drawing.Bitmap]::new($width, $height)
  try {
    $graphics = [Drawing.Graphics]::FromImage($bitmap)
    try {
      $dc = $graphics.GetHdc()
      try { $captured = [ImportScreenshotNative]::PrintWindow($handle, $dc, 2) }
      finally { $graphics.ReleaseHdc($dc) }
    } finally { $graphics.Dispose() }
    if (-not $captured) { throw 'PrintWindow returned false' }
    # Never replace an existing screenshot, even if a caller reuses its path.
    $file = [IO.File]::Open($OutputPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write)
    try { $bitmap.Save($file, [Drawing.Imaging.ImageFormat]::Png) }
    finally { $file.Dispose() }
  } finally { $bitmap.Dispose() }
  'SCREENSHOT_CAPTURED'
  exit 0
} catch {
  [Console]::Error.WriteLine($_.Exception.Message)
  exit 1
}
