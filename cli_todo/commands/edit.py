"""edit 子命令：编辑指定待办的内容。"""
from datetime import datetime
from models import load_todos, save_todos, find_todo_by_id

def run(args) -> None:
    todos = load_todos()
    todo = find_todo_by_id(todos, args.id)
    if todo:
        old_content = todo['content']
        new_content = ' '.join(args.content)  # 合并新内容为一个字符串
        todo['content'] = new_content
        todo['updated_at'] = datetime.now().isoformat(timespec='seconds')
        save_todos(todos)
        print(f"已更新 #{args.id}：{old_content} -> {new_content}")
    else:
        print(f"错误：编号 #{args.id} 不存在")
