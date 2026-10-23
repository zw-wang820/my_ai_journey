"""
S5 阶段：build_index_block / append_index / summarize —— 索引生成 + 汇总
==========================================================================
对应 TECH.md §5（输出标签与计数）、§6（索引写入细则）、§10 步骤 S5。

三个函数，从左到右难度递增：

  build_index_block(records, now) -> str
      纯函数：把计划记录列表渲染成一段 Markdown（段落头 + 表格）。
      **不碰文件系统**，时间从参数传入 —— 这样测试可以断言完整字符串。

  append_index(dest, records) -> None
      薄薄一层 I/O：确保目标目录存在 → 打开 <dest>/INDEX.md 追加 →
      首次创建时补一个 `# 归档索引` 大标题。
      要点：用 'a' 模式（追加），绝不能 'w'（会抹掉历史）。

  summarize(plans, dry_run) -> str
      纯函数：从计划列表统计四类数量，产出 TECH.md §5 规定的那一行。

填写说明：
  - 三个 TODO 相互独立，可以先写 build_index_block（纯字符串，最好测）；
  - records 里每一项就是 plan_one 返回的 plan dict，字段：
        week / category / src / dst / size（size 是 int 字节数）
  - 写完跑 python s5_index.py，期望 6/6 通过。
"""

import tempfile
from datetime import datetime
from pathlib import Path

from s3_skeleton import format_size


# TODO-1: build_index_block —— 渲染一段 Markdown（纯函数）
def build_index_block(records: list, now: datetime, dry_run: bool = False) -> str:
    """
    参数: records 成功归档的 plan 列表; now 时间戳（调用方传入，便于测试）
    返回: 一段 Markdown 文本，结构见 TECH.md §6：

        ## 归档记录 2026-10-21 10:30 (run)

        | 周号 | 文件名 | 源路径 | 目标路径 | 文件大小 |
        |---|---|---|---|---|
        | W34 | W34_test.py | src/W34_test.py | dst/W34/code/W34_test.py | 1.0 KB |

    提示:
      - 段落头时间格式：now.strftime('%Y-%m-%d %H:%M')
      - 文件名用 src.name 取；大小用 format_size(rec['size'])
      - 用列表收集每行 '\\n'.join(...)，比反复 += 字符串干净
    """
    lines = [f"## 归档记录 {now.strftime('%Y-%m-%d %H:%M')} ({'dry-run' if dry_run else 'run'})",
             '',
             '| 周号 | 文件名 | 源路径 | 目标路径 | 文件大小 |',
             '|---|---|---|---|---|']
    for rec in records:
        lines.append(f"| {rec['week']} | {rec['src'].name} | {rec['src'].as_posix()} "
                     f"| {rec['dst'].as_posix()} | {format_size(rec['size'])} |")
    return '\n'.join(lines) + '\n'      # 结尾换行：追加拼接时不会把下一段标题粘上来


# TODO-2: append_index —— 追加写入 INDEX.md
def append_index(dest: Path, records: list,
                 now: datetime | None = None, dry_run: bool = False) -> None:
    """
    参数: dest 目标根目录; records 本次成功归档的 plan 列表
    返回: None

    步骤:
      1. records 为空 → 直接 return（没东西可写，别创建空索引）
      2. dest.mkdir(parents=True, exist_ok=True)
      3. index = dest / 'INDEX.md'
      4. index 不存在 → 先写大标题 '# 归档索引'（首次创建才写，避免每次重复）
      5. 用 open(index, 'a', encoding='utf-8') 追加 build_index_block(...) 的结果
         （'a' 是追加，'w' 会清空历史 —— 这是本函数唯一的高危点）

    提示: 判断「首次创建」用 index.exists()，要在写入大标题**之前**判断
    """
    if not records:
        return
    dest.mkdir(parents=True, exist_ok=True)
    index = dest / 'INDEX.md'
    first = not index.exists()
    if now is None:
        now = datetime.now()
    # 只打开一次：首个段落补大标题，后续段落补空行，避免两段之间粘连
    with open(index, 'a', encoding='utf-8', newline='\n') as f:
        f.write('# 归档索引\n\n' if first else '\n')
        f.write(build_index_block(records, now, dry_run))


# TODO-3: summarize —— 统计并生成 SUMMARY 行
def summarize(plans: list, dry_run: bool) -> str:
    """
    参数: plans 全部计划（含 skip/conflict/plan）; dry_run 模式标志
    返回: 一行字符串，格式见 TECH.md §5：

        dry-run : '[SUMMARY] 计划归档 5 个，跳过 2 个，冲突 1 个，失败 0 个'
        run     : '[SUMMARY] 归档 5 个，跳过 2 个，冲突 1 个，失败 0 个'

    计数规则:
      - 计划归档数 = status == 'plan' 的个数（注意：run 模式下失败的会变成 'failed'，见下）
      - 跳过数     = status == 'skip'
      - 冲突数     = status == 'conflict'
      - 失败数     = status == 'failed'（run 模式下 do_move 失败时把 status 改写为 failed）

    提示: 用 sum(1 for p in plans if p['status'] == 'x') 统计；文案随 dry_run 变
    """
    plan_count = sum(1 for p in plans if p['status'] == 'plan')
    skip_count = sum(1 for p in plans if p['status'] == 'skip')
    conflict_count = sum(1 for p in plans if p['status'] == 'conflict')
    failed_count = sum(1 for p in plans if p['status'] == 'failed')
    verb = '计划归档' if dry_run else '归档'
    return f"[SUMMARY] {verb} {plan_count} 个，跳过 {skip_count} 个，冲突 {conflict_count} 个，失败 {failed_count} 个"


