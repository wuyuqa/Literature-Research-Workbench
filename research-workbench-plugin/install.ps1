$ErrorActionPreference = 'Stop'

function Add-CodexMarketplace([string]$Url) {
  & codex plugin marketplace add $Url --ref main --json
  if ($LASTEXITCODE -ne 0) { Write-Host "Marketplace already registered or unavailable: $Url" -ForegroundColor Yellow }
}

function Add-CodexPlugin([string]$Name, [string]$Marketplace) {
  & codex plugin add $Name --marketplace $Marketplace --json
  if ($LASTEXITCODE -ne 0) { Write-Host "Plugin already installed or unavailable: $Name@$Marketplace" -ForegroundColor Yellow }
}

Write-Host 'Installing Research Workbench dependencies...'

Add-CodexMarketplace 'https://github.com/Imbad0202/academic-research-skills'
Add-CodexMarketplace 'https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep'
Add-CodexMarketplace 'https://github.com/zarazhangrui/frontend-slides'

Add-CodexPlugin 'academic-research-skills' 'academic-research-skills'
Add-CodexPlugin 'aris' 'aris'
Add-CodexPlugin 'frontend-slides' 'frontend-slides'
Add-CodexPlugin 'zotero' 'openai-curated-remote'
Add-CodexPlugin 'app-6a60df60877081919ad4a8109d27535d' 'openai-curated-remote'

Write-Host 'Bundled skills include LaTeX, imagegen, presentations, nature figure checks, SVG/PPTX conversion and Zotero.'
Write-Host 'The Undermind connector may require a one-time sign-in/connection in Codex.'

$source = (Resolve-Path (Join-Path $PSScriptRoot '.')).Path
$marketplace = Join-Path $source '.agents/plugins/marketplace.json'
if (Test-Path $marketplace) {
  & codex plugin marketplace add $source --json
  if ($LASTEXITCODE -ne 0) { Write-Host 'Local marketplace already registered.' -ForegroundColor Yellow }
  Add-CodexPlugin 'literature-research-workbench' 'personal-research-workbench'
}

Write-Host 'Installation finished. Restart Codex and run literature-research-workbench:setup.'
