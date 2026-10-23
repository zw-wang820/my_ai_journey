"""
archive.py —— 学习资料自动归档工具（单文件交付版）
=====================================================
用法:
    python archive.py <源目录> <目标目录> [--dry-run]

归档规则（PRD v1.1 定稿）:
    1. 只处理源目录**顶层**文件，不递归（子目录一律忽略）
    2. 文件名首字符必须是大写 W，否则跳过（小写 w 也跳过）
    3. 周号 = 第一个 '_' 之前的字段（W1 / W34 / W100 都合法，不强制两位数字）
    4. 后缀分类：.py / .sh → code/     .md → note/
    5. 目标路径：<目标目录>/<周号>/<code|note>/<原文件名>
    6. 移动语义：先复制 → 复核目标已落地 → 删源 → 复核源已消失；
       任何一步失败都保留源文件（宁可留重复，绝不丢数据）
    7. 目标已存在同名文件 → 冲突，跳过且不覆盖
    8. run 模式结束后向 <目标目录>/INDEX.md **追加**本次记录
       （周号 / 文件名 / 源路径 / 目标路径 / 文件大小）

两种模式:
    不带 --dry-run = 真实执行；带 --dry-run = 只打印计划，零副作用
    （不建目录、不写索引、不动任何文件）

跨平台: 仅用标准库，Windows / Linux / macOS 行为一致。
        解释器在 Linux/macOS 下通常是 python3，Windows 下是 python。
"""

import errno
import shutil
import sys
from datetime import datetime
from pathlib import Path

# 输出被重定向到文件/管道时强制 UTF-8（直接 `python archive.py ... > log` 也安全）。
# 原因：Windows 默认代码页 936(GBK)，Python 会按 locale 把中文写成 GBK 字节，
#      日志被编辑器按 UTF-8 打开就是乱码。控制台交互（isatty）不改，避免终端显示异常。
if not sys.stdout.isatty():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError):      # 极老解释器 / 已被替换的流
        pass

# 后缀 → 目标子目录（PRD §5.1）
CATEGORY_MAP = {
    '.py': 'code',
    '.sh': 'code',
    '.md': 'note',
}


# ============================================================
# 1. 命令行参数（S1）
# ============================================================

def print_usage() -> None:
    """打印用法说明（参数错误时调用）。"""
    print('用法: python archive.py <源目录> <目标目录> [--dry-run]')
    print('  --dry-run  演练模式：只打印计划，不移动文件、不写索引')
    print('  不带该开关则真实执行')


def parse_args(argv: list) -> tuple:
    """
    解析命令行参数。

    输入: argv —— sys.argv[1:]（不含脚本名）
    返回: (src: Path, dest: Path, dry_run: bool)
    失败: 打印用法后 sys.exit(1)
    """
    positionals = [a for a in argv if not a.startswith('-')]
    flags = [a for a in argv if a.startswith('-')]

    # 位置参数必须恰好 2 个；flag 只允许 --dry-run
    if len(positionals) != 2 or any(f != '--dry-run' for f in flags):
        print_usage()
        sys.exit(1)

    return Path(positionals[0]), Path(positionals[1]), '--dry-run' in flags


def check_src(src: Path) -> None:
    """源目录检查：必须存在且是目录，否则报错退出（PRD §6.5）。"""
    # is_dir() 同时覆盖「不存在」和「是文件」两种情况，比 exists() 更严格
    if not src.is_dir():
        print(f'Error: 源目录不存在或不是目录: {src}')
        sys.exit(1)


# ============================================================
# 2. 文件名分析（S2）
# ============================================================

def analyze(name: str) -> dict:
    """
    分析单个文件名，返回归档判定结果。检查顺序不可颠倒：
    W 前缀 → 下划线 → 后缀，保证每个坏文件只得到唯一一个 reason。

    参数: name —— 纯文件名（不带目录），如 'W34_test.py'
    返回: {'status': 'ok'|'skip', 'week': str, 'category': str, 'reason': str}
    """
    if not name.startswith('W'):
        return {'status': 'skip', 'week': '', 'category': '', 'reason': '首字符非 W'}

    if '_' not in name:
        return {'status': 'skip', 'week': '', 'category': '', 'reason': '未找到 _ 分隔符'}

    week = name.split('_', 1)[0]

    suffix = Path(name).suffix
    if suffix not in CATEGORY_MAP:
        return {'status': 'skip', 'week': '', 'category': '', 'reason': '不支持的后缀'}

    return {'status': 'ok', 'week': week, 'category': CATEGORY_MAP[suffix], 'reason': ''}


