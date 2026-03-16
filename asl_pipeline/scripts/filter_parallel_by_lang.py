#!/usr/bin/env python3
"""Filter a parallel corpus by source-language.

This is intended to remove non-English lines (e.g., Danish/German/Swedish) from
an otherwise EN→ASL(gloss) dataset, while preserving alignment.

Example (drop Danish/German/Swedish lines):
    python asl_pipeline/scripts/filter_parallel_by_lang.py \
        --src-file asl_pipeline/data/raw/subset_100k.filtered.en.txt \
        --tgt-file asl_pipeline/data/raw/subset_100k.filtered.asl.txt \
        --out-src asl_pipeline/data/raw/subset_100k.filtered.en.langclean.txt \
        --out-tgt asl_pipeline/data/raw/subset_100k.filtered.asl.langclean.txt

Notes:
- Keeps alignment: if a src line is dropped, the corresponding tgt line is dropped.
- Writes a small report of language distribution to stdout.
"""

from __future__ import annotations

import argparse
import sys
import unicodedata
import re
from collections import Counter
from pathlib import Path
from itertools import zip_longest


_MOJIBAKE_HINT_RE = re.compile(r"[\u00c2\u00c3]|\u00e2\u20ac")  # Â Ã or the common 'â€' prefix


def _contains_c1_controls(text: str) -> bool:
    return any(0x80 <= ord(ch) <= 0x9F for ch in text)


def _encode_cp1252_like(text: str) -> bytes | None:
    """Encode text to bytes as if it came from Windows-1252, but also allow
    raw C1 control codepoints (U+0080..U+009F) to pass through as bytes.

    This lets us repair strings where bytes 0x80..0x9F were incorrectly decoded
    as Unicode control characters, which otherwise breaks a cp1252 roundtrip.
    """

    out = bytearray()
    for ch in text:
        o = ord(ch)
        if 0x80 <= o <= 0x9F:
            out.append(o)
            continue
        try:
            out.extend(ch.encode("cp1252"))
        except UnicodeEncodeError:
            return None
    return bytes(out)


def _fix_mojibake(text: str) -> str:
    """Best-effort fix for common UTF-8/Windows-1252 mojibake.

    Typical symptoms: 'Â', 'Ã©', 'â€™', 'â€œ', 'â€“', etc.
    Strategy:
      1) try latin-1 -> utf-8 roundtrip when mojibake hints are present
      2) apply targeted replacements for remaining sequences
    """
    if not text:
        return text

    original = text

    if _MOJIBAKE_HINT_RE.search(text) or _contains_c1_controls(text):
        # Some corpora get an extra whitespace inserted inside mojibake sequences,
        # e.g. "COSSÃ ©" instead of "COSSÃ©". Try to stitch these back so the
        # cp1252->utf8 roundtrip can repair them.
        # - remove spaces right after Ã when followed by a non-space
        text = re.sub(r"Ã\s+(?=\S)", "Ã", text)
        # - remove spaces right after the 2nd byte when followed by ASCII letters
        text = re.sub(r"(Ã\S)\s+(?=[A-Za-z])", r"\1", text)

        # Sometimes stray combining marks get inserted (e.g. "Ã̄"), which will
        # prevent encoding. Strip combining marks immediately following typical
        # mojibake starters.
        text = re.sub(r"(?<=[ÃÂâ])[\u0300-\u036f]+", "", text)

        # Heuristic: accept if it reduces typical mojibake markers.
        def _score(s: str) -> int:
            # Penalize typical mojibake artifacts, replacement chars, and embedded C1 controls.
            return (
                s.count("Ã")
                + s.count("Â")
                + s.count("â€")
                + s.count("�")
                + sum(1 for ch in s if 0x80 <= ord(ch) <= 0x9F)
            )

        best = text
        best_score = _score(text)

        # Try common "UTF-8 bytes decoded as Windows-1252" first.
        # Use a cp1252-like encoder that also supports C1 controls.
        for encoder_name in ("cp1252_like", "latin-1"):
            try:
                if encoder_name == "cp1252_like":
                    b = _encode_cp1252_like(text)
                    if b is None:
                        continue
                else:
                    b = text.encode("latin-1")
                candidate = b.decode("utf-8")
            except (UnicodeEncodeError, UnicodeDecodeError):
                continue

            cand_score = _score(candidate)
            if cand_score < best_score:
                best = candidate
                best_score = cand_score
                if best_score == 0:
                    break

        text = best

    # Targeted cleanups (still useful after roundtrip)
    # Remove common NBSP artifact prefix.
    text = text.replace("\u00a0", " ")  # NBSP
    text = text.replace("Â ", " ").replace("Â\u00a0", " ")
    text = text.replace("â€™", "'").replace("â€˜", "'")
    text = text.replace("â€œ", '"').replace("â€\x9d", '"').replace("â€\x9c", '"')
    text = text.replace("â€“", "-").replace("â€”", "-")

    # If any mojibake markers remain, strip them so downstream training isn't polluted.
    # (This corpus is meant to be plain English; preserving these characters isn't critical.)
    text = text.replace("Â", "").replace("Ã", "")
    text = "".join(ch for ch in text if not (0x80 <= ord(ch) <= 0x9F))

    # If we made it worse somehow, fall back.
    if len(text) == 0 and len(original) > 0:
        return original
    return text


