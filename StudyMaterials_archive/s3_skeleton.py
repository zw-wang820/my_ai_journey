"""
S3 阶段：build_dst / format_size / plan_one —— 目标路径、大小格式化、单文件计划
================================================================================
对应 TECH.md §3 函数 4/5/6、§10 步骤 S3。

三个函数的职责（单一职责，各自独立可测）：
  build_dst(dest, week, category, name) -> Path
      目标路径 = dest / week / category / name
  format_size(n) -> str
      < 1024        -> '512 B'（整数）
      < 1024*1024   -> '1.2 KB'（除以 1024，保留 1 位小数）
      否则           -> '3.5 MB'（除以 1024*1024，保留 1 位小数）
  plan_one(f, dest) -> dict
      对单个文件生成归档计划，三种状态：
        skip     : analyze 判为跳过   -> {'status','reason'}
        plan     : 目标不存在，可归档 -> {'status','week','category','src','dst','size'}
        conflict : 目标已存在同名文件 -> 同 plan 的字段，status='conflict'

填写说明：
  - 三个 TODO 顺序无依赖，可以先易后难；
  - analyze 直接从 s2_analyze 导入使用（你已经写好并通过验收的代码）；
  - 写完跑 python s3_skeleton.py，期望 9/9 通过。
"""

import tempfile
from pathlib import Path

from s2_analyze import analyze


# TODO-1: build_dst —— 拼目标路径
def build_dst(dest: Path, week: str, category: str, name: str) -> Path:
    """
    参数: dest 目标根目录; week 周号; category 'code'|'note'; name 原文件名
    返回: Path —— dest / week / category / name
    提示: pathlib 的 Path 对象支持用 / 运算符拼接，比字符串拼路径安全
    """
    return dest / week / category / name



# TODO-2: format_size —— 字节数转人类可读
def format_size(n: int) -> str:
    """
    参数: n 文件字节数（f.stat().st_size 的返回值就是 int）
    返回: '512 B' / '1.2 KB' / '3.5 MB' 这样的字符串
    提示: 两个分界点 1024 和 1024*1024；KB/MB 保留 1 位小数（f-string 的 :.1f）
    """
    if n < 1024:
        return f"{n} B"
    elif n < 1024*1024:
        return f"{n/1024:.1f} KB"
    else:
        return f"{n/(1024*1024):.1f} MB"


# TODO-3: plan_one —— 单文件归档计划
def plan_one(f: Path, dest: Path) -> dict:
    """
    参数: f 源文件的完整 Path; dest 目标根目录
    返回:
      skip     -> {'status': 'skip', 'reason': <analyze 的 reason>}
      plan     -> {'status': 'plan', 'week', 'category', 'src': f, 'dst': Path, 'size': int}
      conflict -> 同 plan 字段，但 'status' = 'conflict'（dst 已存在同名文件）
    步骤:
      1) r = analyze(f.name)；skip 则直接返回 skip 计划
      2) dst = build_dst(...)；size = f.stat().st_size
      3) dst.exists() ? conflict : plan
    """
    r = analyze(f.name)
    if r['status'] == 'skip':
        return r
    week = r['week']
    category = r['category']
    dst = build_dst(dest, week, category, f.name)
    size = f.stat().st_size
    if dst.exists():
        return {'status': 'conflict', 'week': week, 'category': category, 'src': f, 'dst': dst, 'size': size}
    else:
        return {'status': 'plan', 'week': week, 'category': category, 'src': f, 'dst': dst, 'size': size}


# ============================================================
# 自测台（不用改）：临时目录 + 预置夹具，全程不碰你的真实文件
# ============================================================

BUILD_CASES = [
    (Path('archive'), 'W34', 'code', 'W34_test.py', 'archive/W34/code/W34_test.py'),
    (Path('archive'), 'W1', 'note', 'W1_notes.md', 'archive/W1/note/W1_notes.md'),
]

SIZE_CASES = [
    (0, '0 B'),
    (512, '512 B'),
    (1229, '1.2 KB'),
    (3670016, '3.5 MB'),
]


def run_selftest() -> int:
    passed, total = 0, 0

    # build_dst
    for dest, week, category, name, expect in BUILD_CASES:
        total += 1
        got = str(build_dst(dest, week, category, name)).replace('\\', '/')
        ok = got == expect
        print(f"{'PASS' if ok else 'FAIL'}  build_dst {week}/{category} -> {got}")
        passed += ok

    # format_size
    for n, expect in SIZE_CASES:
        total += 1
        got = format_size(n)
        ok = got == expect
        print(f"{'PASS' if ok else 'FAIL'}  format_size({n}) -> '{got}' (期望 '{expect}')")
        passed += ok

    # plan_one：临时目录夹具
    with tempfile.TemporaryDirectory() as td:
        src, dest = Path(td) / 'src', Path(td) / 'dest'
        src.mkdir()
        (src / 'W35_test.py').write_text('hello')          # 5 B，全新 -> plan
        (src / 'W34_test.py').write_text('hello')          # 与夹具同名 -> conflict
        (src / 'readme.txt').write_text('x')               # -> skip
        # 预置冲突夹具：dest/W34/code/W34_test.py 已存在
        (dest / 'W34' / 'code').mkdir(parents=True)
        (dest / 'W34' / 'code' / 'W34_test.py').write_text('old')

        total += 1
        got = plan_one(src / 'W35_test.py', dest)
        ok = (got.get('status') == 'plan'
              and got.get('week') == 'W35'
              and got.get('category') == 'code'
              and got.get('size') == 5
              and got.get('dst').name == 'W35_test.py')
        print(f"{'PASS' if ok else 'FAIL'}  plan_one W35_test.py -> {got}")
        passed += ok

        total += 1
        got = plan_one(src / 'W34_test.py', dest)
        ok = got.get('status') == 'conflict' and got.get('dst').name == 'W34_test.py'
        print(f"{'PASS' if ok else 'FAIL'}  plan_one W34_test.py(冲突) -> {got}")
        passed += ok

        total += 1
        got = plan_one(src / 'readme.txt', dest)
        ok = got.get('status') == 'skip' and got.get('reason') == '首字符非 W'
        print(f"{'PASS' if ok else 'FAIL'}  plan_one readme.txt -> {got}")
        passed += ok

    print(f"\n{passed}/{total} 通过")
    return 0 if passed == total else 1


if __name__ == '__main__':
    raise SystemExit(run_selftest())
