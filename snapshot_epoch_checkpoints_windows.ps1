param(
  [string]$SaveDir = "D:\translation-pipeline-checkpoints\lightconv_100k_e15",
  [int]$PollSeconds = 20,
  [int]$StableWaitSeconds = 8,
  [string]$VenvPython = ""
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($VenvPython)) {
  $repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
  $VenvPython = Join-Path $repoRoot ".venv-lightconv\Scripts\python.exe"
}

if (-not (Test-Path $VenvPython)) {
  throw "Nao encontrei o Python do venv: $VenvPython"
}

if (-not (Test-Path $SaveDir)) {
  throw "Nao encontrei SaveDir: $SaveDir"
}

$checkpointLast = Join-Path $SaveDir "checkpoint_last.pt"

Write-Host "Watcher ativo. SaveDir=$SaveDir"
Write-Host "Vai criar snapshots em: $SaveDir\\snapshots"

$snapDir = Join-Path $SaveDir "snapshots"
New-Item -ItemType Directory -Force $snapDir | Out-Null

function Get-CheckpointMeta([string]$path) {
  $code = @"
import json
import torch

p = r'''$path'''
ck = torch.load(p, weights_only=False)
ti = (ck.get('extra_state') or {}).get('train_iterator') or {}
oh = ck.get('optimizer_history') or []
last = oh[-1] if oh else {}
epoch = ti.get('epoch')
iters = ti.get('iterations_in_epoch')
num_updates = last.get('num_updates')
print(json.dumps({'epoch': epoch, 'iterations_in_epoch': iters, 'num_updates': num_updates}))
"@
  $json = & $VenvPython -c $code 2>$null
  if ([string]::IsNullOrWhiteSpace($json)) {
    return $null
  }
  return ($json | ConvertFrom-Json)
}

$lastSeenWriteTime = Get-Date "1970-01-01"

while ($true) {
  try {
    if (-not (Test-Path $checkpointLast)) {
      Start-Sleep -Seconds $PollSeconds
      continue
    }

    $item = Get-Item -LiteralPath $checkpointLast
    if ($item.LastWriteTime -le $lastSeenWriteTime) {
      Start-Sleep -Seconds $PollSeconds
      continue
    }

    # Wait for the file to finish writing (size stable).
    $size1 = $item.Length
    Start-Sleep -Seconds $StableWaitSeconds
    $item2 = Get-Item -LiteralPath $checkpointLast
    $size2 = $item2.Length
    if ($size2 -ne $size1) {
      Start-Sleep -Seconds $PollSeconds
      continue
    }

    $meta = Get-CheckpointMeta $checkpointLast
    if ($null -eq $meta) {
      Start-Sleep -Seconds $PollSeconds
      continue
    }

    $epoch = $meta.epoch
    $numUpdates = $meta.num_updates

    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $epochStr = if ($epoch -is [int]) { "{0:D3}" -f $epoch } else { "unk" }
    $updStr = if ($numUpdates -is [int]) { $numUpdates } else { "unk" }

    $dest = Join-Path $snapDir "checkpoint_epoch${epochStr}_updates${updStr}_${stamp}.pt"
    if (-not (Test-Path $dest)) {
      Copy-Item -LiteralPath $checkpointLast -Destination $dest -Force
      Write-Host "SNAPSHOT: $([IO.Path]::GetFileName($dest))"
    }

    $lastSeenWriteTime = (Get-Item -LiteralPath $checkpointLast).LastWriteTime
  } catch {
    # Never crash; just keep watching.
    Write-Host "Watcher error: $($_.Exception.Message)"
  }

  Start-Sleep -Seconds $PollSeconds
}
