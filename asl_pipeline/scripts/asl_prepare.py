#!/usr/bin/env python3
"""
Prepare dataset for ASL POC: split, train SentencePiece, apply SentencePiece, and optionally run fairseq-preprocess.

Usage examples:

# If you have a single TSV with src\ttgt per line:
python asl_pipeline/scripts/asl_prepare.py --input data/my_dataset.tsv --input-format tsv --src-lang en --tgt-lang asl --outdir data/asl --vocab-size 8000 --seed 42

# If you have two files (one sentence per line):
python asl_pipeline/scripts/asl_prepare.py --src-file data/all.en --tgt-file data/all.asl --src-lang en --tgt-lang asl --outdir data/asl --vocab-size 8000

After running, you'll have files in outdir: train.en/train.asl, valid.en/valid.asl, test.en/test.asl and SentencePiece model files.
If fairseq is installed, you can add --run-fairseq-preprocess to invoke `fairseq-preprocess` automatically.

Tip: use --limit (and optionally --limit-mode random) to build a smaller subset dataset for faster iteration.
"""

import argparse
import os
import random
import sys
import unicodedata
import re
from pathlib import Path
from itertools import zip_longest


_WS_RE = re.compile(r"\s+")
_STRIP_QUOTES_SEMI_RE = re.compile(r"[\";\u201C\u201D\u201E\u00AB\u00BB]")

# Canonicalize structured ASL gloss markers to reduce punctuation-heavy
# subword splits (e.g., PRO-3(he) -> PRO_3_he).
# Do NOT use \b after ')' (punctuation is not a word char, so \b won't match).
_RE_PRO_POSS_PAREN = re.compile(r"(?P<prefix>PRO|POSS)-(?P<idx>[123])\((?P<lemma>[^)]+)\)")
# No word-boundaries here: markers may be glued to neighbors (e.g., WHATBEPRO-3(it)).
_RE_PRO_POSS_BARE = re.compile(r"(?P<prefix>PRO|POSS)-(?P<idx>[123])")
# Also avoid word-boundaries: wh-q(...) can be glued (e.g., ANDwh-q(when)LIKE).
_RE_WHQ = re.compile(r"(?i)wh-q\((?P<lemma>[^)]+)\)")


def count_ws_tokens(text: str) -> int:
    text = text.strip()
    if not text:
        return 0
    return len(text.split())


def normalize_text(text: str, *, strip_quotes_semicolons: bool = False) -> str:
    text = unicodedata.normalize("NFKC", text)
    if strip_quotes_semicolons:
        text = _STRIP_QUOTES_SEMI_RE.sub("", text)
    text = text.strip()
    text = _WS_RE.sub(" ", text)
    return text


def canonicalize_asl_markers(text: str) -> str:
    """Canonicalize common structured markers in ASL gloss.

    Examples:
        - PRO-3(he)   -> PRO_3_he
        - POSS-1(our) -> POSS_1_our
        - PRO-1       -> PRO_1
        - wh-q(when)  -> WHQ_when

    This reduces the frequency of standalone tokens like ')', '(', and '-3(' in the
    SentencePiece stream, which can otherwise dominate decoding.
    """

    # Markers can be glued to neighbors (e.g., WHATBEPRO-3(it), ANDwh-q(when)LIKE).
    # Add whitespace around *the original marker patterns* (while boundaries are
    # still unambiguous) before replacing them.

    # Space BEFORE markers when glued to a previous word.
    text = re.sub(r"(?<=[0-9A-Za-z])(?=(?:PRO|POSS)-[123])", " ", text)
    text = re.sub(r"(?<=[0-9A-Za-z])(?=(?i:wh-q)\()", " ", text)

    # Space AFTER parenthesized markers when glued to the next word.
    text = re.sub(r"((?:PRO|POSS)-[123]\([^)]+\))(?=[0-9A-Za-z])", r"\1 ", text)
    text = re.sub(r"((?i:wh-q)\([^)]+\))(?=[0-9A-Za-z])", r"\1 ", text)

    # Space AFTER bare markers when glued to the next word (e.g., PRO-2BECERTAINLY).
    text = re.sub(r"((?:PRO|POSS)-[123])(?=[0-9A-Za-z])", r"\1 ", text)

    def _clean_lemma(lemma: str) -> str:
        lemma = lemma.strip()
        lemma = _WS_RE.sub("_", lemma)
        return lemma

    # Canonicalize
    text = _RE_WHQ.sub(lambda m: f"WHQ_{_clean_lemma(m.group('lemma'))}", text)
    text = _RE_PRO_POSS_PAREN.sub(
        lambda m: f"{m.group('prefix')}_{m.group('idx')}_{_clean_lemma(m.group('lemma'))}",
        text,
    )
    text = _RE_PRO_POSS_BARE.sub(lambda m: f"{m.group('prefix')}_{m.group('idx')}", text)

    text = _WS_RE.sub(" ", text).strip()
    return text


