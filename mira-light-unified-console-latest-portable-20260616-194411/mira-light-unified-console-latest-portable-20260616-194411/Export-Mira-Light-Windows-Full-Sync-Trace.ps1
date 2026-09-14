param(
  [string]$SessionDir = "",
  [string]$RuntimeDir = "",
  [string]$OutputDir = "",
  [switch]$IncludeAudio,
  [switch]$Json
)

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VoiceDir = Join-Path $RootDir "Mira-Light-Voice-Full-Ready"

if ($RuntimeDir.Trim().Length -eq 0) {
  $RuntimeDir = Join-Path $VoiceDir "runtime\realtime-voice-interaction"
}
if ($OutputDir.Trim().Length -eq 0) {
  $OutputDir = Join-Path $VoiceDir "runtime\exports"
}

$patterns = @(
  "session.json",
  "warmup.json",
  "turn-*\turn.json",
  "turn-*\transcript.json",
  "turn-*\transcript.txt",
  "turn-*\reply.txt",
  "turn-*\reply.api.json",
  "turn-*\reply.audio.json"
)
if ($IncludeAudio) {
  $patterns += "turn-*\input.wav"
}

function Test-SessionHasTraceFiles([string]$Path) {
  foreach ($pattern in $patterns) {
    $found = Get-ChildItem -Path (Join-Path $Path $pattern) -File -ErrorAction SilentlyContinue |
      Select-Object -First 1
    if ($null -ne $found) {
      return $true
    }
  }
  return $false
}

function Test-SessionHasTurnTraceFiles([string]$Path) {
  $turnPatterns = @(
    "turn-*\turn.json",
    "turn-*\transcript.json",
    "turn-*\transcript.txt",
    "turn-*\reply.txt",
    "turn-*\reply.api.json",
    "turn-*\reply.audio.json"
  )
  if ($IncludeAudio) {
    $turnPatterns += "turn-*\input.wav"
  }
  foreach ($pattern in $turnPatterns) {
    $found = Get-ChildItem -Path (Join-Path $Path $pattern) -File -ErrorAction SilentlyContinue |
      Select-Object -First 1
    if ($null -ne $found) {
      return $true
    }
  }
  return $false
}

function Resolve-LatestSession([string]$BaseDir) {
  if (-not (Test-Path $BaseDir)) {
    throw "Runtime directory not found: $BaseDir"
  }
  $sessions = Get-ChildItem -Path $BaseDir -Directory |
    Sort-Object LastWriteTime -Descending
  if ($null -eq $sessions -or $sessions.Count -eq 0) {
    throw "No session directories found under: $BaseDir"
  }
  foreach ($session in $sessions) {
    if (Test-SessionHasTurnTraceFiles $session.FullName) {
      return $session.FullName
    }
  }
  foreach ($session in $sessions) {
    if (Test-SessionHasTraceFiles $session.FullName) {
      return $session.FullName
    }
  }
  throw "No trace files found under session directories in: $BaseDir"
}

function Get-TraceRelativePath([System.IO.FileInfo]$FileInfo) {
  $parentName = Split-Path -Leaf $FileInfo.DirectoryName
  if ($parentName -like "turn-*") {
    return "$parentName/$($FileInfo.Name)"
  }
  return $FileInfo.Name
}

if ($SessionDir.Trim().Length -eq 0) {
  $SessionDir = Resolve-LatestSession $RuntimeDir
}
if (-not (Test-Path $SessionDir)) {
  throw "Session directory not found: $SessionDir"
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$sessionName = Split-Path -Leaf (Resolve-Path $SessionDir).Path
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$zipPath = Join-Path $OutputDir "mira-full-sync-trace-$sessionName-$stamp.zip"
$stagingDir = Join-Path $OutputDir ".trace-staging-$stamp-$([guid]::NewGuid().ToString('N'))"
New-Item -ItemType Directory -Force -Path $stagingDir | Out-Null

$included = New-Object System.Collections.Generic.List[string]
try {
  foreach ($pattern in $patterns) {
    Get-ChildItem -Path (Join-Path $SessionDir $pattern) -File -ErrorAction SilentlyContinue | ForEach-Object {
      $relative = Get-TraceRelativePath $_
      $target = Join-Path $stagingDir ($relative -replace "/", "\")
      New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
      Copy-Item -LiteralPath $_.FullName -Destination $target -Force
      $included.Add($relative.Replace("\", "/")) | Out-Null
    }
  }

  if ($included.Count -eq 0) {
    throw "No trace files found in session: $SessionDir"
  }

  if (Test-Path $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
  }
  Add-Type -AssemblyName System.IO.Compression.FileSystem
  [System.IO.Compression.ZipFile]::CreateFromDirectory($stagingDir, $zipPath)
} finally {
  if (Test-Path $stagingDir) {
    Remove-Item -LiteralPath $stagingDir -Recurse -Force
  }
}

$payload = [ordered]@{
  ok = $true
  sessionDir = (Resolve-Path $SessionDir).Path
  zipPath = (Resolve-Path $zipPath).Path
  includeAudio = [bool]$IncludeAudio
  included = @($included)
}

if ($Json) {
  $payload | ConvertTo-Json -Depth 8
} else {
  Write-Host "Exported Mira Light full-sync trace:"
  Write-Host "  Session: $($payload.sessionDir)"
  Write-Host "  Zip:     $($payload.zipPath)"
  Write-Host "  Audio:   $($payload.includeAudio)"
  Write-Host "  Files:   $($included.Count)"
}
