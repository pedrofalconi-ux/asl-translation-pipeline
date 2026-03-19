#!/usr/bin/env python3
"""Create an unseen test split from a large parallel corpus.

Goal: build a new test set with sentences never seen in the current train/valid
splits (exact match, after whitespace normalization). This helps make BLEU more
credible when the original splits are too similar.

This script is deterministic given --seed.

It can also apply SentencePiece (separate src/tgt models) to the new test files.

Example:
  python asl_pipeline/scripts/make_unseen_test_from_corpus.py \
    --corpus-en asl_pipeline/data/raw/corpus_0001.clean.en.txt \
    --corpus-asl asl_pipeline/data/raw/corpus_0001.clean.asl.txt \
    --train-en data/asl_100k_canon_enonly_clean/train.en \
    --train-asl data/asl_100k_canon_enonly_clean/train.asl \
    --valid-en data/asl_100k_canon_enonly_clean/valid.en \
    --valid-asl data/asl_100k_canon_enonly_clean/valid.asl \
    --out-en data/asl_100k_canon_enonly_clean/test_unseen.en \
    --out-asl data/asl_100k_canon_enonly_clean/test_unseen.asl \
    --size 8828 --seed 42 \
    --spm-en data/asl_100k_canon_enonly_clean/sp_en.model \
    --spm-asl data/asl_100k_canon_enonly_clean/sp_asl.model
"""

from __future__ import annotations

import argparse
import random
import re
import unicodedata
from pathlib import Path


_WS_RE = re.compile(r"\s+")


def norm(text: str) -> str:
    return _WS_RE.sub(" ", text.strip())


_EN_ALLOWED_RE = re.compile(r"[^A-Z0-9 '\-]")


def _is_ascii_printable(text: str) -> bool:
    # Excludes any non-ASCII characters and control characters.
    for ch in text:
        o = ord(ch)
        if o < 32 or o > 126:
            return False
    return True


def _clean_en(text: str) -> str:
    # Normalize, uppercase, remove most punctuation/symbols.
    text = unicodedata.normalize("NFKC", text)
    text = text.upper().strip()
    text = _EN_ALLOWED_RE.sub(" ", text)
    text = _WS_RE.sub(" ", text).strip()
    return text


def _normalize_pair(en: str, asl: str, *, canonicalize_asl=None) -> tuple[str, str] | None:
    en = _clean_en(en)
    if not en:
        return None
    if canonicalize_asl is not None:
        asl = canonicalize_asl(asl)
    asl = norm(asl)
    if not asl:
        return None
    return en, asl


def _has_germanic_nordic_chars(text: str) -> bool:
    return any(ch in "ÆØÅæøåÄÖÜäöüß" for ch in text)


def _make_detector(detector: str, *, min_en_confidence: float):
    if detector == "lingua":
        from lingua import Language, LanguageDetectorBuilder  # type: ignore

        det = LanguageDetectorBuilder.from_languages(
            Language.ENGLISH,
            Language.GERMAN,
            Language.DANISH,
            Language.SWEDISH,
            Language.BOKMAL,
            Language.NYNORSK,
        ).build()

        def is_en(text: str) -> bool:
            # lingua struggles on ultra-short lines; be conservative.
            if len(text) < 12:
                return False
            if _has_germanic_nordic_chars(text):
                return False
            confidences = det.compute_language_confidence_values(text)
            for c in confidences:
                if c.language == Language.ENGLISH:
                    return c.value >= min_en_confidence
            return False

        return is_en

    if detector == "langid":
        import langid  # type: ignore

        # Focus classifier on relevant languages.
        langid.set_languages(["en", "da", "de", "sv", "no", "nb", "nn"])

        def is_en(text: str) -> bool:
            if len(text) < 12:
                return False
            if _has_germanic_nordic_chars(text):
                return False
            lang, _score = langid.classify(text)
            return lang == "en"

        return is_en

    raise ValueError(f"Unknown detector: {detector}")


def read_set(path: Path) -> set[str]:
    with path.open("r", encoding="utf-8", errors="replace") as f:
        return {norm(line) for line in f if line.strip()}


