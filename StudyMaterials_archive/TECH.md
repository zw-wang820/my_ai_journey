# TECH：学习资料自动归档工具技术方案

- **版本**：v1.1（T1 已确认；T2 判断依据修正为待拍板）
- **日期**：2026-09-21
- **上游**：`PRD_学习资料自动归档.md`（v1.1，已定稿）
- **交付物**：`archive.py`（核心逻辑）+ `archive.sh`（Shell 入口）
- **状态**：待评审 → 评审通过后按 §10「引导式实现计划」逐段编码

---

## 1. 技术选型结论

| 决策项 | 结论 | 理由 |
|---|---|---|
| CLI 解析 | **`sys.argv` 手写解析** | 无子命令，只有 2 个位置参数 + 1 个 flag，`argparse` 属过度设计（已确认） |
| 语言分工 | **Shell 入口 + Python 干活**（单链路） | PRD §7，逻辑复杂的东西不进 Shell |
| 三方依赖 | **0 个** | Python 标准库 + Bash 内置命令 |
| 文件操作 | `pathlib` + `shutil` | 标准库、跨平台、屏蔽路径分隔符差异 |
| 周号匹配 | `re`（正则） | 简单、可读 |
| 记录载体 | `dict`（V1） | 降低学习负担；`dataclass` 列为 V2 可选重构 |
| 时间戳 | `datetime.datetime.now().strftime('%Y-%m-%d %H:%M')` | 索引段落标题 |
| 索引格式 | Markdown 表格，**追加**写入，UTF-8 | PRD §6.3 / Q3 / Q4 |

### 1.1 sys.argv vs argparse（选型对比）

| 维度 | `sys.argv` | `argparse` |
|---|---|---|
| 代码量 | 约 10 行，全部自己控制 | 约 8 行，但需理解 `add_argument` 语义 |
| 自动 `-h` 帮助 | ❌ 需手写用法字符串 | ✅ 自动生成 |
| 参数校验 | 手写判断（本项目就 3 个，够用） | 自动（类型/互斥/必填） |
| 扩展性 | 加参数要手改解析逻辑 | 加一行 `add_argument` |
| 学习成本 | 低，贴合"命令行本质" | 中，需额外学一套 API |

**结论**：本项目参数极少且无子命令，选 `sys.argv`；缺点用「手写 `print_usage()`」补齐。

---

## 2. 文件与运行环境

| 文件 | 层级 | 说明 |
|---|---|---|
| `archive.py` | Python 干活 | 参数解析、筛选分类、移动、冲突处理、索引生成 |
| `archive.sh` | Shell 入口 | 参数接收 → 目录检查 → 调用 `archive.py` 透传参数 |
| `INDEX.md` | 运行产物 | run 模式索引，位于目标目录 |

**平台差异兜底**（`archive.sh` 内）：

```bash
# Windows: python ；Linux/macOS: python3 —— 优先 python3，不存在则回退 python
if command -v python3 >/dev/null 2>&1; then PY=python3; else PY=python; fi
```

Python 版本要求：**3.7+**（用到 `pathlib`、`f-string`；不使用 `match` 等新语法，保持宽容）。

---

## 3. 模块划分与函数签名

设计原则：**单一职责，一个函数只做一件事**——既方便测试，也便于逐段填空式实现。

