#!/usr/bin/env python3
"""
Compute BLEU using sacrebleu for hypothesis vs reference file(s).

Usage:
python asl_pipeline/scripts/eval_bleu.py --sys out.hyp --ref data/asl/test.asl

If you have multiple reference files, pass them as multiple --ref entries.
"""
import argparse
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--sys", required=True, help="System output (one sentence per line)")
    p.add_argument("--ref", required=True, action="append", help="Reference file(s). Can be provided multiple times")
    p.add_argument("--tokenize", default="13a", help="Tokenization for sacrebleu (default: 13a)")
    return p.parse_args()


def main():
    args = parse_args()
    try:
        import sacrebleu
    except Exception:
        raise RuntimeError("sacrebleu not installed. Install with: pip install sacrebleu")

    sys_lines = [l.rstrip("\n") for l in open(args.sys, "r", encoding="utf-8")]
    refs = []
    for r in args.ref:
        refs.append([l.rstrip("\n") for l in open(r, "r", encoding="utf-8")])

    # sacrebleu expects refs as list of reference lists, one per reference file
    # but order: refs = [ref1_lines, ref2_lines, ...]
    bleu = sacrebleu.corpus_bleu(sys_lines, refs, tokenize=args.tokenize)
    print(bleu)

if __name__ == '__main__':
    main()