def read_pair_set(en_path: Path, asl_path: Path) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    with en_path.open("r", encoding="utf-8", errors="replace") as f_en, asl_path.open(
        "r", encoding="utf-8", errors="replace"
    ) as f_asl:
        for en_line, asl_line in zip(f_en, f_asl):
            en = norm(en_line)
            asl = norm(asl_line)
            if en and asl:
                pairs.add((en, asl))
    return pairs


def apply_sentencepiece_file(spm_path: Path, inp: Path, out: Path) -> None:
    import sentencepiece as spm

    sp = spm.SentencePieceProcessor()
    sp.load(str(spm_path))

    with inp.open("r", encoding="utf-8", errors="replace") as f_in, out.open(
        "w", encoding="utf-8", newline="\n"
    ) as f_out:
        for line in f_in:
            line = norm(line)
            if not line:
                f_out.write("\n")
                continue
            pieces = sp.encode(line, out_type=str)
            f_out.write(" ".join(pieces) + "\n")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--corpus-en", required=True, type=Path)
    p.add_argument("--corpus-asl", required=True, type=Path)

    p.add_argument("--train-en", required=True, type=Path)
    p.add_argument("--train-asl", required=True, type=Path)
    p.add_argument("--valid-en", required=True, type=Path)
    p.add_argument("--valid-asl", required=True, type=Path)

    p.add_argument("--out-en", required=True, type=Path)
    p.add_argument("--out-asl", required=True, type=Path)

    p.add_argument("--size", type=int, default=8000)
    p.add_argument("--seed", type=int, default=42)

    p.add_argument(
        "--en-only",
        action="store_true",
        help="Keep only lines confidently classified as English (filters corpus language noise).",
    )
    p.add_argument(
        "--detector",
        choices=["lingua", "langid"],
        default="lingua",
        help="Language detector backend when using --en-only (default: lingua).",
    )
    p.add_argument(
        "--min-en-confidence",
        type=float,
        default=0.70,
        help="Minimum English confidence for lingua when using --en-only (default: 0.70).",
    )
    p.add_argument(
        "--ascii-only",
        action="store_true",
        help="Drop pairs where EN or ASL contains non-ASCII / non-printable characters.",
    )
    p.add_argument(
        "--canonicalize-asl",
        action="store_true",
        help="Apply ASL canonicalization (PRO-3(he)->PRO_3_he, wh-q(x)->WHQ_x) before sampling.",
    )

    p.add_argument("--spm-en", type=Path, default=None, help="Optional SentencePiece model for EN")
    p.add_argument("--spm-asl", type=Path, default=None, help="Optional SentencePiece model for ASL")

    return p.parse_args()