def _clean_for_detection(text: str, *, fix_mojibake: bool) -> str:
    # Normalize and remove some punctuation that can confuse language detection.
    if fix_mojibake:
        text = _fix_mojibake(text)
    text = unicodedata.normalize("NFKC", text)
    text = text.replace('"', "").replace(";", "")
    return text.strip()


_SPECIAL_CHARS_RE = None


def _has_germanic_nordic_chars(text: str) -> bool:
    # High-precision signal for German/Danish/Swedish/Norwegian.
    # (Still allows plain ASCII foreign lines to be handled by langid.)
    global _SPECIAL_CHARS_RE
    if _SPECIAL_CHARS_RE is None:
        import re

        _SPECIAL_CHARS_RE = re.compile(r"[ÆØÅæøåÄÖÜäöüß]")
    return bool(_SPECIAL_CHARS_RE.search(text))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--src-file", required=True)
    p.add_argument("--tgt-file", required=True)
    p.add_argument("--out-src", required=True)
    p.add_argument("--out-tgt", required=True)
    p.add_argument(
        "--mode",
        choices=["drop-langs", "keep-en"],
        default="keep-en",
        help=(
            "Filtering mode. keep-en keeps only English lines with sufficient confidence (default). "
            "drop-langs drops only the languages listed in --drop-langs."
        ),
    )
    p.add_argument(
        "--detector",
        choices=["lingua", "langid"],
        default="lingua",
        help="Language detector backend (default: lingua; fallback: langid).",
    )
    p.add_argument(
        "--drop-langs",
        default="da,de,sv,no,nb,nn",
        help="Comma-separated list of source languages to drop (default: da,de,sv,no,nb,nn).",
    )
    p.add_argument(
        "--langid-langs",
        default="en,da,de,sv,no,nb,nn",
        help="Comma-separated list of languages to consider in langid (default: en,da,de,sv,no,nb,nn).",
    )
    p.add_argument(
        "--min-score",
        type=float,
        default=0.0,
        help=(
            "Minimum langid score to trust a non-English classification (default: 0.0). "
            "We only drop when lang in --drop-langs AND score >= min-score, or when special chars match."
        ),
    )
    p.add_argument(
        "--min-en-confidence",
        type=float,
        default=0.60,
        help=(
            "Minimum confidence to accept English when using lingua in keep-en mode (default: 0.60). "
            "Lower this if too many short English lines are being dropped."
        ),
    )
    p.add_argument(
        "--fix-mojibake",
        action="store_true",
        help="Attempt to fix common mojibake sequences (Â/Ã/â€™/...).",
    )
    p.add_argument("--report-top", type=int, default=10)
    p.add_argument("--progress-every", type=int, default=20000)
    return p.parse_args()


