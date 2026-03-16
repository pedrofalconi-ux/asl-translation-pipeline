r"""Run fairseq CLI entrypoints with a PyTorch>=2.6 checkpoint-load compatibility patch.

PyTorch 2.6 changed torch.load default weights_only from False -> True.
Fairseq 0.12.2 uses torch.load(...) without specifying weights_only, which can
fail to load fairseq checkpoints (argparse.Namespace not allowlisted by default).

This wrapper forces torch.load(..., weights_only=False) for the current process.
Use only for checkpoints you trust (e.g., ones you trained locally).

Examples (PowerShell):
    & .\.venv-lightconv\Scripts\python.exe .\fairseq_compat_run.py generate data-bin/asl --path checkpoints/lightconv_smoke/checkpoint_last.pt --beam 5 --batch-size 16
    & .\.venv-lightconv\Scripts\python.exe .\fairseq_compat_run.py interactive data-bin/asl --path checkpoints/lightconv_smoke/checkpoint_last.pt --beam 5
    & .\.venv-lightconv\Scripts\python.exe .\fairseq_compat_run.py train data-bin/asl --task translation --arch lightconv_iwslt_de_en ...
"""

from __future__ import annotations

import os
import runpy
import sys


def _patch_torch_load_weights_only_false() -> None:
    try:
        import torch
    except Exception:
        return

    orig_load = torch.load

    def patched_load(*args, **kwargs):  # type: ignore[no-untyped-def]
        if "weights_only" not in kwargs:
            kwargs["weights_only"] = False
        return orig_load(*args, **kwargs)

    torch.load = patched_load  # type: ignore[assignment]


def _patch_fairseq_pathmanager_rename_windows() -> None:
    """Patch fairseq PathManager.rename to be overwrite-safe on Windows.

    Fairseq 0.12.x uses os.rename via PathManager.rename. On Windows, os.rename
    fails if the destination exists (WinError 183). This breaks checkpoint
    saving because fairseq writes to <file>.tmp and then renames to <file>,
    where <file> already exists.

    os.replace provides the desired atomic "rename/replace" semantics.
    """

    if os.name != "nt":
        return

    try:
        from fairseq.file_io import PathManager  # type: ignore
    except Exception:
        return

    orig_rename = getattr(PathManager, "rename", None)

    def rename(src: str, dst: str) -> None:  # type: ignore[no-untyped-def]
        # Prefer atomic replace semantics on Windows.
        os.replace(src, dst)

    # Keep reference for debugging/introspection.
    rename.__wrapped__ = orig_rename  # type: ignore[attr-defined]
    PathManager.rename = staticmethod(rename)  # type: ignore[assignment]


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: fairseq_compat_run.py <train|generate|preprocess|interactive|...> [args...]", file=sys.stderr)
        return 2

    entry = argv[1].strip().lower()
    module = f"fairseq_cli.{entry}"

    _patch_torch_load_weights_only_false()
    _patch_fairseq_pathmanager_rename_windows()

    # Make the executed module see expected argv[0].
    sys.argv = [module] + argv[2:]
    try:
        runpy.run_module(module, run_name="__main__")
    except ModuleNotFoundError as e:
        msg = str(e)
        if "fairseq_cli" in msg or "fairseq" in msg:
            print(
                "fairseq is not available in this Python environment.\n"
                "Run this wrapper with the venv Python, e.g.:\n"
                "  & .\\.venv-lightconv\\Scripts\\python.exe .\\fairseq_compat_run.py ...",
                file=sys.stderr,
            )
        else:
            print(f"Unknown fairseq entrypoint '{entry}'. Tried module '{module}'.", file=sys.stderr)
        print(msg, file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
