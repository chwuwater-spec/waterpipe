"""Apply data corrections to waterpipe DB embedded in index.html.

Reads:
  - scripts/data/T07_full.json (彎管完整重建)
  - scripts/data/T05_additions.json (雙承口T字管缺漏補列)
  - 內建 T17 typo fix (D=200 D5: 342 → 338)

Writes:
  - index.html (in-place patch of `const DB = [...]`)
"""
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
INDEX_HTML = ROOT / "index.html"
DATA_DIR = ROOT / "scripts" / "data"


def extract_db_span(html: str) -> tuple[int, int]:
    """Return (start, end) char offsets of the JSON array in `const DB = [...]`."""
    i = html.index("const DB = ")
    i = html.index("[", i)
    depth, in_str, escape = 0, False, False
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
                return i, j + 1
    raise RuntimeError("unterminated DB array")


def rebuild_t07(t07_full: dict) -> list[dict]:
    """Convert T07_full structured data into flat row list for DB."""
    rows = []
    angles = ["90°", "45°", "22.5°", "11.25°", "5.625°"]
    for r in t07_full["rows"]:
        D, T = r["D"], r["T"]
        for ang in angles:
            v = r.get(ang)
            if v is None:
                continue  # JDPA 沒做這格
            R, L1, L2, l, kg = v
            rows.append({
                "D": D, "T": T, "角度": ang,
                "R": R, "L1": L1, "L2": L2,
                "管心長_l": l, "質量": kg,
            })
    return rows


def merge_t05(existing: list[dict], additions: list[dict]) -> list[dict]:
    """Merge T05 additions into existing rows, sorted by (D, d)."""
    seen = {(r["D"], r["d"]) for r in existing}
    out = list(existing)
    for r in additions:
        key = (r["D"], r["d"])
        if key in seen:
            print(f"  skip duplicate T05 {key}")
            continue
        out.append(r)
        seen.add(key)
    out.sort(key=lambda r: (r["D"], r["d"]))
    return out


def main() -> None:
    html = INDEX_HTML.read_text(encoding="utf-8")
    start, end = extract_db_span(html)
    db = json.loads(html[start:end])

    # T07 — full rebuild
    t07_full = json.loads((DATA_DIR / "T07_full.json").read_text(encoding="utf-8"))
    t07 = next(t for t in db if t["id"] == "T07")
    before = len(t07["rows"])
    t07["rows"] = rebuild_t07(t07_full)
    print(f"T07: rebuilt {before} → {len(t07['rows'])} rows")

    # T05 — append missing rows
    t05_add = json.loads((DATA_DIR / "T05_additions.json").read_text(encoding="utf-8"))
    t05 = next(t for t in db if t["id"] == "T05")
    before = len(t05["rows"])
    t05["rows"] = merge_t05(t05["rows"], t05_add["rows"])
    print(f"T05: appended {len(t05['rows']) - before} rows ({before} → {len(t05['rows'])})")

    # T17 — typo fix D=200 D5
    t17 = next(t for t in db if t["id"] == "T17")
    for r in t17["rows"]:
        if r["D"] == 200 and r["D5"] == 342:
            r["D5"] = 338
            print("T17: D=200 D5 fixed 342 → 338")
            break
    else:
        print("T17: D=200 D5 = 342 not found (already fixed?)")

    # Re-serialize DB and patch index.html
    new_db_str = json.dumps(db, ensure_ascii=False, separators=(",", ":"))
    new_html = html[:start] + new_db_str + html[end:]
    INDEX_HTML.write_text(new_html, encoding="utf-8")
    print(f"\nindex.html patched ({INDEX_HTML})")
    print(f"  tables: {len(db)} | rows: {sum(len(t['rows']) for t in db)}")


if __name__ == "__main__":
    main()