def read_tsv(
    path,
    *,
    normalize: bool = False,
    strip_quotes_semicolons: bool = False,
    tgt_canonicalize_markers: bool = False,
):
    pairs = []
    dropped_no_tab = 0
    dropped_empty = 0
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                dropped_empty += 1
                continue
            if "\t" not in line:
                print(f"Skipping line {i}: no tab separator", file=sys.stderr)
                dropped_no_tab += 1
                continue
            src, tgt = line.split("\t", 1)
            src = src.strip()
            tgt = tgt.strip()
            if normalize:
                src = normalize_text(src, strip_quotes_semicolons=strip_quotes_semicolons)
                tgt = normalize_text(tgt, strip_quotes_semicolons=strip_quotes_semicolons)
            if tgt_canonicalize_markers:
                tgt = canonicalize_asl_markers(tgt)
            if not src or not tgt:
                dropped_empty += 1
                continue
            pairs.append((src, tgt))
    if dropped_no_tab or dropped_empty:
        print(f"TSV stats: kept={len(pairs)}, dropped_empty={dropped_empty}, dropped_no_tab={dropped_no_tab}")
    return pairs


def read_parallel(
    src_path,
    tgt_path,
    *,
    normalize: bool = False,
    strip_quotes_semicolons: bool = False,
    strict_align: bool = False,
    tgt_canonicalize_markers: bool = False,
):
    pairs = []
    dropped_empty = 0
    dropped_misaligned = 0
    src_extra = 0
    tgt_extra = 0

    with open(src_path, "r", encoding="utf-8") as fs, open(tgt_path, "r", encoding="utf-8") as ft:
        for i, (s, t) in enumerate(zip_longest(fs, ft, fillvalue=None), 1):
            if s is None:
                tgt_extra += 1
                dropped_misaligned += 1
                if strict_align:
                    raise ValueError(f"Misalignment: target has extra line at {i}")
                continue
            if t is None:
                src_extra += 1
                dropped_misaligned += 1
                if strict_align:
                    raise ValueError(f"Misalignment: source has extra line at {i}")
                continue

            s = s.strip()
            t = t.strip()
            if normalize:
                s = normalize_text(s, strip_quotes_semicolons=strip_quotes_semicolons)
                t = normalize_text(t, strip_quotes_semicolons=strip_quotes_semicolons)
            if tgt_canonicalize_markers:
                t = canonicalize_asl_markers(t)
            if not s or not t:
                dropped_empty += 1
                continue
            pairs.append((s, t))

    if dropped_empty or dropped_misaligned:
        print(
            "Parallel stats: "
            f"kept={len(pairs)}, dropped_empty={dropped_empty}, dropped_misaligned={dropped_misaligned}, "
            f"src_extra={src_extra}, tgt_extra={tgt_extra}"
        )
    return pairs


def write_splits(pairs, outdir, src_lang, tgt_lang, train_frac=0.8, valid_frac=0.1, seed=42):
    random.seed(seed)
    random.shuffle(pairs)
    n = len(pairs)
    ntrain = int(n * train_frac)
    nvalid = int(n * valid_frac)
    train = pairs[:ntrain]
    valid = pairs[ntrain:ntrain + nvalid]
    test = pairs[ntrain + nvalid:]

    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    def write_list(pairs_list, prefix):
        src_path = outdir / f"{prefix}.{src_lang}"
        tgt_path = outdir / f"{prefix}.{tgt_lang}"
        with open(src_path, "w", encoding="utf-8") as fs, open(tgt_path, "w", encoding="utf-8") as ft:
            for s, t in pairs_list:
                fs.write(s + "\n")
                ft.write(t + "\n")
    write_list(train, "train")
    write_list(valid, "valid")
    write_list(test, "test")
    print(f"Wrote: train({len(train)}), valid({len(valid)}), test({len(test)}) to {outdir}")
    return outdir


