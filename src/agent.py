"""Shared limits for the unattended agents (brief, watch) and the git push they end with.

The agents read fetched web pages, so treat every tool they hold as reachable by a prompt
injection: reads stay inside the repo and away from secrets, Bash runs only hf_tool.py, and
hf_tool.py's --out is confined to logs/out/ (HF_AGENT=1).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = "heurist-network/heurist-finance"

ALLOWED_TOOLS = ["Read(./**)", "Glob", "Grep", "WebSearch", "WebFetch",
                 "Bash(uv run python scripts/hf_tool.py:*)"]
DISALLOWED_TOOLS = ["Read(./.env)", "Read(./.env.*)", "Read(./.mcp.json)", "Read(./.git/**)",
                    "Read(./.claude-brief/**)", "Read(./logs/*.log)",
                    "Read(~/.ssh/**)", "Read(~/.aws/**)", "Read(~/.config/**)", "Read(~/.claude/**)",
                    "Read(~/.netrc)", "Read(~/.*_history)", "Read(//etc/**)", "Read(//proc/**)",
                    "Edit", "Write", "NotebookEdit"]
ENV = {"CLAUDE_CONFIG_DIR": str(ROOT / ".claude-brief"), "HF_AGENT": "1"}


def push() -> None:
    """git push, except to the public upstream: a clone holding real plans must push elsewhere."""
    origin = subprocess.run(["git", "remote", "get-url", "origin"], cwd=ROOT,
                            capture_output=True, text=True).stdout.strip()
    if UPSTREAM in origin.removesuffix(".git"):
        print(f"not pushing: origin is the public {UPSTREAM}; point origin at your private repo",
              file=sys.stderr)
        return
    subprocess.run(["git", "push", "-q"], cwd=ROOT, check=True)
