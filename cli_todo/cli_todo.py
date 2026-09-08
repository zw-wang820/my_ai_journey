import os
import sys
import json
import argparse # argparse是python中的标准库，专门用来解析命令行参数
from datetime import datetime
from pathlib import Path

def get_data_dir() -> Path:
    """跨平台友好的数据目录（V1 仅 Windows，V2 扩展 Linux/macOS）"""
    if os.name == 'nt':  # Windows
        appdata = os.environ.get('APPDATA')
        if appdata:
            data_dir = Path(appdata) / 'cli_todo'
            #print(f"windows数据目录:{data_dir}")  #C:\Users\pml_wzw\AppData\Roaming\cli_todo
        else:
            # APPDATA 不存在的极端兜底
            data_dir = Path.home() / 'cli_todo'
    else:  # Linux / macOS（V2 扩展）
        data_dir = Path.home() / '.local' / 'share' / 'cli_todo'
    data_dir.mkdir(parents=True, exist_ok=True)  # 自动创建
    return data_dir

TODO_FILE = get_data_dir() / 'todos.json'

def load_todos() -> list:
    """加载待办列表。
    - 文件不存在：友好提示 + 返回空列表
    - 文件损坏：报错并退出（不返回 []，避免后续 save 覆盖原文件）
    """
    if not TODO_FILE.exists():
        print("已初始化待办列表")
        return []
    try:
        with open(TODO_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"错误：{TODO_FILE} 内容损坏，请检查后重启")
        sys.exit(2)   # 不返回 []，阻断后续 save，保护原文件


"""
保存todo列表
先 json.dump 到 <file>.tmp，再 os.replace(tmp, TODO_FILE)
"""
def save_todos(todos: list) -> None:
    tmp_path = TODO_FILE.with_suffix('.tmp') #临时文件：todos.json.tmp
    try:
        with open(tmp_path,'w', encoding='utf-8') as f:
            json.dump(todos, f,ensure_ascii=False, indent=4) 
        os.replace(tmp_path, TODO_FILE)  #原子替换原文件
    except OSError as e:
        print(f"保存失败：{e}")


# 通过id找todo
def find_todo_by_id(todos: list, todo_id: int):
    """返回id匹配的todo;找不到返回None。"""
    for todo in todos:
        if todo['id'] == todo_id:
            return todo
    return None


def main():
    parser = argparse.ArgumentParser(description="命令行待办事项工具")
    subparsers = parser.add_subparsers(dest='command', required=True, help='子命令')

    #子命令1 ： add -需要一个位置参数content
    parser_add = subparsers.add_parser('add', help='添加待办事项')
    parser_add.add_argument('content', type=str, nargs='+', help='待办事项文本')
   

    #子命令2 ：list -不需要任何参数
    parser_list = subparsers.add_parser('list', help='列出所有待办事项')


    #子命令3 ：done -需要一个位置参数id
    parser_done = subparsers.add_parser('done', help='标记待办事项为已完成')
    parser_done.add_argument('id', type=int, help='待办事项ID')

    #子命令4 ：edit -需要两个位置参数id和content
    parser_edit = subparsers.add_parser('edit', help='编辑待办事项')
    parser_edit.add_argument('id', type=int, help='待办事项ID')
    parser_edit.add_argument('content', type=str, nargs='+', help='新的待办事项文本')
    
    #子命令5 ：del -需要一个位置参数 id
    parser_del = subparsers.add_parser('del', help='删除待办事项')
    parser_del.add_argument('id', type=int, help='待办事项ID')

    #解析命令行参数
    args = parser.parse_args() # 解析命令行参数，返回一个命名空间对象，包含所有解析后的参数

    #根据子命令分发
    if args.command == 'add':
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
    elif args.command == 'list':
        todos = load_todos()
        if todos:
            print("待办事项列表：")
            for todo in todos:
                done_str = "[√]" if todo['done'] else "[ ]"
                print(f"{todo['id']}, {todo['content']} {done_str}")
        else:
            print("暂无待办事项")
    elif args.command == 'done':
        todos = load_todos()
        todo = find_todo_by_id(todos, args.id)
        if todo:
            todo['done'] = True
            todo['updated_at'] = datetime.now().isoformat(timespec='seconds')
            save_todos(todos)
            print(f"已完成 #{args.id}：{todo['content']}")
        else:
            print(f"错误：编号 #{args.id} 不存在")
    elif args.command == 'edit':
        todos = load_todos()
        todo = find_todo_by_id(todos, args.id)
        if todo:
            old_content = todo['content']
            new_content = ' '.join(args.content) # 合并新内容为一个字符串
            todo['content'] = new_content
            todo['updated_at'] = datetime.now().isoformat(timespec='seconds')
            save_todos(todos)
            print(f"已更新 #{args.id}：{old_content} -> {new_content}")
        else:
            print(f"错误：编号 #{args.id} 不存在")    
    elif args.command == 'del':
        todos = load_todos()
        todo = find_todo_by_id(todos, args.id)
        if todo:
            todos.remove(todo)
            save_todos(todos)
            print(f"已删除 #{args.id}：{todo['content']}")   
        else:
            print(f"错误：编号 #{args.id} 不存在")         
        



if __name__ == '__main__': 
    try:
        main()
    except KeyboardInterrupt:
        print("\n操作已取消")
        sys.exit(130)    # 130 = Ctrl+C 的标准退出码
    except Exception as e:
        print(f"未预期的错误：{e}")
        sys.exit(1)      # 1 = 一般错误
