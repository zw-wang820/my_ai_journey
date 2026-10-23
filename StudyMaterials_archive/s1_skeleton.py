"""
archive.py —— S1 阶段骨架：参数解析 + 源目录检查
=================================================
对应 TECH.md §10 步骤 S1，验收用例 TC01 / TC02（§9）。

规则来源：PRD §4.2 / §4.3
  用法: python archive.py <源目录> <目标目录> [--dry-run]
  - 位置参数 2 个：源目录、目标目录
  - 可选 flag：--dry-run（带上 = 演练；不带 = 真实执行）
  - 参数缺失 / 多余 / 未知 flag：打印用法并 exit 1
  - 源目录不存在或不是目录：报错并 exit 1

填写说明：
  - 每个 TODO 是一处空位，按提示自己写第一版；
  - 只允许用：sys / pathlib.Path / f-string（选型已定 sys.argv，不用 argparse）；
  - 写完跑文件底部「自测命令」，TC01 / TC02 通过后交我点评。
"""

import sys
from pathlib import Path


def print_usage() -> None:
    """打印用法说明（参数错误时调用）。"""
    # TODO-1: 打印 2~4 行用法，至少包含：
    #   用法: python archive.py <源目录> <目标目录> [--dry-run]
    #   以及一句 --dry-run 语义说明（不带即真实执行）
    print('脚本用法说明：')
    print('python archive.py <源目录> <目标目录> [--dry-run]')
    print('--dry-run: 演练模式，不实际移动文件')
    print('不带 --dry-run 则真实执行')


def parse_args(argv: list) -> tuple:
    """
    解析命令行参数。

    输入: argv —— sys.argv[1:]，不含脚本名
    返回: (src: Path, dest: Path, dry_run: bool)
    失败: 打印用法并 sys.exit(1)
    """
    # TODO-2: 把 argv 拆成两类
    #   positionals = 不以 '-' 开头的参数（应该恰好 2 个）
    #   flags       = 以 '-' 开头的参数（每个都必须是 '--dry-run'）
    #   提示：两个列表推导式 + str.startswith('-')
    positionals = [a for a in argv if not a.startswith('-')]
    flags       = [a for a in argv if a.startswith('-')]

    # TODO-3: 校验（两条都要）
    #   a) len(positionals) != 2          → print_usage() 后 sys.exit(1)
    #   b) flags 里出现 --dry-run 以外的值 → print_usage() 后 sys.exit(1)
    if len(positionals) != 2 or any(f != '--dry-run' for f in flags):
        print_usage()
        sys.exit(1)

    # TODO-4: 组装返回值
    #   src  = Path(positionals[0])
    #   dest = Path(positionals[1])
    #   dry_run = '--dry-run' in flags
    #   return src, dest, dry_run
    src  = Path(positionals[0])
    dest = Path(positionals[1])
    dry_run = '--dry-run' in flags
    return src, dest, dry_run


def check_src(src: Path) -> None:
    """源目录存在性检查（PRD §6.5：不存在 / 不是目录 → 报错 exit 1）。"""
    # TODO-5: 用 Path 的哪个方法判断"存在 且 是目录"？
    #   不满足时打印: Error: 源目录不存在或不是目录: <src>
    #   然后 sys.exit(1)
    # 思考题：为什么用 is_dir() 而不是 exists()？（答案在你写完后我对答案时说）
    if not src.is_dir():
        print(f'Error: 源目录不存在或不是目录: {src}')
        sys.exit(1)


def main() -> int:
    argv = sys.argv[1:]

    src, dest, dry_run = parse_args(argv)   # S1 目标 1：参数链路
    check_src(src)                          # S1 目标 2：源目录检查

    # S1 阶段占位输出：只证明参数解析通了；S3 起替换为真实归档流程
    mode = 'dry-run' if dry_run else 'run'
    print(f'[OK] src={src} dest={dest} mode={mode}')
    return 0


if __name__ == '__main__':
    sys.exit(main())


# ============================================================
# 自测命令（Git Bash，逐条跑，看输出和 exit= 是否符合预期）
# ------------------------------------------------------------
# TC01 参数缺失 → 打印用法，exit=1
#   python s1_skeleton.py ; echo "exit=$?"
#
# TC02 源目录不存在 → Error，exit=1
#   python s1_skeleton.py ./nodir ./dest ; echo "exit=$?"
#
# 正常路径（占位输出，exit=0）
#   mkdir -p tmp/src tmp/dest && touch tmp/src/W34_test.py
#   python s1_skeleton.py tmp/src tmp/dest --dry-run ; echo "exit=$?"
#   python s1_skeleton.py tmp/src tmp/dest ; echo "exit=$?"
#
# 边界：未知 flag / 多余参数 → 打印用法，exit=1
#   python s1_skeleton.py tmp/src tmp/dest --move ; echo "exit=$?"
#   python s1_skeleton.py tmp/src tmp/dest extra ; echo "exit=$?"
# ============================================================