| # | 函数 | 签名 | 职责 | 返回值 |
|---|---|---|---|---|
| 1 | `parse_args` | `parse_args(argv: list) -> tuple` | 解析并校验参数（源、目标、`--dry-run`） | `(src: Path, dest: Path, dry_run: bool)`；非法则打印用法并 `sys.exit(1)` |
| 2 | `check_src` | `check_src(src: Path) -> None` | 源目录存在性检查（与 Shell 双保险） | 不存在则打印 `Error` 并 `sys.exit(1)` |
| 3 | `analyze` | `analyze(name: str) -> dict` | ① 首字符是否大写 `W`；② 切出周号；③ 按后缀映射 code/note | `{'status': 'ok'\|'skip', 'week': str, 'category': str, 'reason': str}` |
| 4 | `build_dst` | `build_dst(dest: Path, week: str, category: str, name: str) -> Path` | 拼接目标路径 | `Path` |
| 5 | `format_size` | `format_size(n: int) -> str` | 字节 → `B/KB/MB`，保留 1 位小数 | `str` |
| 6 | `plan_one` | `plan_one(f: Path, dest: Path) -> dict` | 生成单文件计划（含冲突检测） | 计划 dict：`status` = `plan` / `skip` / `conflict`，附 `week/category/src/dst/size` |
| 7 | `do_move` | `do_move(src: Path, dst: Path) -> str` | **两步走移动 + 失败保护**（见 §7） | `'ok'` / `'copy_failed'` / `'unlink_failed'` |
| 8 | `append_index` | `append_index(dest: Path, records: list) -> None` | 追加写 `INDEX.md` | `None` |
| 9 | `main` | `main() -> int` | 编排全流程 + 打印 SUMMARY | 退出码 |

> 提示：函数 3~7 是**纯逻辑**（输入→输出，不碰全局状态），是最适合先写测试、再写实现的部分。

---

## 4. 主流程

```python
def main() -> int:
    argv = sys.argv[1:]
    src, dest, dry_run = parse_args(argv)     # 1. 参数解析 + 用法提示
    check_src(src)                            # 2. 源目录检查
    if src.resolve() == dest.resolve():       # 3. 同目录校验（T2 已确认：方案 A 拒绝）
        print('[ERROR] 源目录与目标目录不能相同')
        return 1

    plans, records = [], []
    files = [f for f in src.iterdir() if f.is_file()]   # 4. 只扫顶层文件，不递归
    if not files:
        print('[WARN] 源目录无任何文件')                # PRD §6.5

    for f in files:                            # 5. 逐文件：分析 → 分类 → 拼目标 → 查冲突
        plan = plan_one(f, dest)
        plans.append(plan)
        if plan['status'] == 'plan' and not dry_run:
            result = do_move(f['src'], f['dst'])        # 6. 真实移动（含失败保护）
            ...
    # 7. 输出 + 索引
    print_summary(plans, dry_run)
    if not dry_run and records:
        append_index(dest, records)
    return 0
```

**流程要点**：

- 只遍历 `src.iterdir()` 且 `is_file()` —— 天然满足「不递归」。
- dry-run 与 run 共用 `plan_one` 生成的同一份计划，保证「打印的就是要做的」。
- `plans` 全程累积，SUMMARY 从计划推导，不重复统计。

---

## 5. 输出标签与计数规范

| 标签 | 触发条件 | 触发模式 | 计数归属 |
|---|---|---|---|
| `[PLAN]` | 文件将被归档 | dry-run | 计划归档数 |
| `[DONE]` | 文件已移动到目标 | run | 计划归档数 |
| `[SKIP]` | 首字符非 `W` / 无 `_` / 后缀不支持 | 两者 | 跳过数 |
| `[WARN]` | 目标已存在同名文件（冲突）；或删源失败；或源目录为空 | 两者 | 冲突数 / 失败数 |
| `[ERROR]` | 复制到目标失败 | run | 失败数 |
| `[SUMMARY]` | 结尾一行 | 两者 | 汇总 |

**SUMMARY 格式**：

```
[SUMMARY] 计划归档 5 个，跳过 2 个，冲突 1 个，失败 0 个      # dry-run
[SUMMARY] 归档 5 个，跳过 2 个，冲突 1 个，失败 0 个          # run
```

---

## 6. 索引写入细则

- 位置 `<目标目录>/INDEX.md`，**追加**（`open(..., 'a', encoding='utf-8')`），每次 run 新增一段。
- 每段结构（字段顺序固定）：

