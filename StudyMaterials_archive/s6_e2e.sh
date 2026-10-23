#!/usr/bin/env bash
# ============================================================
# s6_e2e.sh —— S6 端到端验收（不用改，只用来跑）
# ------------------------------------------------------------
# 覆盖 TECH.md §9 的 TC01~TC13 中可在本机自动化的部分。
# 前置：archive.py / archive.sh 的 TODO 已填完。
# 用法：bash s6_e2e.sh
# ============================================================

set -u   # 用到未定义变量就报错
cd "$(dirname "$0")"  # 切换到脚本所在目录

# 日志统一 UTF-8：否则在代码页 936 的 Windows 上日志会被写成 GBK，看起来就是乱码
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

ROOT=tmp/e2e  
OUT=tmp/e2e_out
ok=0
total=0

assert() {                       # 定义断言函数，$1 描述  $2 条件（shell 表达式字符串）
    total=$((total + 1))
    if eval "$2" >/dev/null 2>&1; then
        echo "PASS  $1"
        ok=$((ok + 1))
    else
        echo "FAIL  $1"
        echo "      ↳ 判定条件: $2"      # 断言写错时（如多粘贴了字符）也能立刻看出来
    fi
}

# >/dev/null 2>&1  # 重定向标准错误输出到 /dev/null

# ---------- 构造夹具 ----------
rm -rf "$ROOT" "$OUT"
mkdir -p "$ROOT/src" "$ROOT/dest" "$ROOT/empty" "$OUT"

printf 'print(1)\n'        > "$ROOT/src/W34_test.py"
printf '# notes\n'         > "$ROOT/src/W34_notes.md"
printf '#!/bin/sh\necho\n' > "$ROOT/src/W34_scan.sh"
printf 'readme\n'          > "$ROOT/src/readme.txt"      # 首字符非 W
printf 'x\n'               > "$ROOT/src/w34_lower.py"    # 小写 w
printf 'a,b\n'             > "$ROOT/src/W34_data.csv"    # 后缀不支持
printf 'y\n'               > "$ROOT/src/W34test.py"      # 无下划线

# ---------- TC03~05 / TC12：dry-run 零副作用 + 三类跳过 ----------
bash archive.sh "$ROOT/src" "$ROOT/dest" --dry-run > "$OUT/tc03.log" 2>&1
rc=$?
assert "TC03 dry-run exit 0"        '[ "$rc" -eq 0 ]'
assert "TC03 计划归档 3 个"          '[ "$(grep -c "\[PLAN\]" "$OUT/tc03.log")" -eq 3 ]'
assert "TC03 dry-run 不建任何目录"    '[ -z "$(ls -A "$ROOT/dest")" ]'
assert "TC03 dry-run 不写索引"        '[ ! -f "$ROOT/dest/INDEX.md" ]'
assert "TC04 非 W 开头被 SKIP"        'grep -q "\[SKIP\].*readme.txt" "$OUT/tc03.log"'
assert "TC04 小写 w 被 SKIP"          'grep -q "\[SKIP\].*w34_lower.py" "$OUT/tc03.log"'
assert "TC05 csv 后缀被 SKIP"         'grep -q "\[SKIP\].*W34_data.csv" "$OUT/tc03.log"'
assert "TC12 无下划线给 WARN 提示"     'grep -q "\[WARN\].*W34test.py" "$OUT/tc03.log" && grep -q "未找到" "$OUT/tc03.log"'
assert "TC03 SUMMARY 文案为计划归档"   'grep -q "\[SUMMARY\] 计划归档 3 个" "$OUT/tc03.log"'

# ---------- TC06/07：run 真实移动 + 分类 ----------
bash archive.sh "$ROOT/src" "$ROOT/dest" > "$OUT/tc06.log" 2>&1
rc=$?
assert "TC06 run exit 0"             '[ "$rc" -eq 0 ]'
assert "TC06 py → W34/code"          '[ -f "$ROOT/dest/W34/code/W34_test.py" ]'
assert "TC06 sh → W34/code"          '[ -f "$ROOT/dest/W34/code/W34_scan.sh" ]'
assert "TC06 md → W34/note"          '[ -f "$ROOT/dest/W34/note/W34_notes.md" ]'
assert "TC06 有 [DONE] 输出"          'grep -q "\[DONE\]" "$OUT/tc06.log"'
assert "TC07 源文件已移走"            '[ ! -f "$ROOT/src/W34_test.py" ]'
assert "TC07 被跳过的文件仍留在源目录"  '[ -f "$ROOT/src/readme.txt" ]'

