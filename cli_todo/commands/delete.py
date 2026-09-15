"""del 子命令：删除指定待办。"""
import argparse

from models import load_todos, save_todos, find_todo_by_id

def run(args: argparse.Namespace) -> None:
    """删除指定待办事项。
    
    Args:
        args: argparse解析结果，命令行参数，包含待办事项ID。
    Returns:
        None
    """
    todos = load_todos()
    todo = find_todo_by_id(todos, args.id)
    if todo:
        todos.remove(todo)
        save_todos(todos)
        print(f"已删除 #{args.id}：{todo['content']}")
    else:
        print(f"错误：编号 #{args.id} 不存在")
