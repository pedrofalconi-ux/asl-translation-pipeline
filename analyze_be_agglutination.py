from __future__ import annotations

import argparse
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Pattern:
    token: str
    split: list[str] | None

    @property
    def split_phrase(self) -> str | None:
        return " ".join(self.split) if self.split else None


def split_candidate(tok: str) -> list[str] | None:
    """Heuristic split at the first 'BE' occurrence.

    Examples:
      BEHUNGRY -> [BE, HUNGRY]
      TOMORROWBETUESDAY -> [TOMORROW, BE, TUESDAY]
      TIMEBE -> [TIME, BE]

    Note: This does *not* claim linguistic correctness; it's just to compare
    glued vs separated forms in the corpus.
    """

    i = tok.find("BE")
    if i == -1:
        return None

    pre, post = tok[:i], tok[i + 2 :]
    if i == 0:
        return ["BE", post] if post else ["BE"]
    if not post:
        return [pre, "BE"]
    return [pre, "BE", post]


def iter_lines(paths: Iterable[Path]) -> Iterable[tuple[Path, str]]:
    for p in paths:
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                yield p, line.rstrip("\n")


def parse_outputs(outputs_path: Path) -> list[str]:
    text = outputs_path.read_text(encoding="utf-8")
    hyp_lines = re.findall(r"^\s*HYP:\s*(.*)$", text, flags=re.M)
    tokens: list[str] = []
    for line in hyp_lines:
        tokens.extend(line.strip().split())
    return tokens


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Compare BE/WHERE glued tokens from an outputs file against the original ASL corpus. "
            "Prints exact-token counts and separated-phrase counts." 
        )
    )
    ap.add_argument(
        "--outputs",
        type=Path,
        required=True,
        help="Path to outputs_*.txt containing lines like 'HYP: ...'",
    )
    ap.add_argument(
        "--corpus-dir",
        type=Path,
        default=Path("data/asl_100k_canon_enonly_clean"),
        help="Directory containing train/valid/test *.asl files (default: data/asl_100k_canon_enonly_clean)",
    )
    ap.add_argument(
        "--splits-only",
        action="store_true",
        help="Only analyze tokens that contain 'BE' but are not exactly 'BE'",
    )
    ap.add_argument(
        "--include",
        nargs="*",
        default=[
            "train.asl",
            "valid.asl",
            "test.asl",
            "test_unseen.asl",
            "test_unseen_enonly_ascii_canon.asl",
        ],
        help="Corpus filenames (relative to corpus-dir) to scan",
    )
    ap.add_argument(
        "--max-examples",
        type=int,
        default=2,
        help="Max example lines to print per token (default: 2)",
    )
    args = ap.parse_args()

    tokens = parse_outputs(args.outputs)

    # Identify candidate glued tokens from model output
    uniq = sorted(set(tokens))
    if args.splits_only:
        glued = [t for t in uniq if "BE" in t and t != "BE" and not t.startswith("PRO_")]
    else:
        glued = [t for t in uniq if ("BE" in t and t != "BE" and not t.startswith("PRO_")) or (t.startswith("WHERE") and t != "WHERE")]

    patterns = [Pattern(token=t, split=split_candidate(t)) for t in glued]
    token_set = {p.token for p in patterns}
    phrase_map = {p.token: p.split_phrase for p in patterns if p.split_phrase}

    corpus_paths = [args.corpus_dir / name for name in args.include]
    missing = [str(p) for p in corpus_paths if not p.exists()]
    if missing:
        raise SystemExit(f"Missing corpus files: {missing}")

    exact = Counter()
    split_counts = Counter()
    examples_exact: dict[str, list[tuple[str, str]]] = defaultdict(list)
    examples_split: dict[str, list[tuple[str, str]]] = defaultdict(list)

    for fp, line in iter_lines(corpus_paths):
        toks = line.split()
        for tok in toks:
            if tok in token_set:
                exact[tok] += 1
                if len(examples_exact[tok]) < args.max_examples:
                    examples_exact[tok].append((fp.name, line))

        for tok, phrase in phrase_map.items():
            if phrase in line:
                c = line.count(phrase)
                if c:
                    split_counts[tok] += c
                    if len(examples_split[tok]) < args.max_examples:
                        examples_split[tok].append((fp.name, line))

    print("Scanned corpus files:")
    for p in corpus_paths:
        print(f"- {p}")

    print("\nFound glued tokens from outputs:")
    for p in patterns:
        print(f"- {p.token}  split={p.split}")

    print("\nCounts (token\texact\tsplit_phrase\tphrase):")
    for p in patterns:
        phrase = p.split_phrase or ""
        print(f"{p.token}\t{exact[p.token]}\t{split_counts[p.token]}\t{phrase}")

    print("\nExamples: exact token in corpus")
    for p in patterns:
        if examples_exact[p.token]:
            for fn, ex in examples_exact[p.token]:
                print(f"[{p.token}] ({fn}) {ex}")

    print("\nExamples: split phrase in corpus")
    for p in patterns:
        if examples_split[p.token]:
            for fn, ex in examples_split[p.token]:
                print(f"[{p.token}] ({fn}) {ex}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
