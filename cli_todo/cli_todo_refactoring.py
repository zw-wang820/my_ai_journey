"""兼容入口薄壳。

业务逻辑已拆分到 main.py、models/、commands/。
保留 `python cli_todo.py ...` 的旧调用方式，转发至 main.main()。
"""
import sys

from main import main

# 数据目录与存储实现已迁移至 models/storage.py

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n操作已取消")
        sys.exit(130)
    except Exception as e:
        print(f"未预期的错误：{e}")
        sys.exit(1)