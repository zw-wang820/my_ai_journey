# cli_todo · 命令行待办清单

> V1 · 零三方依赖 · 仅支持 Windows

## 使用

```bash
python cli_todo.py add <待办内容>          # 添加（支持带空格内容）
python cli_todo.py list                   # 查看所有待办
python cli_todo.py done <编号>            # 标记完成
python cli_todo.py edit <编号> <新内容>   # 修改
python cli_todo.py del <编号>             # 删除

## 数据存储

- 位置：`%APPDATA%\cli_todo\todos.json`
- 格式：JSON
- 写入策略：每次操作后原子写入（先写 `.tmp` 再 `os.replace`）

## 文档

- `docs/PRD.md` — 产品需求文档（v0.3）
- `docs/TECH.md` — 技术方案（v0.2）

## 验收

V1 已通过 9 条验收用例（AC-1 ~ AC-9），详见 `docs/PRD.md` §6。
