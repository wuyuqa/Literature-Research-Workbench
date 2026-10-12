$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$patterns = @(
  'sk-[A-Za-z0-9]{20,}',
  'ghp_[A-Za-z0-9]{20,}',
  'AIza[A-Za-z0-9_-]{20,}',
  'xox[baprs]-[A-Za-z0-9-]{10,}',
  '-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----',
  '(?i)(smtp|auth[_ -]?code|password)\s*[:=]\s*["''][^"'']{8,}["'']'
)
$files = Get-ChildItem $root -Recurse -File | Where-Object { $_.FullName -notmatch '\\\.git\\' -and $_.Extension -notin @('.png','.jpg','.jpeg','.gif','.pyc') }
$hits = @()
foreach ($file in $files) {
  $lines = Get-Content -LiteralPath $file.FullName -ErrorAction SilentlyContinue
  for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i] -match '(?i)your[_ -]?(key|token|password|username|auth[_ -]?code)|placeholder|example\.com|<[^>]+>') { continue }
    foreach ($pattern in $patterns) {
      if ($lines[$i] -match $pattern) {
        $hits += [pscustomobject]@{ file = $file.FullName.Substring($root.Length + 1); line = $i + 1 }
        break
      }
    }
  }
}
if ($hits.Count -gt 0) {
  Write-Host 'Potential credential patterns found:' -ForegroundColor Red
  $hits | Format-Table -AutoSize
  exit 1
}
Write-Host 'Preflight passed: no credential pattern detected.' -ForegroundColor Green
