#!/usr/bin/env bash
# ============================================================
# archive.sh —— Shell 入口（只做入口该做的事）
# ------------------------------------------------------------
# 职责边界（PRD §7）：
#   1) 接收参数（源目录、目标目录、--dry-run）
#   2) 源目录存在性检查
#   3) 调度 python（跨平台解释器兜底）
# 归档逻辑一行都不写在这里 —— 全部在 archive.py。
#
# 用法: bash archive.sh <源目录> <目标目录> [--dry-run]
#
# 四个 TODO，填完用 `bash s6_e2e.sh` 验收（TC01/TC02/TC13 直接考这里）。
# ============================================================

set -u          # 用到未定义变量就报错（比 set -e 温和，脚本不易"半死"）

usage() {
    echo "用法: bash archive.sh <源目录> <目标目录> [--dry-run]"
    echo "  --dry-run  演练模式，只打印计划，不移动文件"
    echo "  不带该开关则真实执行"
}

# TODO-1: 参数数量校验
#   $# 是参数个数。少于 2 个（源目录、目标目录）无法工作：
#     → usage 后 exit 1
if [ $# -lt 2 ]; then
    usage
    exit 1
fi

# TODO-2: 源目录存在性检查
#   用 test 的 -d 判断「存在且是目录」：if [ ! -d "$1" ]
#     → echo "Error: 源目录不存在或不是目录: $1" 后 exit 1
#   注意：目标目录**不检查**，它不存在时由 python 自动创建（PRD §4.3）
if [ ! -d "$1" ]; then
    echo "Error: 源目录不存在或不是目录: $1"
    exit 1
fi



# TODO-3: 找 python 解释器（跨平台兜底，TC13）
#   Linux/macOS 通常只有 python3；Windows(Git Bash) 常见 python 或 py（启动器）。
#   按顺序找，第一个存在的就用；都没有 → 报错退出。
PY=$(command -v python || command -v py)
if [ ! -x "$PY" ]; then
    echo "Error: 未找到 python3/python"
    exit 1
fi

# 强制 UTF-8 输出（重要，别删）：
#   Windows 系统代码页是 936(GBK) 时，Python 把输出重定向到文件会按 locale 写 GBK，
#   日志/索引被编辑器按 UTF-8 打开就是乱码。这两个变量 + 下面的 -X utf8 让编码固定。
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8



# TODO-4: 调度 python —— 把**全部参数原样透传**给 archive.py
#   关键：用 "$@"（带引号）才能保住路径里的空格；
#         $@ 不加引号会被再次分词，路径有空格就断成两段。
#   脚本所在目录用 $(dirname "$0")，这样在任何工作目录下都能跑：
#     exec "$PY" "$(dirname "$0")/archive.py" "$@"
#   -X utf8：即使环境变量被清掉，也强制 Python 用 UTF-8 读写文本
exec "$PY" -X utf8 "$(dirname "$0")/archive.py" "$@"
