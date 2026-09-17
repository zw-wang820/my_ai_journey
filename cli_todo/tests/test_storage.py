"""storage 层单元测试：查找 / 保存 / 加载。

运行方式（项目根目录）：
    pytest                      # 跑全部测试
    pytest --cov=. --cov-report=term-missing   # 带覆盖率
"""

import pytest

from models import storage
from models.storage import find_todo_by_id, load_todos, save_todos


def test_find_todo_by_id_命中():
    """列表中存在对应 id 时，返回该条 todo。"""
    todos = [
        {"id": 1, "content": "买牛奶", "done": False},
        {"id": 2, "content": "写周报", "done": True},
    ]

    result = find_todo_by_id(todos, 2)

    assert result is not None
    assert result["content"] == "写周报"


def test_find_todo_by_id_未命中():
    """列表中不存在对应 id 时，返回 None。"""
    todos = [{"id": 1, "content": "买牛奶", "done": False}]

    assert find_todo_by_id(todos, 99) is None


def test_save_then_load_往返(temp_todo_file):
    """保存后能原样读回（依赖 temp_todo_file fixture 隔离真实数据文件）。"""
    todos = [
        {
            "id": 1,
            "content": "买牛奶",
            "done": False,
            "created_at": "2026-09-15T10:00:00",
            "updated_at": "2026-09-15T10:00:00",
        },
    ]

    save_todos(todos)

    assert temp_todo_file.exists()  # 文件确实被创建
    assert load_todos() == todos  # 内容原样读回


# ⚠️ 铁律：凡是会读写文件的测试，**必须**在参数里写 `temp_todo_file`，
#    否则它会去读写 %APPDATA% 下你真实的 todos.json —— 那就是污染真实数据。
#    记住一句话：**测试可以随便跑，真实数据不能碰。**
#


def test_load_todos_文件不存在(temp_todo_file):
    """不预置任何文件（tmp_path 本来就是空的），调用 load_todos()，断言返回 []。"""
    assert load_todos() == []


def test_load_todos_文件损坏(temp_todo_file):
    """写入一个非 JSON 字符串，调用 load_todos() 会抛出 SystemExit。"""
    temp_todo_file.write_text("这不是JSON", encoding="utf-8")
    with pytest.raises(SystemExit):
        load_todos()


def test_save_todos_写入失败时原文件完好(temp_todo_file, monkeypatch):
    """写入中途失败时，原文件必须毫发无损 —— 这才是"原子性"的真正含义。"""
    # 1) 先写入一份"有价值的原始数据"
    original = [{"id": 1, "content": "重要数据", "done": False}]
    save_todos(original)

    # 2) 打桩：只替换 json.dump 这一个函数，json 的其余属性（load / JSONDecodeError）保持原样
    def boom(*args, **kwargs):
        raise OSError("模拟磁盘写入失败")

    monkeypatch.setattr(storage.json, "dump", boom)

    # 3) 尝试覆盖写入新数据（内部 try/except 会吞掉这个 OSError）
    save_todos([{"id": 2, "content": "新数据", "done": False}])

    # 4) 关键断言：原文件必须原封不动
    assert load_todos() == original


def test_save_todos_替换失败时原文件完好(temp_todo_file, monkeypatch):
    """临时文件写好了，但最后一步 os.replace 失败 —— 原文件仍须完好。"""
    original = [{"id": 1, "content": "重要数据", "done": False}]
    save_todos(original)

    def boom(*args, **kwargs):
        raise OSError("模拟替换失败")

    monkeypatch.setattr(storage.os, "replace", boom)

    save_todos([{"id": 2, "content": "新数据", "done": False}])

    assert load_todos() == original  # 原文件完好

    # 临时文件残留（已知，V2 优化点）
    assert (temp_todo_file.parent / "todos.tmp").exists()
