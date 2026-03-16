from __future__ import annotations

import argparse
from pathlib import Path


def iter_lines(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            yield line.rstrip()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--splits-dir", default="data/asl_100k", help="Directory containing train/valid/test.{en,asl}")
    p.add_argument("--out-dir", default="asl_pipeline/data/raw", help="Directory to write the exported parallel TXT files")
    p.add_argument("--out-prefix", default="subset_100k.filtered", help="Output filename prefix")
    p.add_argument("--src-lang", default="en")
    p.add_argument("--tgt-lang", default="asl")
    args = p.parse_args()

    splits_dir = Path(args.splits_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    src_out = out_dir / f"{args.out_prefix}.{args.src_lang}.txt"
    tgt_out = out_dir / f"{args.out_prefix}.{args.tgt_lang}.txt"

    splits = ["train", "valid", "test"]

    n = 0
    with src_out.open("w", encoding="utf-8", newline="\n") as fs, tgt_out.open(
        "w", encoding="utf-8", newline="\n"
    ) as ft:
        for split in splits:
            src_p = splits_dir / f"{split}.{args.src_lang}"
            tgt_p = splits_dir / f"{split}.{args.tgt_lang}"
            if not src_p.exists() or not tgt_p.exists():
                raise SystemExit(f"Missing split files: {src_p} or {tgt_p}")

            for s, t in zip(iter_lines(src_p), iter_lines(tgt_p)):
                fs.write(s + "\n")
                ft.write(t + "\n")
                n += 1

    print(f"Wrote {n} parallel pairs")
    print(src_out)
    print(tgt_out)

    # sanity counts
    for path in (src_out, tgt_out):
        with path.open("r", encoding="utf-8") as f:
            lines = sum(1 for _ in f)
        print(f"{path.name}: {lines} lines")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