def train_sentencepiece(corpus_files, model_prefix, vocab_size=8000, character_coverage=1.0, model_type='bpe'):
    try:
        import sentencepiece as spm
    except Exception as e:
        raise RuntimeError("sentencepiece not installed. Install with: pip install sentencepiece") from e

    combined = model_prefix + ".spm_input.txt"
    # concatenate corpus files (may be large)
    with open(combined, "w", encoding="utf-8") as out:
        for f in corpus_files:
            with open(f, "r", encoding="utf-8") as inf:
                for line in inf:
                    out.write(line)

    # Train SentencePiece model (uses subword BPE by default)
    spm.SentencePieceTrainer.train(
        input=combined,
        model_prefix=model_prefix,
        vocab_size=vocab_size,
        character_coverage=character_coverage,
        model_type=model_type,
    )
    try:
        os.remove(combined)
    except OSError:
        pass
    print(f"Trained SentencePiece model: {model_prefix}.model (vocab={vocab_size})")


def apply_sentencepiece_to_file(sp_model_path, inp_path, out_path):
    import sentencepiece as spm
    sp = spm.SentencePieceProcessor()
    sp.load(sp_model_path)
    with open(inp_path, "r", encoding="utf-8") as inf, open(out_path, "w", encoding="utf-8") as outf:
        for line in inf:
            line = line.strip()
            if not line:
                outf.write("\n")
                continue
            pieces = sp.encode_as_pieces(line)
            outf.write(" ".join(pieces) + "\n")


def apply_sentencepiece_to_split(sp_model_path, outdir, prefixes, src_lang, tgt_lang):
    for p in prefixes:
        s_in = Path(outdir) / f"{p}.{src_lang}"
        t_in = Path(outdir) / f"{p}.{tgt_lang}"
        s_out = Path(outdir) / f"{p}.sp.{src_lang}"
        t_out = Path(outdir) / f"{p}.sp.{tgt_lang}"
        apply_sentencepiece_to_file(sp_model_path, s_in, s_out)
        apply_sentencepiece_to_file(sp_model_path, t_in, t_out)
    print(f"Applied SentencePiece to splits: {prefixes}")


def apply_sentencepiece_to_split_separate(sp_model_src_path, sp_model_tgt_path, outdir, prefixes, src_lang, tgt_lang):
    for p in prefixes:
        s_in = Path(outdir) / f"{p}.{src_lang}"
        t_in = Path(outdir) / f"{p}.{tgt_lang}"
        s_out = Path(outdir) / f"{p}.sp.{src_lang}"
        t_out = Path(outdir) / f"{p}.sp.{tgt_lang}"
        apply_sentencepiece_to_file(sp_model_src_path, s_in, s_out)
        apply_sentencepiece_to_file(sp_model_tgt_path, t_in, t_out)
    print(f"Applied SentencePiece to splits (separate models): {prefixes}")


def run_fairseq_preprocess(outdir, src_lang, tgt_lang, destdir, *, joined_dictionary: bool):
    import sys
    from subprocess import run
    dest = Path(destdir)
    dest.mkdir(parents=True, exist_ok=True)
    trainpref = str(Path(outdir) / f"train.sp")
    # fairseq-preprocess expects files like train.en train.de etc. We'll pass --trainpref <prefix> where prefix is path without lang
    # Our files are train.sp.en and train.sp.asl, so prefix is <outdir>/train.sp
    trainpref = str(Path(outdir) / "train.sp")
    validpref = str(Path(outdir) / "valid.sp")
    testpref = str(Path(outdir) / "test.sp")
    cmd = [
        sys.executable,
        "-m",
        "fairseq_cli.preprocess",
        "--source-lang", src_lang,
        "--target-lang", tgt_lang,
        "--trainpref", trainpref,
        "--validpref", validpref,
        "--testpref", testpref,
        "--destdir", str(destdir),
    ]

    if joined_dictionary:
        cmd.append("--joined-dictionary")
    print("Running:", " ".join(cmd))
    r = run(cmd)
    if r.returncode != 0:
        raise RuntimeError("fairseq preprocess failed. Ensure fairseq is installed in this Python environment.")
    print("fairseq-preprocess finished. Output in:", destdir)


