"""pytest 全局 fixture 定义。

核心目标：**任何测试都不得触碰真实的待办数据文件**
（Windows 下位于 %APPDATA%\\cli_todo\\todos.json）。

做法：用 monkeypatch 把 `models.storage.TODO_FILE` 临时替换成
pytest 提供的临时路径，测试结束后自动还原。
"""
import pytest

from models import storage


@pytest.fixture
def temp_todo_file(tmp_path, monkeypatch):
    """把 storage.TODO_FILE 重定向到本次测试专属的临时文件。

    为什么能生效：`load_todos` / `save_todos` 函数体内引用的 `TODO_FILE`
    是 storage 模块的**全局变量**，运行时从模块命名空间查找。
    monkeypatch 修改的正是这个全局变量，且测试结束自动还原。

    Args:
        tmp_path: pytest 内置 fixture，每个测试独享一个临时目录，结束后自动清理。
        monkeypatch: pytest 内置 fixture，用于测试期间打补丁，结束后自动回滚。

    Returns:
        pathlib.Path: 临时的 todos.json 路径（初始不存在，由测试自行决定是否预置内容）。
    """
    fake_path = tmp_path / 'todos.json'
    monkeypatch.setattr(storage, 'TODO_FILE', fake_path)
    return fake_path
