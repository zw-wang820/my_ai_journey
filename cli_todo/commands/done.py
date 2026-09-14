"""done 子命令：标记指定待办为已完成。"""
from datetime import datetime
from models import load_todos, save_todos, find_todo_by_id

def run(args) -> None:
    todos = load_todos()
    todo = find_todo_by_id(todos, args.id)
    if todo:
        todo['done'] = True
        todo['updated_at'] = datetime.now().isoformat(timespec='seconds')
        save_todos(todos)
        print(f"已完成 #{args.id}：{todo['content']}")
    else:
        print(f"错误：编号 #{args.id} 不存在")
