param(
    [string]$PythonVersion = "3.10",
    [string]$VenvDir = ".venv-lightconv",
    [string]$SrcFile = "asl_pipeline/data/raw/sample.en",
    [string]$TgtFile = "asl_pipeline/data/raw/sample.asl",
    [string]$OutDir = "data/asl",
    [int]$VocabSize = 8000,
    [int]$Seed = 42,
    [switch]$CpuOnlyTorch,
    [switch]$RecreateVenv,
    [switch]$ForceRebuildDataBin,
    [switch]$Normalize,
    [switch]$StrictAlign
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$workspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $workspaceRoot

function Get-PythonExecutable {
    param([string]$Version)

    try {
        $pyExe = & py -$Version -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $pyExe) {
            return $pyExe.Trim()
        }
    }
    catch {
    }

    return $null
}

function Invoke-Step {
    param(
        [string]$Description,
        [scriptblock]$Action
    )

    Write-Host "`n==> $Description" -ForegroundColor Cyan
    & $Action
}

function Invoke-External {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments
    )

    & $FilePath @Arguments
    if (-not $?) {
        $argsJoined = ($Arguments -join ' ')
        throw "Falha ao executar: $FilePath $argsJoined"
    }

    if ($LASTEXITCODE -ne 0) {
        $argsJoined = ($Arguments -join ' ')
        throw "Falha ao executar: $FilePath $argsJoined (exit=$LASTEXITCODE)"
    }
}

$pythonExe = Get-PythonExecutable -Version $PythonVersion
if (-not $pythonExe) {
    throw "Python $PythonVersion não encontrado no launcher 'py'. Instale Python $PythonVersion (x64) e rode novamente."
}

$venvPath = Join-Path $workspaceRoot $VenvDir
$venvPython = Join-Path $venvPath "Scripts\python.exe"
$venvScripts = Join-Path $venvPath "Scripts"

Invoke-Step -Description "Criando ambiente virtual em $VenvDir" -Action {
    if (Test-Path $venvPython) {
        Write-Host "Venv já existe; reutilizando: $venvPython" -ForegroundColor DarkGray
        return
    }

    if ($RecreateVenv -and (Test-Path $venvPath)) {
        Remove-Item -Recurse -Force $venvPath
    }

    Invoke-External $pythonExe -m venv $venvPath
}

if (-not (Test-Path $venvPython)) {
    throw "Falha ao criar venv: não encontrei $venvPython"
}

Invoke-Step -Description "Atualizando pip para versão compatível com fairseq 0.12.2" -Action {
    Invoke-External $venvPython -m pip install --upgrade "pip<24.1"
}

Invoke-Step -Description "Instalando sentencepiece (necessário para asl_prepare.py)" -Action {
    Invoke-External $venvPython -m pip install --upgrade sentencepiece
}

Invoke-Step -Description "Validando import do sentencepiece" -Action {
    Invoke-External $venvPython -c "import sentencepiece; print('sentencepiece OK')"
}

Invoke-Step -Description "Instalando dependências base do projeto" -Action {
    $tmpReq = Join-Path $env:TEMP "requirements.no_fairseq.txt"
    $lines = @(Get-Content -Path "requirements.txt" -ErrorAction Stop)
    $filtered = @(
        $lines |
            Where-Object { $_ -and $_.Trim() -ne "" } |
            Where-Object { -not ($_.Trim().StartsWith("#")) } |
            Where-Object { $_ -notmatch '^\s*fairseq\s*==' }
    )
    Set-Content -Path $tmpReq -Value $filtered -Encoding utf8
    Invoke-External $venvPython -m pip install -r $tmpReq
}

Invoke-Step -Description "Instalando Torch (necessário para fairseq)" -Action {
    if ($CpuOnlyTorch) {
        Invoke-External $venvPython -m pip install --upgrade --index-url https://download.pytorch.org/whl/cpu torch torchvision torchaudio
    }
    else {
        Invoke-External $venvPython -m pip install --upgrade torch torchvision torchaudio
    }
}

