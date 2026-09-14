"""list 子命令：列出所有待办。（模块名避开内置 list）"""
from models import load_todos

def run(args) -> None:
    todos = load_todos()
    if todos:
        print("待办事项列表：")
        for todo in todos:
            done_str = "[√]" if todo['done'] else "[ ]"
            print(f"{todo['id']}, {todo['content']} {done_str}")
    else:
        print("暂无待办事项")