def main() -> None:
    args = parse_args()

    for p in [
        args.corpus_en,
        args.corpus_asl,
        args.train_en,
        args.train_asl,
        args.valid_en,
        args.valid_asl,
    ]:
        if not p.exists():
            raise FileNotFoundError(str(p))

    rng = random.Random(args.seed)

    is_en = None
    if args.en_only:
        is_en = _make_detector(args.detector, min_en_confidence=args.min_en_confidence)

    canonicalize_asl = None
    if args.canonicalize_asl:
        # Import from sibling script (script dir is on sys.path).
        try:
            from asl_prepare import canonicalize_asl_markers as _canonicalize  # type: ignore
        except ImportError:
            # Back-compat if the helper was named differently.
            from asl_prepare import canonicalize_asl_line as _canonicalize  # type: ignore

        canonicalize_asl = _canonicalize

    # Build exclusion sets in the SAME normalized space we use for sampling.
    train_en_raw = read_set(args.train_en)
    valid_en_raw = read_set(args.valid_en)
    train_en = {e for e in (_clean_en(x) for x in train_en_raw) if e}
    valid_en = {e for e in (_clean_en(x) for x in valid_en_raw) if e}
    exclude_en = train_en | valid_en

    train_pairs_raw = read_pair_set(args.train_en, args.train_asl)
    valid_pairs_raw = read_pair_set(args.valid_en, args.valid_asl)
    train_pairs = {
        p
        for p in (
            _normalize_pair(en, asl, canonicalize_asl=canonicalize_asl) for (en, asl) in train_pairs_raw
        )
        if p is not None
    }
    valid_pairs = {
        p
        for p in (
            _normalize_pair(en, asl, canonicalize_asl=canonicalize_asl) for (en, asl) in valid_pairs_raw
        )
        if p is not None
    }
    exclude_pairs = train_pairs | valid_pairs

    # Reservoir-style sampling: we scan the big corpus and keep eligible indices,
    # then sample from them. To avoid high memory, we keep a bounded list of
    # candidates with random acceptance.
    picked: list[tuple[str, str]] = []
    seen_en_in_new: set[str] = set()

    dropped = {
        "empty": 0,
        "ascii": 0,
        "en_only": 0,
        "overlap": 0,
        "dup_in_new": 0,
    }

    def consider(en: str, asl: str) -> None:
        nonlocal picked
        if not en or not asl:
            dropped["empty"] += 1
            return

        # Normalize English (and optionally ASL canonicalization).
        en = _clean_en(en)
        if canonicalize_asl is not None:
            asl = canonicalize_asl(asl)

        if not en or not asl:
            dropped["empty"] += 1
            return

        if args.ascii_only:
            if not _is_ascii_printable(en) or not _is_ascii_printable(asl):
                dropped["ascii"] += 1
                return

        if is_en is not None:
            if not is_en(en):
                dropped["en_only"] += 1
                return

        if en in exclude_en:
            dropped["overlap"] += 1
            return
        if (en, asl) in exclude_pairs:
            dropped["overlap"] += 1
            return
        if en in seen_en_in_new:
            dropped["dup_in_new"] += 1
            return

        if len(picked) < args.size:
            picked.append((en, asl))
            seen_en_in_new.add(en)
            return

        # Replace an existing sample with decreasing probability.
        j = rng.randrange(0, len(picked) + 1)
        if j < args.size:
            old_en = picked[j][0]
            seen_en_in_new.discard(old_en)
            picked[j] = (en, asl)
            seen_en_in_new.add(en)

    with args.corpus_en.open("r", encoding="utf-8", errors="replace") as f_en, args.corpus_asl.open(
        "r", encoding="utf-8", errors="replace"
    ) as f_asl:
        for en_line, asl_line in zip(f_en, f_asl):
            consider(norm(en_line), norm(asl_line))

    if len(picked) < args.size:
        raise RuntimeError(f"Only found {len(picked)} eligible pairs (requested {args.size}).")

    args.out_en.parent.mkdir(parents=True, exist_ok=True)
    args.out_asl.parent.mkdir(parents=True, exist_ok=True)

    with args.out_en.open("w", encoding="utf-8", newline="\n") as f_en, args.out_asl.open(
        "w", encoding="utf-8", newline="\n"
    ) as f_asl:
        for en, asl in picked:
            f_en.write(en + "\n")
            f_asl.write(asl + "\n")

    # Post-check: ensure 0 overlap with train/valid.
    out_en_set_raw = read_set(args.out_en)
    out_en_set = {e for e in (_clean_en(x) for x in out_en_set_raw) if e}
    overlap_train = len(out_en_set & train_en)
    overlap_valid = len(out_en_set & valid_en)
    print(f"Wrote: {args.out_en} / {args.out_asl}")
    print(f"Size: {len(out_en_set)}")
    print(f"Overlap with train.en: {overlap_train}")
    print(f"Overlap with valid.en: {overlap_valid}")
    if args.en_only or args.ascii_only or args.canonicalize_asl:
        print("Dropped counts:")
        for k in sorted(dropped.keys()):
            print(f"  - {k}: {dropped[k]}")

    if args.spm_en and args.spm_asl:
        if not args.spm_en.exists():
            raise FileNotFoundError(str(args.spm_en))
        if not args.spm_asl.exists():
            raise FileNotFoundError(str(args.spm_asl))

        out_en_sp = args.out_en.with_suffix(".sp.en")
        out_asl_sp = args.out_asl.with_suffix(".sp.asl")
        apply_sentencepiece_file(args.spm_en, args.out_en, out_en_sp)
        apply_sentencepiece_file(args.spm_asl, args.out_asl, out_asl_sp)
        print(f"Wrote: {out_en_sp} / {out_asl_sp}")


if __name__ == "__main__":
    main()