Invoke-Step -Description "Checando toolchain C++ (MSVC) para compilar fairseq no Windows" -Action {
    $cl = Get-ChildItem -Path "C:\\Program Files*\\Microsoft Visual Studio\\2022\\BuildTools\\VC\\Tools\\MSVC\\*\\bin\\Hostx64\\x64\\cl.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $cl) {
        throw @"
MSVC (cl.exe) não encontrado.

O fairseq 0.12.2 normalmente NÃO tem wheel pronta para Windows e precisa compilar extensões.

Opções:
1) Instalar "Build Tools for Visual Studio 2022" com o workload "C++ build tools" (Desktop development with C++), reiniciar o terminal e rodar de novo.
2) Usar WSL2 (Ubuntu) e rodar esse setup dentro do Linux (recomendado para fairseq).
"@
    }

    Write-Host "MSVC encontrado: $($cl.FullName)" -ForegroundColor DarkGray
}

Invoke-Step -Description "Garantindo fairseq==0.12.2" -Action {
    $vsDevCmd = "C:\\Program Files (x86)\\Microsoft Visual Studio\\2022\\BuildTools\\Common7\\Tools\\VsDevCmd.bat"
    if (Test-Path $vsDevCmd) {
        $cmd = "`"$vsDevCmd`" -arch=amd64 -host_arch=amd64 && `"$venvPython`" -m pip install fairseq==0.12.2"
        Invoke-External cmd.exe /c $cmd
    }
    else {
        Invoke-External $venvPython -m pip install fairseq==0.12.2
    }
}

Invoke-Step -Description "Validando import do fairseq" -Action {
    Invoke-External $venvPython -c "import fairseq; print('fairseq OK')"
}

$env:Path = "$venvScripts;$env:Path"

$binDir = Join-Path $workspaceRoot "data-bin/asl"
if ($ForceRebuildDataBin -and (Test-Path $binDir)) {
    Invoke-Step -Description "Limpando data-bin/asl (ForceRebuildDataBin)" -Action {
        Remove-Item -Recurse -Force $binDir
    }
}

$hasExistingBin = $false
if (Test-Path $binDir) {
    $maybeDict = Join-Path $binDir "dict.en.txt"
    $maybeTrain = Get-ChildItem -Path $binDir -Filter "train.*.bin" -File -ErrorAction SilentlyContinue | Select-Object -First 1
    if ((Test-Path $maybeDict) -and $maybeTrain) {
        $hasExistingBin = $true
    }
}

$prepareArgs = @(
    "asl_pipeline/scripts/asl_prepare.py",
    "--src-file", $SrcFile,
    "--tgt-file", $TgtFile,
    "--outdir", $OutDir,
    "--vocab-size", "$VocabSize",
    "--seed", "$Seed",
    "--run-fairseq-preprocess"
)

if ($Normalize) {
    $prepareArgs += "--normalize"
}

if ($StrictAlign) {
    $prepareArgs += "--strict-align"
}

Invoke-Step -Description "Preparando dataset e rodando fairseq-preprocess" -Action {
    if ($hasExistingBin -and -not $ForceRebuildDataBin) {
        Write-Host "data-bin/asl já existe; pulando fairseq-preprocess (use -ForceRebuildDataBin para recriar)." -ForegroundColor DarkGray
        return
    }

    Invoke-External $venvPython @prepareArgs
}
$binFiles = @()
if (Test-Path $binDir) {
    $binFiles = @(Get-ChildItem -Path $binDir -File -ErrorAction SilentlyContinue)
}

if (-not $binFiles -or @($binFiles).Length -eq 0) {
    Write-Host "fairseq-preprocess via CLI não gerou arquivos; tentando fallback com módulo Python..." -ForegroundColor Yellow

    Invoke-Step -Description "Fallback: python -m fairseq_cli.preprocess" -Action {
        Invoke-External $venvPython -m fairseq_cli.preprocess `
            --source-lang en `
            --target-lang asl `
            --trainpref "$OutDir/train.sp" `
            --validpref "$OutDir/valid.sp" `
            --testpref "$OutDir/test.sp" `
            --destdir "data-bin/asl" `
            --joined-dictionary
    }
}

$finalFiles = @()
if (Test-Path $binDir) {
    $finalFiles = @(Get-ChildItem -Path $binDir -File -ErrorAction SilentlyContinue)
}

if (-not $finalFiles -or @($finalFiles).Length -eq 0) {
    throw "Não foi possível gerar arquivos em data-bin/asl. Verifique fairseq e logs acima."
}

Write-Host "`nAmbiente pronto e dataset carregado para treino LightConv em data-bin/asl." -ForegroundColor Green
Write-Host "Python do ambiente: $venvPython"
