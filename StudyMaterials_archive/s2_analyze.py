"""
S2 阶段：analyze —— 文件名分析
================================
对应 TECH.md §3 函数 3、§10 步骤 S2。

规则（PRD §5.1，检查顺序不可颠倒）：
  1) 首字符必须是大写字母 W         → 否则 skip，reason='首字符非 W'
  2) 必须含 '_'                     → 否则 skip，reason='未找到 _ 分隔符'
  3) 周号 = 第一个 '_' 之前的字段    → W1 / W34 / W100 都合法（不强制两位数字）
  4) 后缀分类：
       .py → code      .sh → code      .md → note
       其他 → skip，reason='不支持的后缀'

返回 dict（四种键固定都有，便于下游统一取值）：
  {'status': 'ok' | 'skip', 'week': str, 'category': str, 'reason': str}

填写说明：
  - 只填 TODO-A / TODO-B / TODO-C 三处；
  - 提示里给的是思路不是答案，尽量自己写；
  - 写完后跑本文件（python s2_analyze.py），会打印 7 条用例的 PASS / FAIL。
"""

from pathlib import Path

# 后缀 → 目标子目录（PRD §5.1 表格）
CATEGORY_MAP = {
    '.py': 'code',
    '.sh': 'code',
    '.md': 'note',
}


def analyze(name: str) -> dict:
    """
    分析单个文件名，返回归档判定结果。

    参数: name —— 纯文件名（不带目录），如 'W34_test.py'
    返回: {'status', 'week', 'category', 'reason'}
    """

    # TODO-A: 首字符校验
    #   不是大写 W → 直接 return skip 结果，reason='首字符非 W'
    #   提示：str.startswith('W')；注意不能用 lower()，'w' 必须被拒绝
    if not name.startswith('W'):
        return {'status': 'skip', 'week': '', 'category': '', 'reason': '首字符非 W'}

    

    # TODO-B: 下划线校验 + 切出周号
    #   不含 '_' → return skip，reason='未找到 _ 分隔符'
    #   含 '_'   → week = 第一个 '_' 之前的部分
    #   提示：'W34_test.py'.split('_', 1) 的结果是什么？先取第一个元素
    if '_' not in name:
        return {'status': 'skip', 'week': '', 'category': '', 'reason': '未找到 _ 分隔符'}
    
    week = name.split('_', 1)[0]  #里面的1代表只切分一次

    # TODO-C: 后缀分类
    #   Path(name).suffix 得到 '.py' 这样的字符串
    #   在 CATEGORY_MAP 里查得到 → category = 对应值（code / note）
    #   查不到 → return skip，reason='不支持的后缀'
    #   注意：V1 按 PRD 严格小写后缀匹配，'.PY' 会被判为不支持（已知边界，不要求改）
    filename_suffix = Path(name).suffix
    if filename_suffix not in CATEGORY_MAP:
        return {'status': 'skip', 'week': '', 'category': '', 'reason': '不支持的后缀'}
        
    category = CATEGORY_MAP[filename_suffix]


    # 全部通过：返回 ok 结果
    return {'status': 'ok', 'week': week, 'category': category, 'reason': ''}


# ============================================================
# 自测台（不用改；它只是拿你的 analyze 去跑固定用例）
# ============================================================

CASES = [
    ('W34_test.py',      'ok',   'W34',  'code', ''),
    ('W1_test.sh',       'ok',   'W1',   'code', ''),
    ('W100_notes.md',    'ok',   'W100', 'note', ''),
    ('readme.txt',       'skip', '',     '',     '首字符非 W'),
    ('w34_test.py',      'skip', '',     '',     '首字符非 W'),
    ('W34_data.csv',     'skip', '',     '',     '不支持的后缀'),
    ('W34test.py',       'skip', '',     '',     '未找到 _ 分隔符'),
]


def run_selftest() -> int:
    passed = 0
    for name, status, week, category, reason in CASES:
        got = analyze(name)
        ok = (
            got.get('status') == status
            and got.get('week') == week
            and got.get('category') == category
            and got.get('reason') == reason
        )
        print(f"{'PASS' if ok else 'FAIL'}  {name:<16} -> {got}")
        if ok:
            passed += 1
    print(f"\n{passed}/{len(CASES)} 通过")
    return 0 if passed == len(CASES) else 1


if __name__ == '__main__':
    raise SystemExit(run_selftest())
