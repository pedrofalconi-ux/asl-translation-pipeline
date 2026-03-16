from __future__ import annotations

import argparse
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Example:
    idx: int
    src_sp: str
    ref_sp: str
    hyp_sp: str | None = None


def decode_sentencepiece_tokens(sp_line: str) -> str:
    """Best-effort decode of SentencePiece-tokenized text.

    Fairseq output/input here uses whitespace-separated SentencePiece tokens.
    We convert token stream back to text by joining and replacing the SP word
    boundary marker '▁' with spaces.
    """

    tokens = sp_line.strip().split()
    text = "".join(tokens).replace("▁", " ").strip()
    text = re.sub(r"\s+", " ", text)
    return text


def read_n_lines(path: Path, n: int) -> list[str]:
    lines: list[str] = []
    with path.open("r", encoding="utf-8") as f:
        for _ in range(n):
            line = f.readline()
            if not line:
                break
            lines.append(line.rstrip("\n"))
    return lines


def find_latest_snapshot(snapshots_dir: Path) -> Path:
    cands = sorted(
        snapshots_dir.glob("checkpoint_epoch*.pt"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not cands:
        raise FileNotFoundError(f"No snapshot checkpoints found in: {snapshots_dir}")
    return cands[0]


def parse_interactive_hyps(stdout: str) -> dict[int, str]:
    """Parse fairseq-interactive output and return best hypothesis per id."""

    hyps: dict[int, str] = {}
    for line in stdout.splitlines():
        # Example: H-0\t-0.123\t▁TOKEN ▁TOKEN ...
        if not line.startswith("H-"):
            continue
        try:
            header, _score, text = line.split("\t", 2)
            idx = int(header[2:])
            hyps[idx] = text.strip()
        except Exception:
            continue
    return hyps


def run_interactive(
    venv_python: Path,
    repo_root: Path,
    data_bin_dir: str,
    checkpoint_path: Path,
    source_lang: str,
    target_lang: str,
    beam: int,
    input_path: Path,
    batch_size: int,
    buffer_size: int,
) -> str:
    compat = repo_root / "fairseq_compat_run.py"
    if not compat.exists():
        raise FileNotFoundError(f"Missing: {compat}")

    cmd = [
        str(venv_python),
        str(compat),
        "interactive",
        data_bin_dir,
        "--path",
        str(checkpoint_path),
        "--source-lang",
        source_lang,
        "--target-lang",
        target_lang,
        "--beam",
        str(beam),
        "--nbest",
        "1",
        "--buffer-size",
        str(buffer_size),
        "--batch-size",
        str(batch_size),
        "--input",
        str(input_path),
    ]

    env = os.environ.copy()
    # Avoid Windows console encoding crashes when SentencePiece marker (▁)
    # appears in fairseq output.
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")

    proc = subprocess.run(
        cmd,
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    # fairseq writes warnings to stderr; treat non-zero as error.
    if proc.returncode != 0:
        raise RuntimeError(
            "interactive failed\n"
            f"cmd: {' '.join(cmd)}\n"
            f"exit: {proc.returncode}\n"
            f"stderr:\n{proc.stderr[-4000:]}\n"
            f"stdout:\n{proc.stdout[-4000:]}\n"
        )
    return proc.stdout


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--split", choices=["test", "valid"], default="test")
    ap.add_argument("--beam", type=int, default=5)
    ap.add_argument("--data-text-dir", default="data/asl_100k")
    ap.add_argument("--data-bin-dir", default="data-bin/asl_100k")
    ap.add_argument("--source-lang", default="en")
    ap.add_argument("--target-lang", default="asl")
    ap.add_argument(
        "--checkpoint",
        default="",
        help="Path to checkpoint (.pt). If empty, uses latest snapshot in D:.",
    )
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parent
    venv_python = repo_root / ".venv-lightconv" / "Scripts" / "python.exe"
    if not venv_python.exists():
        raise FileNotFoundError(f"Missing venv python: {venv_python}")

    # pick checkpoint
    if args.checkpoint:
        ckpt = Path(args.checkpoint)
    else:
        snapshots_dir = Path(r"D:\translation-pipeline-checkpoints\lightconv_100k_e15\snapshots")
        ckpt = find_latest_snapshot(snapshots_dir)

    text_dir = repo_root / args.data_text_dir
    src_path = text_dir / f"{args.split}.sp.{args.source_lang}"
    ref_path = text_dir / f"{args.split}.sp.{args.target_lang}"
    if not src_path.exists() or not ref_path.exists():
        raise FileNotFoundError(f"Missing split files: {src_path} / {ref_path}")

    n = max(1, args.n)
    src_lines = read_n_lines(src_path, n)
    ref_lines = read_n_lines(ref_path, n)
    n_eff = min(len(src_lines), len(ref_lines))
    src_lines = src_lines[:n_eff]
    ref_lines = ref_lines[:n_eff]

    logs_dir = repo_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    inp = logs_dir / f"quality_input_{args.split}_{n_eff}.sp.{args.source_lang}.txt"
    inp.write_text("\n".join(src_lines) + "\n", encoding="utf-8")

    stdout = run_interactive(
        venv_python=venv_python,
        repo_root=repo_root,
        data_bin_dir=args.data_bin_dir,
        checkpoint_path=ckpt,
        source_lang=args.source_lang,
        target_lang=args.target_lang,
        beam=args.beam,
        input_path=inp,
        batch_size=min(32, n_eff),
        buffer_size=n_eff,
    )

    hyps = parse_interactive_hyps(stdout)

    examples: list[Example] = []
    for i in range(n_eff):
        examples.append(Example(idx=i, src_sp=src_lines[i], ref_sp=ref_lines[i], hyp_sp=hyps.get(i)))

    ckpt_stem = ckpt.stem
    out_path = logs_dir / f"quality_report_{ckpt_stem}_{args.split}_{n_eff}.txt"

    def iter_report_rows(exs: Iterable[Example]) -> Iterable[str]:
        yield f"checkpoint: {ckpt}"
        yield f"split: {args.split}"
        yield f"n: {n_eff}"
        yield ""
        for ex in exs:
            src = decode_sentencepiece_tokens(ex.src_sp)
            ref = decode_sentencepiece_tokens(ex.ref_sp)
            hyp = decode_sentencepiece_tokens(ex.hyp_sp or "") if ex.hyp_sp else "(no hyp produced)"
            yield f"#{ex.idx}"
            yield f"SRC(en): {src}"
            yield f"REF(asl): {ref}"
            yield f"HYP(asl): {hyp}"
            yield ""

    report = "\n".join(iter_report_rows(examples))
    out_path.write_text(report, encoding="utf-8")

    print(report)
    print(f"\nWrote: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
