# CLI 待办清单 · 技术方案

> **版本**：v0.3（模块化重构 + 测试落地后更新）
> **状态**：✅ 已定稿
> **基于**：PRD v0.2
> **文档维护原则**：每完成一轮方案确认，版本号 +1，并在「变更记录」写明本次补了什么。
> **标注说明**：每条决策后用 **[用户]** / **[AI 补]** / **[共识]** 标注来源，便于追溯与挑战。

---

## 1. 数据模型

每条 todo 在 JSON 中是一个 `dict` 对象，整个文件是一个 `list`。

| 字段 | 类型 | 含义 | 来源 |
|---|---|---|---|
| `id` | int | 待办编号（=在列表中的索引 + 1） | [用户] |
| `content` | str | 待办内容 | [用户] |
| `done` | bool | 是否已完成 | [用户：原写 `biaoji`，规范化为英文术语 `done`] |
| `created_at` | str (ISO8601) | 创建时间 | [AI 补] |
| `updated_at` | str (ISO8601) | 最后修改时间（done / edit 时更新） | [AI 补] |

**JSON 示例**：

```json
[
  {
    "id": 1,
    "content": "买牛奶",
    "done": false,
    "created_at": "2026-09-04T18:05:33",
    "updated_at": "2026-09-04T18:05:33"
  }
]
```

**字段命名规范** [AI 补 + 用户同意]：
- 使用英文术语，不用拼音（避免 `biaoji` / `shijian` 这类）。
- snake_case 风格。
- 布尔字段用 `done` 而非 `is_done`（Python 内置 `if todo.done` 更顺）。

---

## 2. 项目结构

V1 初版为单文件方案（`cli_todo.py`）。**v0.3 起已重构为多模块包结构**：

```
main.py            入口薄壳（argparse 子命令解析 + logging 初始化）
commands/          命令实现（add / list / done / edit / del）
models/
    storage.py     数据存储实现（读 / 写 JSON、原子写入、错误处理）
tests/
    conftest.py    pytest fixture（临时数据文件）
    test_storage.py  storage 层单元测试
legacy/            旧版单文件代码归档，不参与格式化与测试
```

> 拆分原则：入口薄壳只做解析与分发，业务在 `commands/`，持久化在 `models/storage.py`，为 V2 扩展（优先级、分类等）预留模块边界。

---

## 3. 命令解析

**选用 `argparse`（子命令模式）**。  [用户 + 共识]

**理由** [用户查资料结论]：
- V1 有 6 个子命令，未来可能扩展 → 子命令模式天然适配。
- `argparse` 自动生成 `--help`、参数校验、错误提示。
- `sys.argv` 适合脚本级 / 一次性参数，**不适合这种多子命令 + 给人用的 CLI**。

**命令格式设计** [AI 补，可调整]：

| 命令 | argparse 调用 | 示例 |
|---|---|---|
| `add <content>` | `args.command == 'add'; args.content` | `python cli_todo.py add 买牛奶` |
| `list` | `args.command == 'list'` | `python cli_todo.py list` |
| `done <id>` | `args.command == 'done'; args.id` | `python cli_todo.py done 1` |
| `edit <id> <content>` | `args.command == 'edit'; args.id, args.content` | `python cli_todo.py edit 1 买面包` |
| `del <id>` | `args.command == 'del'; args.id` | `python cli_todo.py del 1` |
| `exit` | `args.command == 'exit'` | `python cli_todo.py exit` |

> 命令名已锁定（F1-F6 全套）。如有调整，进入 v0.3 流程。

---

## 4. 持久化流程

> 用户的原答「不知道」，本节由 AI 起草建议方案，v0.2 用户复核。

### 4.1 读文件（启动时）

```
1. 拼接目标文件路径（Windows APPDATA\cli_todo\todos.json）
2. 文件不存在 → 创建空 JSON 文件，返回空列表
3. 文件存在 → open + json.load
   - 解析成功 → 返回列表
   - 解析失败 → 提示「文件损坏，请检查」，退出，**不覆盖原文件**
```

### 4.2 写文件（每次操作后）

**采用「写临时文件 + 原子 rename」的安全写入模式**：  [AI 补]

```
1. 把内存列表 dump 成 JSON 字符串
2. 写到 <目标文件>.tmp
3. os.replace(<目标文件>.tmp, <目标文件>)  ← 原子操作
4. 异常 → 提示原因，保留旧文件
```

**为什么用临时文件 + rename**：
- 直接写原文件，崩溃 / 断电 / 磁盘满可能导致原文件损坏，数据全丢。
- rename 在 POSIX / Windows 上都是原子操作。
- 写入失败时，旧文件保持完好。

