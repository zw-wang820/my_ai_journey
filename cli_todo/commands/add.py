"""add 子命令：新增一条待办。"""
from datetime import datetime
from models import load_todos, save_todos

def run(args) -> None:
    todos = load_todos()
    new_id = max([t['id'] for t in todos], default=0) + 1
    content = ' '.join(args.content)
    todos.append({
        'id': new_id,
        'content': content,
        'done': False,
        'created_at': datetime.now().isoformat(timespec='seconds'),
        'updated_at': datetime.now().isoformat(timespec='seconds'),
    })
    save_todos(todos)
    print(f"已添加 #{new_id}：{content}")