# ============================================================
# 3. 计划构建（S3）
# ============================================================

def build_dst(dest: Path, week: str, category: str, name: str) -> Path:
    """
    <目标目录>/<周号>/<code|note>/<原文件名>。
    用 pathlib 的 / 拼接，比字符串拼路径更安全（自动处理分隔符差异）。
    """
    return dest / week / category / name


def format_size(n: int) -> str:
    """字节数转人类可读字符串：'512 B' / '1.2 KB' / '3.5 MB'。"""
    if n < 1024:
        return f'{n} B'
    if n < 1024 * 1024:
        return f'{n / 1024:.1f} KB'
    return f'{n / (1024 * 1024):.1f} MB'      # 括号不能省：n/1024*1024 等于 n


def plan_one(f: Path, dest: Path) -> dict:
    """
    为单个文件生成归档计划。三种状态：
      skip     -> analyze 的原始结果（含 reason，不含 src/dst）
      plan     -> 目标不存在，可归档
      conflict -> 目标已存在同名文件，跳过不覆盖
    """
    r = analyze(f.name)
    if r['status'] == 'skip':
        return r

    dst = build_dst(dest, r['week'], r['category'], f.name)
    plan = {
        'status': 'plan',
        'week': r['week'],
        'category': r['category'],
        'src': f,
        'dst': dst,
        'size': f.stat().st_size,       # 原始字节数（int），展示时才格式化
    }
    if dst.exists():
        plan['status'] = 'conflict'
    return plan


# ============================================================
# 4. 移动与失败保护（S4）—— 整个工具最关键的一段
# ============================================================

def explain_oserror(exc: OSError) -> str:
    """把建目录 / 复制时抛出的 OSError 归类成可读原因，便于现场排障。"""
    if isinstance(exc, PermissionError):
        return '权限不足：目标目录不可写，或目标文件正被其他程序占用'
    if isinstance(exc, FileExistsError):
        return '目标目录路径已被同名文件占用，无法建目录'
    if isinstance(exc, NotADirectoryError):
        return '目标路径中间有一段是文件而不是目录'
    if isinstance(exc, IsADirectoryError):
        return '目标位置已存在同名目录'
    if isinstance(exc, FileNotFoundError):
        return '源文件或上级目录不存在（可能已被其他进程移动/删除）'
    if exc.errno == errno.ENOSPC:
        return '磁盘空间不足，清理空间后重试'
    if exc.errno == errno.EDQUOT:
        return '超出用户磁盘配额'
    if exc.errno == errno.EROFS:
        return '目标位于只读文件系统或只读介质'
    if exc.errno == errno.ENAMETOOLONG:
        return '路径过长（Windows 默认上限约 260 字符）'
    if exc.errno == errno.EXDEV:
        return '跨设备操作被拒绝'
    return f'未归类错误（errno={exc.errno}）'


def do_move(src: Path, dst: Path) -> str:
    """
    两步走移动：复制成功才删源，任何一步失败都保留源文件。

    返回:
      'ok'            源已消失、目标已存在
      'copy_failed'   复制没成功，源文件原样保留
      'unlink_failed' 复制成功但源删不掉，源与目标同时存在（留重复，不丢数据）
    """
    # 第 1 步：建父目录 + 复制。mkdir 也要在 try 里 —— 目录可能被同名文件占位
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    except OSError as exc:
        print(f'[ERROR] 复制失败：{src} -> {dst}')
        print(f'  原因：{explain_oserror(exc)}')
        print(f'  原始异常：{type(exc).__name__}: {exc}')
        return 'copy_failed'

    # 第 2 步：复核目标真的落地（没抛异常 ≠ 文件存在）
    if not dst.exists():
        print(f'[ERROR] 复制后目标不存在：{dst}')
        return 'copy_failed'

    # 第 3 步：删源
    try:
        src.unlink()
    except OSError as exc:
        print(f'[WARN] 删除源失败，源与目标同时保留：{src}')
        print(f'  原因：{explain_oserror(exc)}')
        return 'unlink_failed'

    # 第 4 步：复核源真的消失
    if src.exists():
        print(f'[WARN] 删除源后源文件仍存在：{src}')
        return 'unlink_failed'

    return 'ok'