```markdown
## 归档记录 2026-09-21 11:25 (run)

| 周号 | 文件名 | 源路径 | 目标路径 | 文件大小 |
|---|---|---|---|---|
| W34 | W34_test.py | tmp/src/W34_test.py | tmp/dest/W34/code/W34_test.py | 1.2 KB |
```

- 只写**成功归档**的记录（skip/conflict/失败的不入索引，避免索引失真）。
- dry-run 完全不碰索引文件。
- 文件大小用 §3 的 `format_size` 输出人类可读格式。

---

## 7. 移动失败保护实现细则（决策 3）

**思路**（你提出的方案）：不依赖异常类型判断，而用**文件存在性**判断失败类型——直观、可测、跨平台稳定。

```
步骤 1  目标父目录 mkdir(parents=True, exist_ok=True)
步骤 2  shutil.copy2(src, dst)                      ← 复制
步骤 3  若 dst 不存在 → 'copy_failed'（[ERROR]，源文件保留）
步骤 4  src.unlink()                                ← 删源
步骤 5  若 src 仍存在 → 'unlink_failed'（[WARN]，源与目标都保留，形成重复文件）
        否则            → 'ok'
```

```python
def do_move(src: Path, dst: Path) -> str:
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)            # 保留元数据
    except OSError as e:                  # 权限/磁盘满等兜底
        print(f'[ERROR] {src.name} -> {dst} ; {e}')
        return 'copy_failed'

    if not dst.exists():                  # 存在性复核（判断依据 1：目标目录）
        print(f'[ERROR] {src.name} 复制后目标不存在，源文件保留')
        return 'copy_failed'

    try:
        src.unlink()
    except OSError as e:
        print(f'[WARN] {src.name} 已归档但源文件删除失败 ; {e}')
        return 'unlink_failed'

    if src.exists():                      # 存在性复核（判断依据 2：源目录）
        print(f'[WARN] {src.name} 源文件仍存在，未完成移动')
        return 'unlink_failed'

    return 'ok'
```

**红线**：任何失败路径都**不得**丢失源文件；宁可留下重复文件，也不能少一份学习成果。

---

## 8. 异常处理约定

- 单文件级 `try/except OSError`，**失败不中断**整个批次（继续处理下一个文件）。
- 参数错误 / 源目录不存在 → 立即 `sys.exit(1)`（不做任何归档动作）。
- 批次内个别文件失败 → 记入失败数，**正常结束并返回 0**（T1 已确认）；失败明细通过 `[ERROR]` 与 SUMMARY 暴露，退出码只用于区分"用法/环境错误"。

---

## 9. 测试用例设计（含决策 4 的构造式验证）

**构造法**：临时目录 + 构造样例文件，全部可重复执行。

```bash
mkdir -p tmp/src tmp/dest
touch tmp/src/W34_test.py tmp/src/W34_notes.md tmp/src/W34_scan.sh \
      tmp/src/readme.txt tmp/src/w34_lower.py tmp/src/W34_data.csv \
      tmp/src/W34test.py            # 无下划线样例
```

