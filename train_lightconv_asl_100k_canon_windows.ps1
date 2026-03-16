param(
  [string]$DatasetDir = "data-bin/asl_100k_canon_enonly_clean",
  [int]$MaxTokens = 512,
  [int]$UpdateFreq = 1,
  [int]$MaxEpoch = 20,
  [int]$WarmupUpdates = 4000,
  [string]$Lr = "5e-4",
  [double]$Dropout = 0.3,
  [double]$WeightDecay = 0.0001,
  [double]$LabelSmoothing = 0.1,
  [string]$SaveDir = "D:\translation-pipeline-checkpoints\lightconv_asl_100k_canon_enonly_clean_invSqrt",
  [int]$SaveIntervalUpdates = 2000,
  [int]$KeepIntervalUpdates = 10,
  [int]$KeepBestCheckpoints = 1,
  [int]$LogInterval = 50,
  [int]$Patience = 7,
  [switch]$Cpu
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
  throw "Nao encontrei $venvPython. Crie o venv .venv-lightconv primeiro."
}

$dataset = Join-Path $repoRoot $DatasetDir
if (-not (Test-Path $dataset)) {
  throw "Nao encontrei $dataset. Rode: .\\prepare_subset_100k_windows.ps1 (gera $DatasetDir)."
}

$compatRunner = Join-Path $repoRoot "fairseq_compat_run.py"
if (-not (Test-Path $compatRunner)) {
  throw "Nao encontrei $compatRunner (wrapper de compatibilidade)."
}

# Enforce storing checkpoints on D: (storage constraint).
if (-not ($SaveDir -match '^[Dd]:\\')) {
  throw "SaveDir precisa estar no disco D: (ex.: D:\\translation-pipeline-checkpoints\\...). Atual: $SaveDir"
}

$dDrive = Get-PSDrive -Name D -ErrorAction SilentlyContinue
if (-not $dDrive) {
  throw "Disco D: nao esta disponivel. Monte/ative o drive D: antes do treino."
}

Write-Host ("Disco D: livre: {0:N2} GB / total: {1:N2} GB" -f ($dDrive.Free/1GB), ($dDrive.Used/1GB + $dDrive.Free/1GB))

New-Item -ItemType Directory -Force -Path $SaveDir | Out-Null

Write-Host "Usando python: $venvPython"
# fairseq may emit informational messages to stderr (e.g., tensorboardX notice).
# On Windows PowerShell 5.1 with ErrorActionPreference=Stop, that can abort the script.
$prevEapValidate = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& $venvPython -c "import sys; print('python exe:', sys.executable); import fairseq; print('fairseq', fairseq.__version__)" 2>&1
$ErrorActionPreference = $prevEapValidate
if ($LASTEXITCODE -ne 0) {
  throw "Falha ao validar o ambiente (exit=$LASTEXITCODE)"
}

$cmd = @(
  $compatRunner,
  "train",
  $DatasetDir,
  "--task", "translation",
  "--arch", "lightconv_iwslt_de_en",
  "--share-decoder-input-output-embed",
  "--seed", "42",
  "--criterion", "label_smoothed_cross_entropy",
  "--label-smoothing", $LabelSmoothing,
  "--optimizer", "adam",
  "--lr", $Lr,
  "--lr-scheduler", "inverse_sqrt",
  "--warmup-updates", $WarmupUpdates,
  "--dropout", $Dropout,
  "--weight-decay", $WeightDecay,
  "--max-tokens", $MaxTokens,
  "--update-freq", $UpdateFreq,
  "--max-epoch", $MaxEpoch,
  "--save-dir", $SaveDir,
  "--no-epoch-checkpoints",
  "--save-interval-updates", $SaveIntervalUpdates,
  "--keep-interval-updates", $KeepIntervalUpdates,
  "--keep-best-checkpoints", $KeepBestCheckpoints,
  "--patience", $Patience,
  "--log-format", "simple",
  "--log-interval", $LogInterval
)

if ($Cpu) {
  $cmd += "--cpu"
}

Write-Host "Rodando treino (do zero):"
Write-Host "  data-bin: $DatasetDir"
Write-Host "  save-dir: $SaveDir"
Write-Host "  max-tokens: $MaxTokens, update-freq: $UpdateFreq"
Write-Host "  lr: $Lr, scheduler: inverse_sqrt, warmup-updates: $WarmupUpdates"
Write-Host "  dropout: $Dropout, label-smoothing: $LabelSmoothing, weight-decay: $WeightDecay"
Write-Host "  checkpoint: save-interval-updates=$SaveIntervalUpdates, keep-interval-updates=$KeepIntervalUpdates, keep-best=$KeepBestCheckpoints"

$prevEap = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& $venvPython @cmd 2>&1
$ErrorActionPreference = $prevEap

if ($LASTEXITCODE -ne 0) {
  throw "Treino falhou (exit=$LASTEXITCODE). Veja o output/log."
}
