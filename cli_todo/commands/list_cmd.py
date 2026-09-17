"""list 子命令：列出所有待办。（模块名避开内置 list）"""

import argparse
from models import load_todos


def run(args: argparse.Namespace) -> None:
    """列出所有待办事项。

    Args:
        args: argparse解析结果，命令行参数，无额外参数。
    Returns:
        None
    """
    todos = load_todos()
    if todos:
        print("待办事项列表：")
        for todo in todos:
            done_str = "[√]" if todo["done"] else "[ ]"
            print(f"{todo['id']}, {todo['content']} {done_str}")
    else:
        print("暂无待办事项")