def main() -> int:
    args = parse_args()

    # Detector selection.
    detector = None
    lingua_lang_en = None
    if args.detector == "lingua":
        try:
            from lingua import Language, LanguageDetectorBuilder  # type: ignore

            lingua_lang_en = Language.ENGLISH
            detector = LanguageDetectorBuilder.from_languages(
                Language.ENGLISH,
                Language.GERMAN,
                Language.DANISH,
                Language.SWEDISH,
                Language.BOKMAL,
                Language.NYNORSK,
            ).build()
        except Exception as e:
            print(f"lingua not available ({e}). Falling back to langid.", file=sys.stderr)
            args.detector = "langid"

    if args.detector == "langid":
        try:
            import langid  # type: ignore

            detector = langid
        except Exception as e:
            print("Missing dependency: langid. Install with: pip install langid", file=sys.stderr)
            raise

    drop_langs = {x.strip() for x in args.drop_langs.split(",") if x.strip()}
    langid_langs = [x.strip() for x in args.langid_langs.split(",") if x.strip()]

    if args.detector == "langid":
        try:
            detector.set_languages(langid_langs)
        except Exception:
            # Older langid versions should still support set_languages; if not, proceed with default model.
            pass

    src_path = Path(args.src_file)
    tgt_path = Path(args.tgt_file)
    out_src = Path(args.out_src)
    out_tgt = Path(args.out_tgt)

    out_src.parent.mkdir(parents=True, exist_ok=True)
    out_tgt.parent.mkdir(parents=True, exist_ok=True)

    kept = 0
    dropped = 0
    lang_counts = Counter()
    drop_lang_counts = Counter()

    tmp_src = out_src.with_suffix(out_src.suffix + ".tmp")
    tmp_tgt = out_tgt.with_suffix(out_tgt.suffix + ".tmp")

    with src_path.open("r", encoding="utf-8", errors="replace") as fs, tgt_path.open(
        "r", encoding="utf-8", errors="replace"
    ) as ft, tmp_src.open("w", encoding="utf-8") as osrc, tmp_tgt.open("w", encoding="utf-8") as otgt:
        for i, (s, t) in enumerate(zip_longest(fs, ft, fillvalue=None), 1):
            if s is None or t is None:
                raise ValueError(
                    f"Misalignment in input files at line {i}: "
                    f"src={'EOF' if s is None else 'OK'}, tgt={'EOF' if t is None else 'OK'}"
                )
            s = s.rstrip("\n")
            t = t.rstrip("\n")

            # Clean for detection and output.
            s_out = _fix_mojibake(s) if args.fix_mojibake else s
            t_out = _fix_mojibake(t) if args.fix_mojibake else t

            s_clean = _clean_for_detection(s_out, fix_mojibake=False)
            if not s_clean:
                # if source empty, drop pair
                dropped += 1
                drop_lang_counts["<empty>"] += 1
                continue

            should_drop = False

            # Always drop if special germanic/nordic chars are present.
            if _has_germanic_nordic_chars(s_clean):
                should_drop = True
                lang_counts["<special_chars>"] += 1
                drop_lang_counts["<special_chars>"] += 1
            else:
                if args.detector == "lingua":
                    lang = detector.detect_language_of(s_clean)
                    lang_counts[str(lang)] += 1
                    if args.mode == "keep-en":
                        if lang != lingua_lang_en:
                            should_drop = True
                            drop_lang_counts[str(lang)] += 1
                        else:
                            confs = detector.compute_language_confidence_values(s_clean)
                            en_conf = 0.0
                            for cv in confs:
                                if cv.language == lingua_lang_en:
                                    en_conf = float(cv.value)
                                    break
                            if en_conf < args.min_en_confidence:
                                should_drop = True
                                drop_lang_counts["Language.ENGLISH(low_conf)"] += 1
                    else:
                        # drop-langs mode under lingua: drop if detected is in drop_langs
                        # Map lingua enums to rough ISO-like keys.
                        lang_key = str(lang).split(".")[-1].lower()
                        if lang_key in drop_langs:
                            should_drop = True
                            drop_lang_counts[str(lang)] += 1
                else:
                    lang, score = detector.classify(s_clean)
                    lang_counts[lang] += 1
                    if args.mode == "keep-en":
                        should_drop = lang != "en"
                        if should_drop:
                            drop_lang_counts[lang] += 1
                    else:
                        # Drop when lang is one of drop_langs AND confidence >= min_score.
                        should_drop = lang in drop_langs and score >= args.min_score
                        if should_drop:
                            drop_lang_counts[lang] += 1

            if should_drop:
                dropped += 1
            else:
                osrc.write(s_out + "\n")
                otgt.write(t_out + "\n")
                kept += 1

            if args.progress_every and i % args.progress_every == 0:
                print(f"Processed {i} lines... kept={kept} dropped={dropped}", file=sys.stderr)

    # Atomic replace: only publish outputs once fully written.
    tmp_src.replace(out_src)
    tmp_tgt.replace(out_tgt)

    total = kept + dropped
    print(f"Input:  {src_path} / {tgt_path}")
    print(f"Output: {out_src} / {out_tgt}")
    print(f"Total pairs read: {total}")
    print(f"Kept: {kept}")
    print(f"Dropped: {dropped}")

    print("\nTop predicted languages (source):")
    for lang, c in lang_counts.most_common(args.report_top):
        print(f"  {lang}: {c}")

    if dropped:
        print("\nTop dropped languages (source):")
        for lang, c in drop_lang_counts.most_common(args.report_top):
            print(f"  {lang}: {c}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
