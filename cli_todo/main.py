"""cli_todo 程序入口：定义 argparse 子命令，分发给 commands 注册表。"""

import argparse
import logging
import sys
from commands import COMMANDS


def main() -> None:
    """程序入口：定义 argparse 子命令并分发给 commands 注册表。"""
    parser = argparse.ArgumentParser(description="命令行待办事项工具")
    subparsers = parser.add_subparsers(dest="command", required=True, help="子命令")

    # add
    parser_add = subparsers.add_parser("add", help="添加待办事项")
    parser_add.add_argument("content", type=str, nargs="+", help="待办事项文本")

    # list
    subparsers.add_parser("list", help="列出所有待办事项")

    # done
    parser_done = subparsers.add_parser("done", help="标记待办事项为已完成")
    parser_done.add_argument("id", type=int, help="待办事项ID")

    # edit
    parser_edit = subparsers.add_parser("edit", help="编辑待办事项")
    parser_edit.add_argument("id", type=int, help="待办事项ID")
    parser_edit.add_argument("content", type=str, nargs="+", help="新的待办事项文本")

    # del
    parser_del = subparsers.add_parser("del", help="删除待办事项")
    parser_del.add_argument("id", type=int, help="待办事项ID")

    args = parser.parse_args()
    COMMANDS[args.command](args)


if __name__ == "__main__":
    # 只在真正作为 CLI 运行时配置日志；被 import（如 pytest）时不生效
    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s: %(message)s",
    )
    try:
        main()
    except KeyboardInterrupt:
        print("\n操作已取消")
        sys.exit(130)  # 130 = Ctrl+C 的标准退出码
    except Exception as e:
        print(f"未预期的错误：{e}")
        sys.exit(1)  # 1 = 一般错误
