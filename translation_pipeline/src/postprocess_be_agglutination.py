from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, TextIO


WH_PREFIXES = ("WHERE", "WHAT", "HOW", "WHO", "WHY", "WHEN")
TIME_PREFIXES = ("TODAY", "TOMORROW", "YESTERDAY")

# Optional built-in *extra* whitelist (examples from the corpus analysis).
# Note: this is NOT the main preservation mechanism. We already preserve *any* token that
# appears in the corpus-derived vocabulary (`token in corpus_vocab`). This small set exists
# only as a safety net / convenience when users run without providing extra whitelist files.
DEFAULT_EXTRA_GLUE_WHITELIST = {
    "BENOT",
    "BEVERY",
    "BEWELCOME",
    "BELOST",
}

# Backwards-compatible alias (older name used in early iterations).
DEFAULT_GLUE_WHITELIST = DEFAULT_EXTRA_GLUE_WHITELIST


@dataclass(frozen=True)
class Correction:
    original: str
    corrected_tokens: tuple[str, ...]

    @property
    def corrected(self) -> str:
        return " ".join(self.corrected_tokens)


@dataclass(frozen=True)
class RepairIndexes:
    """Indexes to conservatively repair REST (X) by 1 character.

    - add_first_unique: maps rest -> full_token when full_token[1:] == rest and the mapping is unique.
    - add_last_unique: maps rest -> full_token when full_token[:-1] == rest and the mapping is unique.

    We only store unique mappings to avoid ambiguous rewrites.
    """

    add_first_unique: dict[str, str]
    add_last_unique: dict[str, str]


def build_repair_indexes(corpus_vocab: set[str]) -> RepairIndexes:
    # Only index plain alphabetic tokens to avoid PRO_*, punctuation, etc.
    alpha = [t for t in corpus_vocab if t.isalpha() and len(t) >= 2]

    add_first: dict[str, set[str]] = {}
    add_last: dict[str, set[str]] = {}

    for t in alpha:
        add_first.setdefault(t[1:], set()).add(t)
        add_last.setdefault(t[:-1], set()).add(t)

    add_first_unique = {k: next(iter(v)) for k, v in add_first.items() if len(v) == 1}
    add_last_unique = {k: next(iter(v)) for k, v in add_last.items() if len(v) == 1}

    return RepairIndexes(add_first_unique=add_first_unique, add_last_unique=add_last_unique)


def iter_corpus_tokens(paths: Iterable[Path]) -> Iterable[str]:
    for path in paths:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                for tok in line.split():
                    yield tok


def build_vocab_from_corpus_files(paths: Iterable[Path]) -> set[str]:
    vocab: set[str] = set()
    for tok in iter_corpus_tokens(paths):
        vocab.add(tok)
    return vocab


def load_whitelist_files(paths: Iterable[Path]) -> set[str]:
    out: set[str] = set()
    for p in paths:
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                # allow whitespace-separated tokens per line
                out.update(line.split())
    return out


def split_invalid_be_token(
    token: str,
    *,
    corpus_vocab: set[str],
    glued_whitelist: set[str],
    repair_indexes: RepairIndexes | None = None,
) -> Correction | None:
    """Split invalid glued tokens that match `PREFIX + BE + X`.

    Rules implemented (conservative):
    - Never change if token exists in corpus_vocab OR in glued_whitelist.
    - Only consider exact patterns:
      - WH + BE + X  where WH in {WHERE, WHAT, HOW, WHO, WHY, WHEN}
      - TIME + BE + X where TIME in {TODAY, TOMORROW, YESTERDAY}
    - Before splitting, require X to exist in corpus_vocab.
    - Output is always: PREFIX, BE, X
    """

    if token in corpus_vocab or token in glued_whitelist:
        return None

    # Keep non-alphabetic tokens unchanged (punctuation, tags, PRO_*, etc.).
    # This also avoids being clever with edge cases; the rule is token-based.
    if not token.isalpha():
        return None

    prefixes = WH_PREFIXES + TIME_PREFIXES
    for prefix in prefixes:
        glued_prefix = prefix + "BE"
        if not token.startswith(glued_prefix):
            continue

        rest = token[len(glued_prefix) :]
        if not rest:
            return None

        # Extra conservativeness: avoid splitting cases like TODAYBEM (X='M'),
        # which can arise from partial/garbled tokenization. We only split when
        # X looks like a real token (>= 2 characters).
        if len(rest) < 2:
            return None

        # Mandatory validation (base): X must exist in corpus vocabulary.
        if rest in corpus_vocab:
            return Correction(original=token, corrected_tokens=(prefix, "BE", rest))

        # Conservative 1-character repairs of REST (X), to handle common model glitches like:
        #   WHEREBELEVATOR  (missing 'E' -> ELEVATOR)
        #   WHEREBESSTAIRS  (extra leading 'S' -> STAIRS)
        #   WHEREBETKITCHEN (extra leading 'T' -> KITCHEN)
        # We only apply when the repaired token exists in the corpus vocab.

        # 1) Drop extra first char
        if len(rest) >= 3 and rest[1:] in corpus_vocab:
            return Correction(original=token, corrected_tokens=(prefix, "BE", rest[1:]))

        # 2) Drop extra last char
        if len(rest) >= 3 and rest[:-1] in corpus_vocab:
            return Correction(original=token, corrected_tokens=(prefix, "BE", rest[:-1]))

        # 3) Add missing first char (unique)
        if repair_indexes is not None:
            cand = repair_indexes.add_first_unique.get(rest)
            if cand is not None and cand in corpus_vocab:
                return Correction(original=token, corrected_tokens=(prefix, "BE", cand))

            # 4) Add missing last char (unique)
            cand = repair_indexes.add_last_unique.get(rest)
            if cand is not None and cand in corpus_vocab:
                return Correction(original=token, corrected_tokens=(prefix, "BE", cand))

        return None

    return None


