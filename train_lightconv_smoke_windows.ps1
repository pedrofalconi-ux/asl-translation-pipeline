param(
  [string]$DatasetDir = "data-bin/asl",
  [int]$MaxTokens = 512,
  [int]$MaxEpoch = 1,
  [int]$MaxUpdate = 0,
  [int]$LogInterval = 5,
  [string]$SaveDir = "checkpoints/lightconv_smoke",
  [switch]$NoEpochCheckpoints,
  [int]$SaveInterval = 1,
  [int]$KeepLastEpochs = 0,
  [switch]$NoSaveOptimizerState
)

$ErrorActionPreference = 'Stop'

# Some PowerShell versions treat native stderr output as terminating errors when
# $ErrorActionPreference is 'Stop'. Fairseq/PyTorch can emit harmless warnings
# on stderr (e.g., pin_memory on CPU). We must not abort training because of
# warnings; rely on $LASTEXITCODE instead.
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
  $PSNativeCommandUseErrorActionPreference = $false
}

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

$venvPython = Join-Path $repoRoot ".venv-lightconv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
  throw "Nao encontrei $venvPython. Crie o venv .venv-lightconv primeiro (setup_lightconv_windows.ps1)."
}

$dataset = Join-Path $repoRoot $DatasetDir
if (-not (Test-Path $dataset)) {
  throw "Nao encontrei $dataset. Rode o preprocess primeiro (ex.: asl_prepare.py --run-fairseq-preprocess --destdir $DatasetDir)."
}

Write-Host "Usando python: $venvPython"
& $venvPython -c "import sys; print('python exe:', sys.executable); import fairseq_cli; print('fairseq_cli ok')" 2>&1
if ($LASTEXITCODE -ne 0) {
  throw "Falha ao validar o ambiente Python/fairseq_cli (exit=$LASTEXITCODE)"
}

New-Item -ItemType Directory -Force -Path $SaveDir | Out-Null

$compatRunner = Join-Path $repoRoot "fairseq_compat_run.py"

$cmd = @(
  $compatRunner,
  "train",
  $DatasetDir,
  "--task", "translation",
  "--arch", "lightconv_iwslt_de_en",
  "--criterion", "label_smoothed_cross_entropy",
  "--label-smoothing", "0.1",
  "--optimizer", "adam",
  "--lr", "5e-4",
  "--max-tokens", $MaxTokens,
  "--save-dir", $SaveDir,
  "--log-format", "simple",
  "--log-interval", $LogInterval
)

if (-not (Test-Path $compatRunner)) {
  throw "Nao encontrei $compatRunner. Esse arquivo e necessario para compatibilidade com PyTorch>=2.6 ao carregar checkpoints."
}

if ($NoEpochCheckpoints) {
  $cmd += "--no-epoch-checkpoints"
}

if ($SaveInterval -gt 0) {
  $cmd += @("--save-interval", $SaveInterval)
}

if ($KeepLastEpochs -gt 0) {
  $cmd += @("--keep-last-epochs", $KeepLastEpochs)
}

if ($NoSaveOptimizerState) {
  $cmd += "--no-save-optimizer-state"
}

if ($MaxUpdate -gt 0) {
  $cmd += @("--max-update", $MaxUpdate)
  Write-Host "Rodando treino: fairseq_cli.train (max-tokens=$MaxTokens, max-update=$MaxUpdate)"
} else {
  $cmd += @("--max-epoch", $MaxEpoch)
  Write-Host "Rodando treino: fairseq_cli.train (max-tokens=$MaxTokens, max-epoch=$MaxEpoch)"
}
# Do not let stderr warnings abort the script.
$prevEap = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& $venvPython @cmd 2>&1
$ErrorActionPreference = $prevEap
if ($LASTEXITCODE -ne 0) {
  throw "Treino falhou (exit=$LASTEXITCODE). Veja o output acima/log."
}