### 4.3 写文件时机：**每次操作后立即写** ✅

**决策** [用户同意 AI 推荐]：
- 每次 `add` / `done` / `edit` / `del` 后都触发一次 `save()`。
- V1 数据量小，性能差异可忽略；安全第一。

---

## 5. 错误处理

**两层结合**：  [用户]
- **每层自己处理已知异常**（文件不存在、参数缺失等业务错误）→ 友好提示。
- **顶层 `try-except` 兜底**（未知异常）→ 打印堆栈 + 友好退出，不吞错。

**异常使用原则**：  [用户]
- **优先用 Python 内置异常类**（`ValueError`, `FileNotFoundError`, `json.JSONDecodeError`）。
- **自定义异常类**仅在业务逻辑需要新增异常类型时使用（V1 可能不需要）。

**典型场景的异常归属** [AI 补]：

| 场景 | 异常类型 | 处理位置 |
|---|---|---|
| 参数缺失 / 类型错 | `argparse` 自动处理 | CLI 解析层 |
| 文件不存在 | `FileNotFoundError` | 持久化层（自动创建） |
| JSON 损坏 | `json.JSONDecodeError` | 持久化层（提示 + 退出） |
| 编号不存在 | `IndexError` / `ValueError` | 业务层（友好提示） |
| 未知异常 | `Exception` | 顶层兜底 |

---

## 6. 测试与质量门禁

### 6.1 单元测试（v0.3 已落地）

V1 初版为手动验收（AC-1 ~ AC-9），**v0.3 起引入 `pytest`** 对 storage 层做自动化测试：

- 范围：核心持久化函数（读 / 写 / 增 / 删 / 改的底层），对应 `tests/test_storage.py`。
- 数据隔离：`tests/conftest.py` 提供 `temp_todo_file` fixture，所有读写文件的测试**必须**注入该 fixture，避免污染 `%APPDATA%` 下的真实数据。
- 运行：`python -m pytest`（配置在 `pytest.ini`：testpaths=tests、pythonpath=.、`-v`）。

### 6.2 代码规范与提交门禁

- 格式化：`black`（`pyproject.toml`：line-length=88，target-version py310，排除 `legacy/`）。
- 规范检查：`flake8`（`.flake8`：max-line-length=88 与 black 对齐，ignore E203）。
- 日志约定：纯用户提示用 `print`；开发者也需关注的信息（文件损坏、保存失败）用 `logging.error`，且用惰性 `%s` 占位；`logging.basicConfig()` 只写在 `main.py` 的入口块内。

**提交前三道门禁**：`black --check .` 无 reformat → `flake8 .` 零输出 → `pytest` 全部通过。

---

## 7. 跨平台路径策略（代码片段草案）

```python
import os
from pathlib import Path

def get_data_dir() -> Path:
    """跨平台友好的数据目录（V1 仅 Windows，V2 扩展 Linux/macOS）"""
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
```

---

## 8. 变更记录

- **v0.3**：模块化重构 + 测试落地后同步文档。
  - 项目结构：单文件 → 多模块包结构（main.py / commands/ / models/ / tests/），旧代码归档至 `legacy/`。
  - 测试策略：引入 `pytest`，storage 层单测 + `conftest.py` 临时文件 fixture 落地（原 V2 规划提前实现）。
  - 新增质量门禁：black + flake8（配置对齐 line-length=88）+ pytest 三道门禁；明确 logging 输出约定。
  - 测试框架配置：`pytest.ini`（testpaths / pythonpath / -v）、`pyproject.toml`（black）、`.flake8`。
- **v0.2**：定稿，作为「写代码」的输入。
  - 数据模型：补 `created_at` / `updated_at` 字段 [用户同意]。
  - 字段命名：`biaoji` → `done`，命名规范确认 [用户同意]。
  - 命令名：F1-F6 全套命令确认 [用户同意]。
  - 持久化：写文件时机确定为「每次操作后立即写」[用户同意]。
- **v0.1**：基于用户首轮回答建立初稿。
  - 数据模型：用户给 `id` / `content` / `biaoji`；AI 规范化为 `done`，并补 `created_at` / `updated_at`（待拍板）。
  - 项目结构：单文件 [用户]。
  - 命令解析：`argparse` 子命令模式 [用户 + 共识]。
  - 持久化流程：起草读 / 写流程 + 原子写入策略 [AI 补]；写文件时机待用户决策。
  - 错误处理：两层结合 + 内置优先 [用户]。
  - 测试策略：手动验收 [用户]。
  - 路径策略：起草代码片段 [AI 补]。