def parse_args():
    p = argparse.ArgumentParser()
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--input", help="TSV input with src\ttgt per line")
    group.add_argument("--src-file", help="Source file: one sentence per line (English)")
    p.add_argument("--tgt-file", help="Target file: one sentence per line (ASL gloss)")
    p.add_argument("--input-format", choices=["tsv"], default=None, help="Format of --input")
    p.add_argument("--src-lang", default="en")
    p.add_argument("--tgt-lang", default="asl")
    p.add_argument("--outdir", default="data/asl")
    p.add_argument("--vocab-size", type=int, default=8000)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument(
        "--limit",
        type=int,
        default=None,
        help="If set, keep only N parallel pairs (after basic cleaning). Useful for quick experiments.",
    )
    p.add_argument(
        "--limit-mode",
        choices=["random", "first"],
        default="random",
        help="How to pick the subset when using --limit. random uses --seed; first keeps the first N lines.",
    )
    p.add_argument(
        "--min-tokens",
        type=int,
        default=None,
        help="If set, drop pairs where either side has fewer than this many whitespace tokens.",
    )
    p.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        help="If set, drop pairs where either side has more than this many whitespace tokens.",
    )
    p.add_argument("--model-prefix", help="prefix for sentencepiece model files (default: <outdir>/sp)" )
    p.add_argument(
        "--sp-separate",
        action="store_true",
        help="Train separate SentencePiece models for source and target (default is a joint model).",
    )

    dict_group = p.add_mutually_exclusive_group()
    dict_group.add_argument(
        "--joined-dictionary",
        action="store_true",
        help="Use a single (joined) dictionary for source and target in fairseq-preprocess.",
    )
    dict_group.add_argument(
        "--separate-dictionary",
        action="store_true",
        help="Use separate dictionaries for source and target in fairseq-preprocess.",
    )
    p.add_argument("--run-fairseq-preprocess", action="store_true", help="If set, attempt to run fairseq-preprocess automatically (requires fairseq installed).")
    p.add_argument(
        "--destdir",
        default=str(Path("data-bin") / "asl"),
        help="Destination directory for fairseq-preprocess output (default: data-bin/asl).",
    )
    p.add_argument("--normalize", action="store_true", help="Apply basic normalization (NFKC + trim + collapse whitespace).")
    p.add_argument(
        "--strip-quotes-semicolons",
        action="store_true",
        help='When used with --normalize, remove double-quotes (including common Unicode quotes) and semicolons (;) from src/tgt.',
    )
    p.add_argument(
        "--tgt-canonicalize-markers",
        action="store_true",
        help="Canonicalize common ASL markers in the target (e.g., PRO-3(he)->PRO_3_he, wh-q(when)->WHQ_when).",
    )
    p.add_argument("--strict-align", action="store_true", help="Fail if src/tgt files have different number of lines (only for --src-file/--tgt-file).")
    return p.parse_args()