# ---------- TC10：索引 ----------
assert "TC10 INDEX.md 已生成"         '[ -f "$ROOT/dest/INDEX.md" ]'
assert "TC10 五字段表头齐全"           'grep -q "| 周号 | 文件名 | 源路径 | 目标路径 | 文件大小 |" "$ROOT/dest/INDEX.md"'
assert "TC10 三条归档记录"             '[ "$(grep -c "^| W34 |" "$ROOT/dest/INDEX.md")" -eq 3 ]'

# ---------- TC08：冲突跳过 + 不覆盖 ----------
printf 'changed\n' > "$ROOT/src/W34_test.py"
bash archive.sh "$ROOT/src" "$ROOT/dest" > "$OUT/tc08.log" 2>&1
assert "TC08 冲突给出 [WARN]"          'grep -q "\[WARN\].*W34_test.py" "$OUT/tc08.log"'
assert "TC08 冲突计入 "          'grep -q "冲突 1 个" "$OUT/tc08.log"'
assert "TC08 目标内容未被覆盖"          'grep -q "print(1)" "$ROOT/dest/W34/code/W34_test.py"'
assert "TC08 源文件仍在（未移动）"       '[ -f "$ROOT/src/W34_test.py" ]'

# ---------- TC11：空源目录 ----------
bash archive.sh "$ROOT/empty" "$ROOT/dest2" > "$OUT/tc11.log" 2>&1
rc=$?
assert "TC11 exit 0"                  '[ "$rc" -eq 0 ]'
assert "TC11 提示源目录无任何文件"       'grep -q "源目录无任何文件" "$OUT/tc11.log"'
assert "TC11 SUMMARY 全 0"             'grep -qE "\[SUMMARY\].*(计划归档|归档) 0 个，跳过 0 个，冲突 0 个，失败 0 个" "$OUT/tc11.log"'
assert "TC11 不创建目标目录"            '[ ! -d "$ROOT/dest2" ]'

# ---------- TC09：移动失败保护（父路径被文件占位） ----------
mkdir -p "$ROOT/src2" "$ROOT/dest3/W41"
printf 'keep\n'    > "$ROOT/src2/W41_test.py"
printf 'blocker\n' > "$ROOT/dest3/W41/code"     # 该占位必须是文件，不能是目录
bash archive.sh "$ROOT/src2" "$ROOT/dest3" > "$OUT/tc09.log" 2>&1
rc=$?
assert "TC09 exit 0（失败不算致命）"     '[ "$rc" -eq 0 ]'
assert "TC09 失败计入 SUMMARY"           'grep -q "失败 1 个" "$OUT/tc09.log"'
assert "TC09 源文件仍存在"               '[ -f "$ROOT/src2/W41_test.py" ]'
assert "TC09 有错误输出"                 'grep -qE "\[ERROR\]|复制失败" "$OUT/tc09.log"'

# ---------- TC01/02 + 自归档拒绝 ----------
bash archive.sh > "$OUT/tc01.log" 2>&1
rc=$?
assert "TC01 无参数 exit 1"              '[ "$rc" -eq 1 ]'
assert "TC01 打印用法"                   'grep -q "用法" "$OUT/tc01.log"'

bash archive.sh ./nodir ./dest > "$OUT/tc02.log" 2>&1
rc=$?
assert "TC02 源目录不存在 exit 1"        '[ "$rc" -eq 1 ]'
assert "TC02 有 Error 提示"              'grep -q "Error" "$OUT/tc02.log"'

bash archive.sh "$ROOT/src" "$ROOT/src" > "$OUT/tc14.log" 2>&1
rc=$?
assert "TC14 源=目标 被拒绝"             'grep -q "不能相同" "$OUT/tc14.log"'

echo ""
echo "$ok/$total 通过"
[ "$ok" -eq "$total" ] || exit 1