| 用例 | 目的 | 构造 / 命令 | 期望结果 | 对应 PRD |
|---|---|---|---|---|
| TC01 | 参数缺失 | `bash archive.sh` | 打印用法，exit 1 | §8-1 |
| TC02 | 源目录不存在 | `bash archive.sh ./nodir ./dest` | `Error`，exit 1 | §8-1 |
| TC03 | dry-run 零副作用 | `bash archive.sh tmp/src tmp/dest --dry-run` | 有 `[PLAN]` 输出；目标目录**无任何新增文件/目录**，无 INDEX.md | §8-4 |
| TC04 | 首字符非 W 跳过 | 同 TC03 | `readme.txt`、`w34_lower.py` 均 `[SKIP]`（首字符非 W） | §8-2 |
| TC05 | 后缀不支持跳过 | 同 TC03 | `W34_data.csv` `[SKIP]`（不支持的后缀） | §8-2 |
| TC06 | 分类正确 | `bash archive.sh tmp/src tmp/dest` | `.py`/`.sh` → `W34/code/`；`.md` → `W34/note/` | §8-3 |
| TC07 | 移动成功 | 同 TC06 | 源目录中已归档文件**消失**（仅剩跳过的文件） | §8-5 |
| TC08 | 冲突跳过 | 连续执行两次 TC06 | 第二次全部 `[WARN]`，目标文件内容未被覆盖 | §8-5 |
| TC09 | 移动失败保护 | 把 `W34/code/W34_test.py` 预先建为**目录**占位，或在目标父目录去掉写权限 | `[ERROR]`，**源文件仍存在**，SUMMARY 计入失败 | §8-7 |
| TC10 | 索引字段 | TC06 后查看 `dest/INDEX.md` | 段落标题 + 5 字段齐全，追加而非覆盖 | §8-6 |
| TC11 | 空源目录 | `bash archive.sh tmp/empty tmp/dest2` | `[WARN] 源目录无任何文件` + SUMMARY 全 0，exit 0 | §6.5 |
| TC12 | 无下划线 | 含 `W34test.py` 时执行 | 跳过 + `[WARN] 未找到 _ 分隔符` | §6.5 / Q5 |
| TC13 | 跨平台入口 | Linux/macOS 执行 `archive.sh` | 自动使用 `python3`，结果一致 | §8-9 |

> 测试顺序建议：TC01/02（参数）→ TC03~05（dry-run 安全性 + 筛选）→ TC06/07（真实移动）→ TC08（幂等/冲突）→ TC09（失败保护）→ TC10（索引）→ TC11/12（边界）。

---

## 10. 引导式实现计划（每段：你写第一版 → 我看 → 补漏）

| 步骤 | 实现内容 | 你要写的核心 | 完成标志（可验证） |
|---|---|---|---|
| **S1** | 参数解析 + 源目录检查 | `parse_args` / `check_src` / `print_usage` | TC01、TC02 通过 |
| **S2** | 文件名分析 | `analyze`（首字符 W、周号切分、后缀映射） | 手工调用 5 个样例名，返回结果符合预期 |
| **S3** | 计划生成 + dry-run 打印 | `build_dst` / `format_size` / `plan_one` + 打印 | TC03、TC04、TC05 通过 |
| **S4** | 真实移动 + 失败保护 | `do_move`（§7 五步） | TC06、TC07、TC09 通过 |
| **S5** | 冲突处理 + 索引生成 | 冲突分支 + `append_index` | TC08、TC10 通过 |
| **S6** | Shell 入口封装 + 端到端 | `archive.sh`（参数接收、目录检查、python 兜底、透传） | TC11~TC13 通过，全量回归 |

> 建议每步写完立即跑对应用例，别攒到最后一起调试——这也是「关卡式学习」的设计意图。

---

## 11. TECH 级决策与待确认项

### T1 批次内个别文件失败时的退出码 —— ✅ 已确认

**结论：返回 0**（视为批次完成）。理由：失败已通过 `[ERROR]` + SUMMARY 完整暴露；退出码 1 只保留给"用法错误 / 环境错误"（参数缺失、源目录不存在），语义不混淆。

### T2 源目录 == 目标目录 —— ✅ 已确认（方案 A：拒绝）

**结论：方案 A——直接报错退出**：打印 `[ERROR] 源目录与目标目录不能相同`，exit 1，不做任何归档动作。「就地整理」留给 V2 显式开关（如 `--in-place`）。

**背景（原判断依据已修正）**：原 TECH.md 写「移动后再次扫描会自我循环」，该说法**不成立**。按 PRD §3.2「不递归、只扫源目录顶层」推演：

