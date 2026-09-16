"""持久化层：数据目录、todo 文件读写、按 id 查找。"""
import os
import sys
import json
from pathlib import Path

def get_data_dir() -> Path:
    """跨平台友好的数据目录（V1 仅 Windows，V2 扩展 Linux/macOS）。
    
    Args:
        None
    Returns:
        Path: 数据目录路径，确保存在且可写入
    """
    if os.name == 'nt':  # Windows
        appdata = os.environ.get('APPDATA')
        if appdata:
            data_dir = Path(appdata) / 'cli_todo'
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

    Returns:
        list: 待办事项列表，每个元素为字典，包含 id、content、done 字段。


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

def save_todos(todos: list) -> None:
    """保存todo列表：先 json.dump 到 <file>.tmp，再 os.replace(tmp, TODO_FILE)。
    
    Args:
        todos: 待办事项列表，每个元素为字典，包含 id、content、done 字段。
    Returns:
        None
    """ 
    tmp_path = TODO_FILE.with_suffix('.tmp')  # 临时文件：todos.tmp
    try:
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(todos, f, ensure_ascii=False, indent=4)  # 写入临时文件
        os.replace(tmp_path, TODO_FILE)  # 原子替换原文件
    except OSError as e:
        print(f"保存失败：{e}")

def find_todo_by_id(todos: list, todo_id: int) -> dict | None:
    """返回 id 匹配的 todo；找不到返回 None。
    
    Args:
        todos: 待办事项列表，每个元素为字典，包含 id、content、done 字段。
        todo_id: 待办事项ID
    Returns:
        dict: 匹配的待办事项字典，包含 id、content、done 字段；若找不到则 None
    """
    for todo in todos:
        if todo['id'] == todo_id:
            return todo
    return None
