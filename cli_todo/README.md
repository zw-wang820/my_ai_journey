# cli_todo · 命令行待办清单

> V1 · 零三方运行时依赖 · 仅支持 Windows

## 使用

```bash
python main.py add <待办内容>          # 添加（支持带空格内容）
python main.py list                   # 查看所有待办
python main.py done <编号>            # 标记完成
python main.py edit <编号> <新内容>   # 修改
python main.py del <编号>             # 删除
```

## 数据存储

- 位置：`%APPDATA%\cli_todo\todos.json`
- 格式：JSON
- 写入策略：每次操作后原子写入（先写 `.tmp` 再 `os.replace`）

## 项目结构

```
main.py            入口薄壳（argparse 子命令解析 + logging 初始化）
commands/          命令实现（add / list / done / edit / del）
models/
    storage.py     数据存储实现（读 / 写 JSON、原子写入、错误处理）
tests/
    conftest.py    pytest fixture：临时数据文件，隔离真实数据
    test_storage.py  storage 层单元测试
legacy/            旧版本单文件代码，仅作历史留存，不再维护
```

## 开发与质量门禁

```bash
python -m pytest            # 运行单元测试
python -m black --check .   # 格式检查
python -m flake8            # 代码规范检查
```

- 测试框架：`pytest`（配置在 `pytest.ini`：testpaths、pythonpath、`-v`）
- 格式化：`black`（配置在 `pyproject.toml`：line-length=88，py310，排除 legacy/）
- 规范检查：`flake8`（配置在 `.flake8`：max-line-length=88，ignore E203）
- 开发依赖（pytest / black / flake8）见 `requirements.txt`；运行时本身零三方依赖

## 文档

- `docs/PRD.md` — 产品需求文档（v0.3）
- `docs/TECH.md` — 技术方案（v0.3）
- `docs/V1验收报告.md` — AC-1 ~ AC-9 手动验收记录

## 验收

V1 已通过 9 条验收用例（AC-1 ~ AC-9），详见 `docs/PRD.md` §6。
