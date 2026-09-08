# my_ai_journey
记录我自学AI的旅程，以作品为目标，在作品中学习，一步一步踏上AI之旅！！！

23年双非硕士毕业，现已工作3年多，通信测试开发岗，目前想转行AI。这个仓库就是记录我学习AI之旅。以作品为主要目标，在做作品的过程中学习基础知识。

## 作品

### 作品一：cli_todo · 命令行待办清单（第一个作品）

我 AI 之旅的**第一个作品**，纯 Python 实现的命令行待办清单工具，零三方依赖，仅支持 Windows。

- **功能**：`add` 添加 / `list` 查看 / `done` 标记完成 / `edit` 修改 / `del` 删除
- **数据持久化**：JSON 文件存储于 `%APPDATA%\cli_todo\todos.json`，采用原子写入（`.tmp` + `os.replace`）保证数据安全
- **学习价值**：完整走通「PRD → 技术方案 → 代码」的工程流程，从需求文档、技术选型、异常处理到验收测试逐条落地

详见 [`cli_todo/`](cli_todo/)。

### 作品二：BuildSelf_APP

通过 vibe coding 为自己设计的个人成长 App，仓库见 https://github.com/zw-wang820/BuildSelf_APP。
