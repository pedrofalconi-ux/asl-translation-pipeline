param(
  [string]$SrcFile = "asl_pipeline/data/raw/subset_100k.filtered.en.enonly.clean.txt",
  [string]$TgtFile = "asl_pipeline/data/raw/subset_100k.filtered.asl.enonly.clean.txt",
  [string]$OutDir = "data/asl_100k_canon_enonly_clean",
  [string]$DestDir = "data-bin/asl_100k_canon_enonly_clean",
  [int]$Seed = 42,
  [int]$Limit = 100000,
  [ValidateSet('random','first')][string]$LimitMode = "random",
  [int]$MinTokens = 3,
  [int]$MaxTokens = 60,
  [switch]$Normalize = $true,
  [switch]$StripQuotesSemicolons = $true,
  [switch]$CanonicalizeMarkers = $true,
  [switch]$SeparateSentencePiece = $true,
  [switch]$SeparateDictionary = $true
)

$ErrorActionPreference = 'Stop'

# Some PowerShell versions treat native stderr as terminating errors when EAP=Stop.
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
  $PSNativeCommandUseErrorActionPreference = $false
}

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

$venvPython = Join-Path $repoRoot ".venv-lightconv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
  throw "Nao encontrei $venvPython. Crie o venv .venv-lightconv primeiro (setup_lightconv_windows.ps1)."
}

$preparePy = Join-Path $repoRoot "asl_pipeline\scripts\asl_prepare.py"
if (-not (Test-Path $preparePy)) {
  throw "Nao encontrei $preparePy"
}

if (-not (Test-Path (Join-Path $repoRoot $SrcFile))) {
  throw "Nao encontrei SrcFile: $SrcFile"
}
if (-not (Test-Path (Join-Path $repoRoot $TgtFile))) {
  throw "Nao encontrei TgtFile: $TgtFile"
}

Write-Host "Usando python: $venvPython"
& $venvPython -c "import sys; print('python exe:', sys.executable)"

$argsList = @(
  $preparePy,
  "--src-file", $SrcFile,
  "--tgt-file", $TgtFile,
  "--outdir", $OutDir,
  "--run-fairseq-preprocess",
  "--destdir", $DestDir,
  "--seed", $Seed,
  "--min-tokens", $MinTokens,
  "--max-tokens", $MaxTokens,
  "--limit", $Limit,
  "--limit-mode", $LimitMode
)

if ($Normalize) {
  $argsList += "--normalize"
}

if ($StripQuotesSemicolons) {
  $argsList += "--strip-quotes-semicolons"
}

if ($CanonicalizeMarkers) {
  $argsList += "--tgt-canonicalize-markers"
}

if ($SeparateSentencePiece) {
  $argsList += "--sp-separate"
}

if ($SeparateDictionary) {
  $argsList += "--separate-dictionary"
}

Write-Host "Preparando subset filtrado: limit=$Limit (mode=$LimitMode), minTokens=$MinTokens, maxTokens=$MaxTokens"
Write-Host "OutDir=$OutDir"
Write-Host "DestDir=$DestDir"

$prevEap = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& $venvPython @argsList 2>&1
$ErrorActionPreference = $prevEap

if ($LASTEXITCODE -ne 0) {
  throw "prepare falhou (exit=$LASTEXITCODE). Veja o output/log acima."
}
