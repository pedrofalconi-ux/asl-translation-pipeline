param(
  [string]$DatasetDir = "data-bin/asl",
  [string]$CheckpointPath = "checkpoints/lightconv_smoke/checkpoint_last.pt",
  [int]$Beam = 5
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

$venvPython = Join-Path $repoRoot ".venv-lightconv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
  throw "Nao encontrei $venvPython. Use o ambiente .venv-lightconv (setup_lightconv_windows.ps1)."
}

$wrapper = Join-Path $repoRoot "fairseq_compat_run.py"
if (-not (Test-Path $wrapper)) {
  throw "Nao encontrei $wrapper"
}

if (-not (Test-Path (Join-Path $repoRoot $DatasetDir))) {
  throw "Nao encontrei DatasetDir: $DatasetDir"
}
if (-not (Test-Path (Join-Path $repoRoot $CheckpointPath))) {
  throw "Nao encontrei CheckpointPath: $CheckpointPath"
}

Write-Host "Usando python: $venvPython"
& $venvPython -c "import sys; print('python exe:', sys.executable); import fairseq_cli; print('fairseq_cli ok')"

Write-Host "Rodando interativo (beam=$Beam)"
Write-Host "Dataset: $DatasetDir"
Write-Host "Checkpoint: $CheckpointPath"
Write-Host "Cole uma frase EN e aperte Enter. Ctrl+C para sair."

& $venvPython $wrapper interactive $DatasetDir --path $CheckpointPath --beam $Beam
