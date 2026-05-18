"""Extract DB array from index.html into db.json for further analysis."""
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
html = (ROOT / "index.html").read_text(encoding="utf-8")

start = html.index("const DB = ")
i = html.index("[", start)
depth = 0
in_str = False
escape = False
for j in range(i, len(html)):
    ch = html[j]
    if in_str:
        if escape:
            escape = False
        elif ch == "\\":
            escape = True
        elif ch == '"':
            in_str = False
        continue
    if ch == '"':
        in_str = True
    elif ch == "[":
        depth += 1
    elif ch == "]":
        depth -= 1
        if depth == 0:
            end = j + 1
            break
else:
    raise RuntimeError("unterminated array")

db = json.loads(html[i:end])
(ROOT / "scripts" / "db.json").write_text(
    json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(f"tables: {len(db)}")
print(f"total rows: {sum(len(t['rows']) for t in db)}")
for t in db:
    print(f"  {t['id']:5s} {t['table_no']:12s} {t['name_zh']}  rows={len(t['rows'])}")