| 关注点 | 实际情况 | 结论 |
|---|---|---|
| 已归档文件 | 已被**移动**到目标，源目录中不再存在 | 下轮扫不到，无循环 |
| 新建的周目录 `W34/` | 是**目录**，被 `is_file()` 过滤 | 不进入处理，无循环 |
| `INDEX.md` | 落在源目录（= 目标目录）中，下轮被扫到时首字符 `I` 非 `W` | `[SKIP]`，无害，仅日志噪音 |

**结论**：`src == dest` 在 V1 设计下**是安全的**，真正的取舍不在数据安全，而在「语义清晰度 + 防误操作」。三个方案：

| 方案 | 行为 | 优点 | 代价 |
|---|---|---|---|
| **A｜拒绝（保守）** | 报错退出，不做任何动作 | 1 行代码；防止"以为在归档、实际就地改造源目录"的误操作；为将来若加递归预留安全边界 | 少一种用法 |
| B｜允许 | 不校验，就地整理 | 代码最少，用法最灵活 | `INDEX.md` 混在源目录；"归档"语义边界模糊 |
| C｜允许但提示 | 打印 `[WARN] 源目录与目标目录相同，将就地整理` 后继续 | 灵活 + 用户知情 | 多一行提示 |

**采纳记录（2026-09-21）**：用户确认选 **A**。以下为决策时的对比分析：

### T3 「已扫描过的文件下轮不再扫」—— 建议 V1 不做

**你的思路可行，但 V1 不建议实现**，根因三点：

1. **它不是死循环，只是重复输出**。被跳过的文件每轮再判一次 `[SKIP]`，不改动任何文件，行为**幂等**。
2. **加标记会引入新的失效模式**：若你把 `readme.txt` 改名成 `W34_readme.md`（已合规），"扫描记忆"会让它**被错误跳过**——除非标记同时记录 mtime/size，复杂度立刻上升。
3. **"跳过"里其实有两类**：命名不合规（该跳过）vs 冲突/失败（**下轮应该重试**）。统一"不再扫描"会把第二类一起挡住，反而危险。

**若确实需要降噪（列 V2，安全形态）**：记忆文件**只影响日志详略，绝不影响归档决策**——每轮归档决策仍完全由文件系统现状重算；标记命中时把逐行 `[SKIP]` 折叠成一行 `[INFO] 本轮跳过 3 个已知不合规文件（readme.txt, ...）`。

**V1 的零成本替代**：SKIP 逐行输出本就是 PRD §8-2 的验收要求，保留即可；等真被噪音困扰再上 V2 折叠。

---

## 12. 风险与注意点

| 风险 | 说明 | 应对 |
|---|---|---|
| Windows 控制台中文乱码 | 中文提示在部分终端编码异常 | 输出标签统一用英文（`[SKIP]`/`[WARN]`），索引文件固定 `encoding='utf-8'` |
| 路径拼接踩坑 | 手拼 `'/'` 在 Windows 下不稳 | 全程用 `pathlib`，禁止字符串拼路径 |
| 目标同名项是目录 | `copy2` 会抛异常 | 归入 `copy_failed`，`[ERROR]` 后继续（TC09 覆盖） |
| 长路径 / 特殊字符文件名 | Windows 260 字符限制 | `pathlib` 处理；失败即记 `[ERROR]`，不中断 |
| 索引段落膨胀 | 追加模式下文件会持续变长 | V1 接受（可追溯优先）；V2 可加日期归档或轮转 |

---

## 13. 下一步

1. **T1（返回 0）、T2（方案 A 拒绝）均已确认**；T3 结论：V1 不加"已扫描标记"（§11）。
2. **S1 已启动**：填空框架见 `s1_skeleton.py`（TODO-1 ~ TODO-5 + 自测命令），你写第一版实现；
3. S1 跑通 TC01 / TC02 后交我看 → 点评补漏 → 进 S2（`analyze`）。
