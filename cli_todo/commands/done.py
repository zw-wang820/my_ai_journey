"""done 子命令：标记指定待办为已完成。"""

import argparse
from datetime import datetime
from models import load_todos, save_todos, find_todo_by_id


def run(args: argparse.Namespace) -> None:
    """标记指定待办事项为已完成。

    Args:
        args: argparse解析结果，命令行参数，包含待办事项ID。
    Returns:
        None
    """
    todos = load_todos()
    todo = find_todo_by_id(todos, args.id)
    if todo:
        todo["done"] = True
        todo["updated_at"] = datetime.now().isoformat(timespec="seconds")
        save_todos(todos)
        print(f"已完成 #{args.id}：{todo['content']}")
    else:
        print(f"错误：编号 #{args.id} 不存在")