def postprocess_line(
    line: str,
    *,
    corpus_vocab: set[str],
    glued_whitelist: set[str],
    repair_indexes: RepairIndexes | None = None,
) -> tuple[str, list[Correction]]:
    tokens = line.rstrip("\n").split()
    corrections: list[Correction] = []
    out_tokens: list[str] = []

    for tok in tokens:
        corr = split_invalid_be_token(
            tok,
            corpus_vocab=corpus_vocab,
            glued_whitelist=glued_whitelist,
            repair_indexes=repair_indexes,
        )
        if corr is None:
            out_tokens.append(tok)
        else:
            corrections.append(corr)
            out_tokens.extend(list(corr.corrected_tokens))

    return " ".join(out_tokens), corrections


def _write_log(log_fp: TextIO, line_no: int, corrections: list[Correction]) -> None:
    for c in corrections:
        log_fp.write(f"line={line_no}\torig={c.original}\tnew={c.corrected}\n")


def run_stream(
    inp: TextIO,
    out: TextIO,
    *,
    corpus_vocab: set[str],
    glued_whitelist: set[str],
    repair_indexes: RepairIndexes | None = None,
    log_fp: TextIO | None = None,
) -> int:
    for i, line in enumerate(inp, start=1):
        fixed, corrections = postprocess_line(
            line,
            corpus_vocab=corpus_vocab,
            glued_whitelist=glued_whitelist,
            repair_indexes=repair_indexes,
        )
        out.write(fixed + "\n")
        if log_fp and corrections:
            _write_log(log_fp, i, corrections)
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Conservative post-processing for ASL gloss outputs: fix ONLY invalid glued tokens involving 'BE' "
            "for patterns WH+BE+X and TIME+BE+X, preserving tokens that exist in the corpus or whitelist."
        )
    )

    ap.add_argument(
        "--corpus-dir",
        type=Path,
        default=Path("data/asl_100k_canon_enonly_clean"),
        help="Directory containing corpus .asl files (default: data/asl_100k_canon_enonly_clean)",
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
        help="Corpus filenames (relative to corpus-dir) to build the vocabulary from",
    )
    ap.add_argument(
        "--whitelist",
        action="append",
        default=[],
        type=Path,
        help="Optional path to a whitelist file (one or more). Can be repeated.",
    )
    ap.add_argument(
        "--whitelist-tokens",
        nargs="*",
        default=[],
        help="Extra glued tokens to preserve (space-separated)",
    )
    ap.add_argument(
        "--no-default-whitelist",
        action="store_true",
        help="Disable the built-in whitelist (BENOT, BEVERY, BEWELCOME, BELOST)",
    )
    ap.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Input text file (default: stdin)",
    )
    ap.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output text file (default: stdout)",
    )
    ap.add_argument(
        "--log",
        type=Path,
        default=None,
        help="Optional TSV log of applied corrections",
    )

    args = ap.parse_args(argv)

    corpus_paths = [args.corpus_dir / name for name in args.include]
    missing = [str(p) for p in corpus_paths if not p.exists()]
    if missing:
        ap.error(f"Missing corpus files: {missing}")

    corpus_vocab = build_vocab_from_corpus_files(corpus_paths)
    repair_indexes = build_repair_indexes(corpus_vocab)

    glued_whitelist: set[str] = set()
    if not args.no_default_whitelist:
        glued_whitelist |= DEFAULT_GLUE_WHITELIST

    if args.whitelist:
        glued_whitelist |= load_whitelist_files(args.whitelist)

    if args.whitelist_tokens:
        glued_whitelist |= set(args.whitelist_tokens)

    inp: TextIO
    out: TextIO
    log_fp: TextIO | None

    inp = args.input.open("r", encoding="utf-8") if args.input else sys.stdin
    out = args.output.open("w", encoding="utf-8", newline="\n") if args.output else sys.stdout
    log_fp = args.log.open("w", encoding="utf-8", newline="\n") if args.log else None

    try:
        return run_stream(
            inp,
            out,
            corpus_vocab=corpus_vocab,
            glued_whitelist=glued_whitelist,
            repair_indexes=repair_indexes,
            log_fp=log_fp,
        )
    finally:
        if args.input and inp is not sys.stdin:
            inp.close()
        if args.output and out is not sys.stdout:
            out.close()
        if log_fp:
            log_fp.close()


if __name__ == "__main__":
    raise SystemExit(main())
