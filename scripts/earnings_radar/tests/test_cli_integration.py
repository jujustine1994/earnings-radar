"""Subprocess integration test for the documented CLI invocation.

Unlike the pure-function unit tests, this exercises the real production import
path: running a script by file path from the repo root with PYTHONPATH=scripts,
exactly as RUNNER.md instructs the scheduled agent. This catches the
ModuleNotFoundError that pytest's own sys.path insertion would otherwise mask.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

# tests/ -> earnings_radar/ -> scripts/ -> repo root
SCRIPTS_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = SCRIPTS_DIR.parent


def test_check_previews_cli_runs_from_repo_root_with_pythonpath(tmp_path):
    watchlist = tmp_path / "watchlist.json"
    state = tmp_path / "state.json"
    watchlist.write_text("[]", encoding="utf-8")
    state.write_text("{}", encoding="utf-8")

    env = dict(os.environ)
    # Same as documented: PYTHONPATH=scripts (relative to the repo-root cwd).
    env["PYTHONPATH"] = "scripts"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/earnings_radar/check_previews.py",
            "--watchlist",
            str(watchlist),
            "--state",
            str(state),
        ],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, (
        f"CLI exited {result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    # stdout must be valid JSON (empty watchlist -> empty array).
    assert json.loads(result.stdout) == []
