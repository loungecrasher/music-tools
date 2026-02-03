"""Launchers for tools located outside the main Music Tools package."""

from __future__ import annotations

import importlib
import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = PROJECT_ROOT.parent

EDM_DIR = WORKSPACE_ROOT / "EDM Sharing Site Web Scrapper"
EDM_SCRIPT = EDM_DIR / "cli_scraper.py"

TAGGER_DIR = WORKSPACE_ROOT / "Tag Country Origin Editor" / "Codebase" / "music_tagger" / "src"
TAGGER_SCRIPT = TAGGER_DIR / "cli.py"

CTXT_MODULE_PATH = WORKSPACE_ROOT / "New Base" / "ctxt.py"
_CTCT_MODULE: ModuleType | None = None


def _run_script(script_path: Path, *, cwd: Optional[Path] = None) -> None:
    if not script_path.exists():
        raise FileNotFoundError(f"Could not find script: {script_path}")
    subprocess.run([sys.executable, str(script_path)], cwd=cwd or script_path.parent, check=False)


def launch_edm_scraper() -> None:
    """Launch the EDM blog scraper interactive CLI."""

    _run_script(EDM_SCRIPT, cwd=EDM_DIR)


def launch_music_tagger() -> None:
    """Launch the Music Library Country Tagger CLI."""

    _run_script(TAGGER_SCRIPT, cwd=TAGGER_DIR)


def _load_ctxt_module() -> ModuleType:
    global _CTCT_MODULE
    if _CTCT_MODULE is None:
        if not CTXT_MODULE_PATH.exists():
            raise FileNotFoundError(f"CSV converter module not found: {CTXT_MODULE_PATH}")
        spec = importlib.util.spec_from_file_location("ctxt_converter", CTXT_MODULE_PATH)
        if spec is None or spec.loader is None:
            raise ImportError(f"Unable to load module from {CTXT_MODULE_PATH}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)  # type: ignore[attr-defined]
        _CTCT_MODULE = module
    return _CTCT_MODULE


def convert_csv_directory(*args, **kwargs):  # type: ignore[no-untyped-def]
    module = _load_ctxt_module()
    return module.convert_csv_directory(*args, **kwargs)


def convert_csv_cli(*args, **kwargs):  # type: ignore[no-untyped-def]
    module = _load_ctxt_module()
    return module._main(*args, **kwargs)