def main():
    args = parse_args()
    outdir = args.outdir
    src_lang = args.src_lang
    tgt_lang = args.tgt_lang

    if args.input:
        if args.input_format == "tsv":
            pairs = read_tsv(
                args.input,
                normalize=args.normalize,
                strip_quotes_semicolons=args.strip_quotes_semicolons,
                tgt_canonicalize_markers=args.tgt_canonicalize_markers,
            )
        else:
            raise ValueError("Only tsv input-format supported for --input currently")
    else:
        if not args.tgt_file:
            raise ValueError("When using --src-file you must provide --tgt-file")
        pairs = read_parallel(
            args.src_file,
            args.tgt_file,
            normalize=args.normalize,
            strip_quotes_semicolons=args.strip_quotes_semicolons,
            strict_align=args.strict_align,
            tgt_canonicalize_markers=args.tgt_canonicalize_markers,
        )

    if args.min_tokens is not None and args.min_tokens < 0:
        raise ValueError("--min-tokens must be >= 0")
    if args.max_tokens is not None and args.max_tokens < 1:
        raise ValueError("--max-tokens must be >= 1")
    if args.min_tokens is not None and args.max_tokens is not None and args.min_tokens > args.max_tokens:
        raise ValueError("--min-tokens cannot be greater than --max-tokens")

    if args.min_tokens is not None or args.max_tokens is not None:
        before = len(pairs)
        dropped_short = 0
        dropped_long = 0
        kept = []
        for s, t in pairs:
            s_len = count_ws_tokens(s)
            t_len = count_ws_tokens(t)
            if args.min_tokens is not None and (s_len < args.min_tokens or t_len < args.min_tokens):
                dropped_short += 1
                continue
            if args.max_tokens is not None and (s_len > args.max_tokens or t_len > args.max_tokens):
                dropped_long += 1
                continue
            kept.append((s, t))
        pairs = kept
        print(
            "Length filter stats: "
            f"before={before}, kept={len(pairs)}, dropped_short={dropped_short}, dropped_long={dropped_long}, "
            f"min_tokens={args.min_tokens}, max_tokens={args.max_tokens}"
        )

    if args.limit is not None and args.limit <= 0:
        raise ValueError("--limit must be a positive integer")

    if args.limit is not None and len(pairs) > args.limit:
        if args.limit_mode == "first":
            pairs = pairs[:args.limit]
        else:
            rng = random.Random(args.seed)
            rng.shuffle(pairs)
            pairs = pairs[:args.limit]
        print(f"Using subset: {len(pairs)} pairs (limit={args.limit}, mode={args.limit_mode})")

    if len(pairs) < 10:
        print("Warning: very small dataset (<10 pairs). Results will be poor.")

    outdir_path = write_splits(pairs, outdir, src_lang, tgt_lang, seed=args.seed)

    model_prefix = args.model_prefix or str(Path(outdir_path) / "sp")
    # Train SentencePiece on train split.
    train_src = Path(outdir_path) / f"train.{src_lang}"
    train_tgt = Path(outdir_path) / f"train.{tgt_lang}"

    try:
        import sentencepiece as spm
    except Exception:
        print("sentencepiece not installed. Please install: pip install sentencepiece", file=sys.stderr)
        sys.exit(1)

    if args.sp_separate:
        src_prefix = model_prefix + f"_{src_lang}"
        tgt_prefix = model_prefix + f"_{tgt_lang}"
        print("Training SentencePiece models (separate src/tgt)... this may take a while")
        train_sentencepiece([str(train_src)], src_prefix, vocab_size=args.vocab_size)
        train_sentencepiece([str(train_tgt)], tgt_prefix, vocab_size=args.vocab_size)

        sp_model_src = src_prefix + ".model"
        sp_model_tgt = tgt_prefix + ".model"
        apply_sentencepiece_to_split_separate(
            sp_model_src,
            sp_model_tgt,
            outdir_path,
            ["train", "valid", "test"],
            src_lang,
            tgt_lang,
        )
    else:
        print("Training SentencePiece model (joint src+tgt)... this may take a while")
        train_sentencepiece([str(train_src), str(train_tgt)], model_prefix, vocab_size=args.vocab_size)

        sp_model = model_prefix + ".model"
        apply_sentencepiece_to_split(sp_model, outdir_path, ["train", "valid", "test"], src_lang, tgt_lang)

    if args.run_fairseq_preprocess:
        # Default behavior:
        # - joint SP -> joined dictionary (keeps legacy behavior)
        # - separate SP -> separate dictionaries (recommended)
        if args.joined_dictionary:
            joined = True
        elif args.separate_dictionary:
            joined = False
        else:
            joined = not args.sp_separate

        run_fairseq_preprocess(outdir_path, src_lang, tgt_lang, args.destdir, joined_dictionary=joined)

    print("Done. Prepared data in:", outdir_path)
    if args.sp_separate:
        print("SentencePiece model files:", src_prefix + ".model", src_prefix + ".vocab", "|", tgt_prefix + ".model", tgt_prefix + ".vocab")
    else:
        print("SentencePiece model files:", model_prefix + ".model", model_prefix + ".vocab")
    print("Tokenized files (space-separated pieces) have suffix .sp.<lang>")


if __name__ == '__main__':
    main()
