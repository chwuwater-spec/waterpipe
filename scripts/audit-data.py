"""Audit waterpipe DB for missing data — produces scripts/audit-report.md."""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
db = json.load(open(ROOT / "scripts/db.json", encoding="utf-8"))

lines: list[str] = []
def p(s: str = "") -> None:
    lines.append(s)


def fnum(x: str) -> float:
    return float(x)


def images_for(table_id: str) -> list[str]:
    img_dir = ROOT / "images"
    return sorted(f.name for f in img_dir.glob(f"{table_id}_*.webp"))


p("# waterpipe 資料完整性盤點 — 對照工作清單")
p("")
p("> 自動產出。資料源：`index.html` 內嵌 DB（執行 `python scripts/extract-db.py` 重抽）。")
p("> `null` 不必然是缺漏；表名宣告的多角度 / 多形式則是硬合約，缺一就是漏。")
p("")
p(f"範圍：{len(db)} 張表 / {sum(len(t['rows']) for t in db)} 筆 row")
p("")
p("## 使用方法")
p("")
p("對照原圖（`images/T{id}_*.webp`）逐項判定，把每個 `- [ ]` 改成：")
p("")
p("- `- [x]` ← JDPA 本來就沒做（不必補），不必補充說明")
p("- `- [!]` ← 確認漏掉，請在該項下面**附上規格圖上的數值**，例如 `D=900 22.5°: R=___, L1=___, L2=___, 管心長_l=___, 質量=___, T=___`")
p("")
p("對完傳回給 Claude，會批次補進 `index.html` DB 並提 PR。")
p("")

# --- 1. 跨表 D 覆蓋 ---
all_d = sorted({r["D"] for t in db for r in t["rows"]})
p("## 1. 各表 D（口徑）覆蓋總覽")
p("")
p("全集 D 序列：" + ", ".join(str(d) for d in all_d) + f"（共 {len(all_d)} 個）")
p("")
p("| 表 | 名稱 | D 數 | 缺的 D | 對照圖 |")
p("| :-- | :-- | --: | :-- | :-- |")
for t in db:
    ds = sorted({r["D"] for r in t["rows"]})
    missing = sorted(set(all_d) - set(ds))
    miss_str = ", ".join(str(d) for d in missing) if missing else "—"
    imgs = ", ".join(f"`{n}`" for n in images_for(t["id"]))
    p(f"| {t['id']} | {t['name_zh']} | {len(ds)} | {miss_str} | {imgs} |")
p("")
p("（**缺的 D** 不一定是漏，可能 JDPA 本來就沒做這口徑。下面分表列出來給你判定。）")
p("")

# --- 2. T07 彎管角度組合 ---
t07 = next(t for t in db if t["id"] == "T07")
declared = re.findall(r"(\d+(?:\.\d+)?)°", t07["name_zh"])
declared_set = set(declared)
p("## 2. T07 彎管：角度組合缺漏（最嚴重）")
p("")
p(f"**對照圖**：{', '.join('`' + n + '`' for n in images_for('T07'))}")
p("")
p(f"宣告角度（依表名）：{', '.join(a + '°' for a in declared)}")
seen_angles = sorted({r["角度"].rstrip("°") for r in t07["rows"]}, key=fnum, reverse=True)
p(f"資料出現角度：{', '.join(a + '°' for a in seen_angles)}")
p("")
by_d_t07 = defaultdict(set)
for r in t07["rows"]:
    by_d_t07[r["D"]].add(r["角度"].rstrip("°"))
p("逐 D 缺漏清單（對完原圖把 `[ ]` 改成 `[x]` 沒有 / `[!]` 漏了）：")
p("")
for d in sorted(by_d_t07):
    have = sorted(by_d_t07[d], key=fnum, reverse=True)
    miss = sorted(declared_set - by_d_t07[d], key=fnum, reverse=True)
    if not miss:
        continue
    have_str = ", ".join(a + "°" for a in have)
    p(f"**D = {d}** — 已有 {have_str}")
    for m in miss:
        p(f"- [ ] {m}°")
    p("")

# --- 3-5. D × d 配對表 ---
def pair_audit(table_id: str, title: str, d_label: str, dd_label: str) -> None:
    t = next(t for t in db if t["id"] == table_id)
    pairs = defaultdict(list)
    for r in t["rows"]:
        pairs[r["D"]].append(r["d"])
    p(f"## {title}")
    p("")
    p(f"**對照圖**：{', '.join('`' + n + '`' for n in images_for(table_id))}")
    p("")
    p("對完原圖在每列勾「□ 對」或標「+ 應補配對：xxx, yyy」：")
    p("")
    p(f"| □/+ | {d_label} | {dd_label} | 配對數 |")
    p("| :-: | --: | :-- | --: |")
    for d in sorted(pairs):
        ds = sorted(pairs[d])
        p(f"| [ ] | {d} | {', '.join(str(x) for x in ds)} | {len(ds)} |")
    p("")


pair_audit("T06", "3. T06 異徑管：D × d 配對", "D（大徑）", "d 配對（小徑）")
pair_audit("T05", "4. T05 雙承口T字管：D × d 配對", "D（本管）", "d 配對（支管）")
pair_audit("T10", "5. T10 附法蘭T字管：D × d 配對", "D（本管）", "d 配對")

# --- 6. null 欄位統計 ---
p("## 6. 各表 null 欄位統計")
p("")
p("null 不必然是缺漏；但某欄位 null 比例很高時值得回頭對原圖確認。")
p("")
p("| □/+ | 表 | 欄位 | null 筆數 / 總筆數 | 比例 | 對照圖 |")
p("| :-: | :-- | :-- | :-- | --: | :-- |")
for t in db:
    n = len(t["rows"])
    for col in t["columns"]:
        nulls = sum(1 for r in t["rows"] if r.get(col) is None)
        if nulls > 0:
            ratio = nulls / n
            imgs = ", ".join(f"`{x}`" for x in images_for(t["id"]))
            p(f"| [ ] | {t['id']} | `{col}` | {nulls} / {n} | {ratio:.0%} | {imgs} |")
p("")
p("---")
p("")
p("對完整份清單，存檔，把這份檔回貼給 Claude 即可批次補資料。")

out_path = ROOT / "scripts" / "audit-report.md"
out_path.write_text("\n".join(lines), encoding="utf-8")
print(f"wrote: {out_path.relative_to(ROOT)} ({len(lines)} lines)")