# ============================================================
# 5. 索引与汇总（S5）
# ============================================================

def build_index_block(records: list, now: datetime, dry_run: bool = False) -> str:
    """
    把归档记录渲染成一段 Markdown（纯函数，时间由调用方传入，便于测试）。
    返回的文本**以换行结尾**，方便调用方直接追加拼接。
    """
    mode = 'dry-run' if dry_run else 'run'
    lines = [
        f"## 归档记录 {now.strftime('%Y-%m-%d %H:%M')} ({mode})",
        '',
        '| 周号 | 文件名 | 源路径 | 目标路径 | 文件大小 |',
        '|---|---|---|---|---|',
    ]
    for rec in records:
        lines.append(
            f"| {rec['week']} | {rec['src'].name} | {rec['src'].as_posix()} "
            f"| {rec['dst'].as_posix()} | {format_size(rec['size'])} |"
        )
    return '\n'.join(lines) + '\n'


def append_index(dest: Path, records: list, now: datetime | None = None,
                 dry_run: bool = False) -> None:
    """
    向 <目标目录>/INDEX.md **追加**一段记录（'a' 模式，绝不覆盖历史）。
    records 为空则什么都不做（不创建空索引文件）。
    """
    if not records:
        return

    dest.mkdir(parents=True, exist_ok=True)
    index = dest / 'INDEX.md'
    first = not index.exists()
    if now is None:
        now = datetime.now()

    with open(index, 'a', encoding='utf-8') as f:
        if first:
            f.write('# 归档索引\n\n')
        else:
            f.write('\n')          # 段间空行：避免上一段末行与新标题粘成一行
        f.write(build_index_block(records, now, dry_run))


def summarize(plans: list, dry_run: bool) -> str:
    """统计四类数量，产出 TECH §5 规定的 SUMMARY 行（纯函数，只返回不打印）。"""
    counts = {k: sum(1 for p in plans if p['status'] == k)
              for k in ('plan', 'skip', 'conflict', 'failed')}
    verb = '计划归档' if dry_run else '归档'
    return (f"[SUMMARY] {verb} {counts['plan']} 个，跳过 {counts['skip']} 个，"
            f"冲突 {counts['conflict']} 个，失败 {counts['failed']} 个")


# ============================================================
# 6. 编排入口
# ============================================================

def collect_files(src: Path) -> list:
    """取源目录顶层文件（不递归），按文件名排序保证输出稳定可复现。"""
    return sorted((p for p in src.iterdir() if p.is_file()), key=lambda p: p.name)


def main() -> int:
    src, dest, dry_run = parse_args(sys.argv[1:])
    check_src(src)

    # 自归档拒绝（TECH §11 T2 方案 A）
    if src.resolve() == dest.resolve():
        print('[ERROR] 源目录与目标目录不能相同')
        return 1

    files = collect_files(src)
    if not files:
        print('[WARN] 源目录无任何文件')
        print(summarize([], dry_run))
        return 0

    plans = [plan_one(f, dest) for f in files]

    # 逐条输出；run 模式在这里真正移动
    for f, plan in zip(files, plans):
        if plan['status'] == 'plan':
            if dry_run:
                print(f"[PLAN] {f.name} -> {plan['dst']}")
            else:
                result = do_move(plan['src'], plan['dst'])
                if result == 'ok':
                    print(f"[DONE] {f.name} -> {plan['dst']}")
                else:
                    plan['status'] = 'failed'    # 让摘要能统计到失败数
        elif plan['status'] == 'conflict':
            print(f'[WARN] {f.name} 目标已存在，跳过')
        else:
            # 无 `_` 属「命名不规范」而非「不需要归档」，按 PRD §6.5 给 WARN
            label = '[WARN]' if '未找到' in plan['reason'] else '[SKIP]'
            print(f"{label} {f.name} ({plan['reason']})")

    # 只有真正执行成功（status 仍为 plan）的记录才入索引
    records = [p for p in plans if p['status'] == 'plan']
    if not dry_run and records:
        append_index(dest, records)
    print(summarize(plans, dry_run))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
