from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

import torch


_UPDATE_CKPT_RE = re.compile(r"^checkpoint_(?P<epoch>\d+)_(?P<updates>\d+)\.pt$")


def load_checkpoint(path: Path) -> dict[str, Any]:
    return torch.load(str(path), map_location="cpu", weights_only=False)


def find_update_checkpoints(save_dir: Path) -> list[Path]:
    cands: list[tuple[int, Path]] = []
    for p in save_dir.glob("checkpoint_*.pt"):
        m = _UPDATE_CKPT_RE.match(p.name)
        if not m:
            continue
        cands.append((int(m.group("updates")), p))
    cands.sort(key=lambda t: t[0])
    return [p for _u, p in cands]


def average_models(ckpts: list[dict[str, Any]]) -> dict[str, torch.Tensor]:
    if not ckpts:
        raise ValueError("No checkpoints provided")

    avg: dict[str, torch.Tensor] = {}
    n = len(ckpts)

    # Start with a copy of the first model state
    first_model: dict[str, torch.Tensor] = ckpts[0]["model"]
    for k, v in first_model.items():
        if torch.is_tensor(v) and torch.is_floating_point(v):
            avg[k] = v.clone().to(dtype=torch.float32)
        else:
            # non-float tensors (e.g., int) copied as-is
            avg[k] = v

    # Accumulate remaining
    for ckpt in ckpts[1:]:
        model_sd: dict[str, torch.Tensor] = ckpt["model"]
        for k, v in model_sd.items():
            if k not in avg:
                continue
            if torch.is_tensor(v) and torch.is_floating_point(v) and torch.is_tensor(avg[k]) and torch.is_floating_point(avg[k]):
                avg[k] += v.to(dtype=torch.float32)

    # Divide
    for k, v in list(avg.items()):
        if torch.is_tensor(v) and torch.is_floating_point(v):
            avg[k] = (v / float(n)).to(dtype=first_model[k].dtype)

    return avg


def main() -> int:
    ap = argparse.ArgumentParser(description="Average the last N fairseq update checkpoints.")
    ap.add_argument("--save-dir", type=Path, required=True, help="Directory containing checkpoints")
    ap.add_argument("--num", type=int, default=5, help="How many checkpoints to average")
    ap.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output checkpoint path (default: <save-dir>/checkpoint_avg<num>.pt)",
    )
    args = ap.parse_args()

    save_dir: Path = args.save_dir
    if not save_dir.exists():
        raise SystemExit(f"Missing save dir: {save_dir}")

    ckpt_paths = find_update_checkpoints(save_dir)
    if not ckpt_paths:
        raise SystemExit(f"No update checkpoints found in {save_dir} (expected checkpoint_<epoch>_<updates>.pt)")

    n = max(1, int(args.num))
    selected = ckpt_paths[-n:]

    ckpts = [load_checkpoint(p) for p in selected]
    avg_model = average_models(ckpts)

    # Use the newest checkpoint as base so fairseq can load cfg/args/etc.
    base = ckpts[-1]
    base["model"] = avg_model

    out = args.output or (save_dir / f"checkpoint_avg{n}.pt")
    out.parent.mkdir(parents=True, exist_ok=True)
    torch.save(base, str(out))

    print("Averaged checkpoints:")
    for p in selected:
        print(f"- {p.name}")
    print(f"Wrote: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