# ============================================================
# 自测台（不用改）
# ============================================================

def _rec(week: str, name: str, size: int) -> dict:
    """构造一条 plan 记录，路径统一用虚构值，方便断言字符串"""
    return {
        'status': 'plan',
        'week': week,
        'category': 'code',
        'src': Path('src') / name,
        'dst': Path('dst') / week / 'code' / name,
        'size': size,
    }


def run_selftest() -> int:
    passed, total = 0, 0
    now = datetime(2026, 10, 21, 10, 30)

    # 用例 1：段落头 + 表头 + 分隔行结构正确
    total += 1
    block = build_index_block([_rec('W34', 'W34_test.py', 512)], now, dry_run=False) or ''
    lines = block.strip().splitlines()
    ok1 = (len(lines) >= 4
           and lines[0] == '## 归档记录 2026-10-21 10:30 (run)'
           and lines[1].strip() == ''
           and lines[2] == '| 周号 | 文件名 | 源路径 | 目标路径 | 文件大小 |'
           and lines[3] == '|---|---|---|---|---|')
    print(f"{'PASS' if ok1 else 'FAIL'}  段落头与表头（首行={lines[0] if lines else None!r}）")
    passed += ok1

    # 用例 2：数据行五个字段 + 大小走 format_size
    total += 1
    block2 = build_index_block([_rec('W34', 'W34_test.py', 1024)], now) or ''
    rows2 = block2.strip().splitlines()
    row = rows2[-1] if rows2 else ''
    ok2 = row == '| W34 | W34_test.py | src\\W34_test.py | dst\\W34\\code\\W34_test.py | 1.0 KB |' \
        or row == '| W34 | W34_test.py | src/W34_test.py | dst/W34/code/W34_test.py | 1.0 KB |'
    print(f"{'PASS' if ok2 else 'FAIL'}  数据行 -> {row}")
    passed += ok2

    # 用例 3：多条记录 → 每条一行（1+3 行数据行）
    total += 1
    block3 = build_index_block([_rec('W1', 'W1_a.py', 10),
                                _rec('W100', 'W100_b.py', 2048)], now) or ''
    data_rows = [ln for ln in block3.splitlines() if ln.startswith('| W')]
    ok3 = len(data_rows) == 2 and 'W1' in data_rows[0] and 'W100' in data_rows[1]
    print(f"{'PASS' if ok3 else 'FAIL'}  两条记录 -> {len(data_rows)} 行数据")
    passed += ok3

    # 用例 4：首次 append 创建 INDEX.md 并带大标题
    total += 1
    with tempfile.TemporaryDirectory() as td:
        dest = Path(td) / 'archive'
        append_index(dest, [_rec('W34', 'W34_test.py', 100)])
        index = dest / 'INDEX.md'
        text = index.read_text(encoding='utf-8') if index.exists() else ''
        ok4 = index.exists() and text.lstrip().startswith('# 归档索引') and 'W34_test.py' in text
        print(f"{'PASS' if ok4 else 'FAIL'}  首次创建 -> 存在={index.exists()} 有标题={text.lstrip().startswith('# 归档索引')}")
        passed += ok4

    # 用例 5：二次 append 是追加，历史记录不丢（两段 + 两条记录都在）
    # 额外要求：每段标题必须**独立成行**（防止上一段末行与下一段标题粘连）
    total += 1
    with tempfile.TemporaryDirectory() as td:
        dest = Path(td) / 'archive'
        append_index(dest, [_rec('W34', 'W34_test.py', 100)])
        append_index(dest, [_rec('W35', 'W35_test.py', 100)])
        index5 = dest / 'INDEX.md'
        text = index5.read_text(encoding='utf-8') if index5.exists() else ''
        glued = [ln for ln in text.splitlines() if '##' in ln and not ln.startswith('##')]
        ok5 = (text.count('## 归档记录') == 2 and 'W34_test.py' in text and 'W35_test.py' in text
               and text.count('# 归档索引') == 1 and not glued)
        print(f"{'PASS' if ok5 else 'FAIL'}  追加两段 -> 段落={text.count('## 归档记录')} 标题={text.count('# 归档索引')} 粘连行={glued[:1]}")
        passed += ok5

    # 用例 6：空 records 不创建文件 + summarize 文案与计数
    total += 1
    with tempfile.TemporaryDirectory() as td:
        dest = Path(td) / 'archive'
        append_index(dest, [])
        no_file = not (dest / 'INDEX.md').exists()
    plans = [
        {'status': 'plan'},
        {'status': 'plan'},
        {'status': 'skip'},
        {'status': 'conflict'},
        {'status': 'failed'},
    ]
    s_dry = summarize(plans, True) or ''
    s_run = summarize(plans, False) or ''
    ok6 = (no_file
           and s_dry == '[SUMMARY] 计划归档 2 个，跳过 1 个，冲突 1 个，失败 1 个'
           and s_run == '[SUMMARY] 归档 2 个，跳过 1 个，冲突 1 个，失败 1 个')
    print(f"{'PASS' if ok6 else 'FAIL'}  空记录+汇总 -> 空={no_file} dry={s_dry!r} run={s_run!r}")
    passed += ok6

    print(f"\n{passed}/{total} 通过")
    return 0 if passed == total else 1


if __name__ == '__main__':
    raise SystemExit(run_selftest())
