"""Add T08 S字彎管 (Sベンド) table to waterpipe DB.

Reads:  scripts/data/T08_full.json
Writes: index.html (in-place)
  - Inserts T08 entry into DB array (after T07)
  - Adds T08 keyword aliases to NL_TABLE_ALIASES (before T07 to avoid '彎管' shadowing)
  - Extends NL angle filter to apply for T08 too
  - Adds T08 fallback (管心長_l/L1/L2 → L) to NL FALLBACK map
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
INDEX_HTML = ROOT / "index.html"
DATA_DIR = ROOT / "scripts" / "data"


def extract_db_span(html: str) -> tuple[int, int]:
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


def build_t08(t08_full: dict) -> dict:
    angles = ["90°", "45°", "22.5°", "11.25°", "5.625°"]
    rows = []
    for r in t08_full["rows"]:
        D = r["D"]
        for ang in angles:
            v = r.get(ang)
            if v is None:
                continue
            L, H = v
            rows.append({"D": D, "角度": ang, "L": L, "H": H})
    return {
        "id": "T08",
        "table_no": "表8-K形",
        "name_jp": "Sベンド",
        "name_zh": "S字彎管（90°/45°/22.5°/11.25°/5.625°）",
        "columns": ["D", "角度", "L", "H"],
        "unit": "mm",
        "rows": rows,
        "notes": [
            "A形 D=75~350、K形 D=75~2600 共用本表；waterpipe 為 K形專案，全收。",
            "'—' = JDPA 規格本來就沒做。",
            "D=2600 11.25°/5.625° L/H 數值偏小，同 T07 規律。",
        ],
    }


def patch_js_aliases(html: str) -> str:
    # 1. NL_TABLE_ALIASES：T08 必須放在 T07 之前，否則 '彎管' 會搶
    old_t07_line = "  {id:'T07', keys:['彎管','彎頭','elbow','bend']},"
    new_lines = (
        "  {id:'T08', keys:['S字彎管','S彎管','S字','Sベンド','sbend','s-bend','S形彎管']},\n"
        + old_t07_line
    )
    assert old_t07_line in html, "T07 keyword line not found"
    html = html.replace(old_t07_line, new_lines, 1)

    # 2a. NL 角度篩選 — getFilteredRows 端
    old_filter = "if(nlAngleFilter && t.id === 'T07') rows = rows.filter(r => r['角度'] === nlAngleFilter);"
    new_filter = "if(nlAngleFilter && (t.id === 'T07' || t.id === 'T08')) rows = rows.filter(r => r['角度'] === nlAngleFilter);"
    if old_filter in html:
        html = html.replace(old_filter, new_filter, 1)
    else:
        assert new_filter in html, "neither old nor new angle filter line found"

    # 2b. NL 角度篩選 — runNLQuery 設值端（沒這條 T08 NL 查詢角度不會生效）
    old_set = "nlAngleFilter = (p.tableId==='T07') ? p.angle : null;"
    new_set = "nlAngleFilter = (p.tableId==='T07' || p.tableId==='T08') ? p.angle : null;"
    if old_set in html:
        html = html.replace(old_set, new_set, 1)
    else:
        assert new_set in html, "neither old nor new angle filter setter found"

    # 3. NL FALLBACK：T08 只有 L/H，把 管心長_l/L1/L2 都映到 L
    old_fallback = "'T07': {'L':'管心長_l'},                    // 彎管：長 → 管心長_l"
    new_fallback = (
        "'T07': {'L':'管心長_l'},                    // 彎管：長 → 管心長_l\n"
        "        'T08': {'L1':'L','L2':'L','管心長_l':'L'},     // S字彎管：只有 L、H"
    )
    assert old_fallback in html, "fallback T07 line not found"
    html = html.replace(old_fallback, new_fallback, 1)

    return html


def main() -> None:
    html = INDEX_HTML.read_text(encoding="utf-8")
    start, end = extract_db_span(html)
    db = json.loads(html[start:end])

    # 若已存在 T08，先移除再重建（idempotent）
    db = [t for t in db if t["id"] != "T08"]

    t08_full = json.loads((DATA_DIR / "T08_full.json").read_text(encoding="utf-8"))
    t08 = build_t08(t08_full)

    # 插在 T07 之後（找 T07 位置 +1）
    t07_idx = next(i for i, t in enumerate(db) if t["id"] == "T07")
    db.insert(t07_idx + 1, t08)

    new_db_str = json.dumps(db, ensure_ascii=False, separators=(",", ":"))
    new_html = html[:start] + new_db_str + html[end:]

    # JS 程式碼 patch
    new_html = patch_js_aliases(new_html)

    INDEX_HTML.write_text(new_html, encoding="utf-8")
    print(f"T08 added: {len(t08['rows'])} rows")
    print(f"  table_no: {t08['table_no']}")
    print(f"  name_zh:  {t08['name_zh']}")
    print(f"\nindex.html patched ({INDEX_HTML})")
    print(f"  tables: {len(db)} | rows: {sum(len(t['rows']) for t in db)}")


if __name__ == "__main__":
    main()
