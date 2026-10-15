"""To-dos from a plain text or Markdown file, top of the file first.

Accepts "- [ ] task", "* task", "1. task" or a bare line. Skips done items
("- [x]"), blank lines, headings and # comments.
"""

from __future__ import annotations

import re
from pathlib import Path

_DONE = re.compile(r"^\s*(?:[-*+]|\d+[.)])?\s*\[[xX]\]")
_PREFIX = re.compile(r"^\s*(?:[-*+]|\d+[.)])?\s*(?:\[ \]\s*)?")


def read_todos(path: str) -> list[str]:
    out = []
    for line in Path(path).expanduser().read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#") or _DONE.match(line):
            continue
        text = _PREFIX.sub("", line, count=1).strip()
        if text:
            out.append(text)
    return out
