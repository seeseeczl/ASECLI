# One-command installer for Windows PowerShell.
$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$repo = "seeseeczl/ASECLI"
$localBin = Join-Path $HOME ".local\bin"
$env:Path = "$localBin;$env:Path"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    irm https://astral.sh/uv/install.ps1 | iex
    $env:Path = "$localBin;$env:Path"
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Error "uv installed but not on PATH. Open a new PowerShell window and re-run this command."
}

if ($env:ASECLI_REF) {
    $tag = $env:ASECLI_REF
} else {
    $tag = (Invoke-RestMethod "https://api.github.com/repos/$repo/releases/latest").tag_name
}
if (-not $tag) {
    $tag = "v0.8.0"
}

$version = $tag.TrimStart("v")
$wheel = "https://github.com/$repo/releases/download/$tag/asecli-$version-py3-none-any.whl"
uv tool install --force $wheel
$skillHelp = (& asecli install-skill --help 2>&1 | Out-String)
if ($skillHelp -match "--agent") {
    & asecli install-skill --agent all
} else {
    & asecli install-skill
}
if ($LASTEXITCODE -ne 0) {
    Write-Host "CLI is installed. Skill was skipped because a different copy already exists."
}
Write-Host ""
Write-Host "Done. Try: asecli --help"
Write-Host "If the command is not found, open a new terminal."
