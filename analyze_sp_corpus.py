from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Stats:
    lines: int
    tokens: int
    avg_len: float
    p50: int
    p95: int
    lines_with_parens: int
    lines_with_PRO: int
    lines_with_hyphen: int


def compute_stats(path: Path, max_lines: int) -> tuple[Stats, Counter[str]]:
    counter: Counter[str] = Counter()
    line_lens: list[int] = []
    paren_lines = 0
    pro_lines = 0
    hyphen_lines = 0

    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if max_lines > 0 and i >= max_lines:
                break
            toks = line.strip().split()
            if not toks:
                continue
            counter.update(toks)
            line_lens.append(len(toks))
            joined = "".join(toks)
            if ")" in joined or "(" in joined:
                paren_lines += 1
            if "PRO" in joined:
                pro_lines += 1
            if "-" in joined:
                hyphen_lines += 1

    if not line_lens:
        raise ValueError(f"No non-empty lines found in: {path}")

    line_lens_sorted = sorted(line_lens)
    n_lines = len(line_lens_sorted)
    p50 = line_lens_sorted[n_lines // 2]
    p95 = line_lens_sorted[int(n_lines * 0.95)]
    total_tokens = sum(counter.values())

    stats = Stats(
        lines=n_lines,
        tokens=total_tokens,
        avg_len=total_tokens / n_lines,
        p50=p50,
        p95=p95,
        lines_with_parens=paren_lines,
        lines_with_PRO=pro_lines,
        lines_with_hyphen=hyphen_lines,
    )
    return stats, counter


def main() -> int:
    ap = argparse.ArgumentParser(description="Analyze SentencePiece-tokenized corpus (.sp.*).")
    ap.add_argument("path", type=Path, help="Path to .sp.* text file")
    ap.add_argument("--max-lines", type=int, default=200_000, help="0 = full file")
    ap.add_argument("--top-k", type=int, default=40)
    args = ap.parse_args()

    path: Path = args.path
    if not path.exists():
        raise SystemExit(f"Missing: {path}")

    stats, counter = compute_stats(path, max_lines=args.max_lines)

    print(f"path: {path}")
    print(f"sampled_lines: {stats.lines}")
    print(f"sampled_tokens: {stats.tokens}")
    print(f"avg_len: {stats.avg_len:.2f}")
    print(f"p50_len: {stats.p50}")
    print(f"p95_len: {stats.p95}")
    print(f"lines_with_parens: {stats.lines_with_parens} ({stats.lines_with_parens / stats.lines:.1%})")
    print(f"lines_with_PRO: {stats.lines_with_PRO} ({stats.lines_with_PRO / stats.lines:.1%})")
    print(f"lines_with_hyphen: {stats.lines_with_hyphen} ({stats.lines_with_hyphen / stats.lines:.1%})")

    print("\nTop tokens:")
    for tok, c in counter.most_common(max(1, args.top_k)):
        print(f"{c:>10} {tok}")

    pro_tok = sum(c for tok, c in counter.items() if tok.replace("▁", "").startswith("PRO"))
    paren_tok = sum(c for tok, c in counter.items() if ")" in tok or "(" in tok)
    hyphen_tok = sum(c for tok, c in counter.items() if "-" in tok)

    all_tok = stats.tokens
    print("\nToken share (rough):")
    print(f"PRO*: {pro_tok} ({pro_tok / all_tok:.1%})")
    print(f"contains_paren: {paren_tok} ({paren_tok / all_tok:.1%})")
    print(f"contains_hyphen: {hyphen_tok} ({hyphen_tok / all_tok:.1%})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
