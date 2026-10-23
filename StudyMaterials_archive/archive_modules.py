"""
S6 阶段：archive.py —— 编排入口（把 S1~S5 串成一条流水线）
=============================================================
对应 TECH.md §4（主流程）、§5（输出标签）、§10 步骤 S6。

本阶段只写「编排」，不写新算法 —— 所有能力都来自你已经通过验收的模块：
  s1_skeleton   print_usage / parse_args / check_src
  s2_analyze    analyze（已被 plan_one 内部调用）
  s3_skeleton   plan_one / build_dst / format_size
  s4_move       do_move（五步移动 + 失败保护）
  s5_index      append_index / summarize

输出标签规范（TECH.md §5）：
  [PLAN]     dry-run 下：文件将被归档
  [DONE]     run 下：文件已移动完成
  [SKIP]     首字符非 W / 无 `_` / 后缀不支持
  [WARN]     冲突（目标已存在）/ 删源失败 / 源目录为空
  [ERROR]    复制失败
  [SUMMARY]  结尾一行

四个 TODO（按 main 里的顺序填，可以边填边跑 s6_e2e.sh）：
  A 空目录早退              → TC11
  B 生成 plans              → TC03/04/05 的前提
  C 逐条输出 + 真实移动      → TC06/07/08/09
  D 写索引 + 打印 SUMMARY    → TC10

写完跑 bash s6_e2e.sh，期望全部 PASS。

注意：本阶段先用「模块导入」跑通端到端；全绿之后我们再做最后一步收尾
      —— 把这些模块合并成单文件 archive.py（交付形态），那时 s*_*.py 只作学习痕迹保留。
"""

import sys
from datetime import datetime
from pathlib import Path

from s1_skeleton import check_src, parse_args
from s3_skeleton import plan_one
from s4_move import do_move
from s5_index import append_index, summarize


def collect_files(src: Path) -> list:
    """
    取源目录顶层的文件（PRD §3.2：不递归），按文件名排序保证输出稳定可复现。

    为什么先过滤 is_file()：目标目录建出来的是**目录**，递归/重复扫描时
    不会被误当文件处理；这里显式写上，语义更清楚。
    """
    return sorted([p for p in src.iterdir() if p.is_file()], key=lambda p: p.name)


def main() -> int:
    src, dest, dry_run = parse_args(sys.argv[1:])
    check_src(src)

    # 自归档校验（TECH §11 T2 方案 A）：源与目标是同一个目录 → 直接拒绝
    if src.resolve() == dest.resolve():
        print('[ERROR] 源目录与目标目录不能相同')
        return 1

    files = collect_files(src)

    # TODO-A: 空目录早退（PRD §6.5 / TC11）
    #   1) files 为空 → 打印 '[WARN] 源目录无任何文件'
    #   2) 再打印一行全 0 的 SUMMARY：直接用 summarize([], dry_run)
    #   3) return 0（空目录不是错误，exit 0）
    #   注意：此时**不要**创建目标目录、不要写索引
    if not files:
        print('[WARN] 源目录无任何文件')
        print(summarize([], dry_run))
        return 0
      

    # TODO-B: 生成计划（TC03/04/05 的前提）
    #   对 files 里每个文件调 plan_one(f, dest)，收集成 plans 列表
    #   提示：列表推导式一行即可 —— [plan_one(f, dest) for f in files]
    plans = [plan_one(f, dest) for f in files]

    # TODO-C: 逐条输出 + run 模式真实移动（TC06/07/08/09）
    #   遍历时用 zip(files, plans) 成对取 —— 原因见下方「注意」。
    #   按 status 分支：
    #     'skip'     → 无 `_` 的用 [WARN]（PRD §6.5），其余用 [SKIP]：
    #                    label = '[WARN]' if '未找到' in plan['reason'] else '[SKIP]'
    #                    print(f"{label} {f.name} ({plan['reason']})")
    #     'conflict' → print(f"[WARN] {f.name} 目标已存在，跳过")
    #     'plan'     → dry-run: print(f"[PLAN] {f.name} -> {plan['dst']}")
    #                  run    : r = do_move(plan['src'], plan['dst'])
    #                           r == 'ok' → print(f"[DONE] {f.name} -> {plan['dst']}")
    #                           r != 'ok' → plan['status'] = 'failed'（原因 do_move 已打印）
    #   提示：改 plan['status'] 是「让计划反映执行结果」的关键一步，
    #         summarize 靠它统计失败数；不要另开一个计数器。
    #
    #   ⚠️ 注意（很重要，S3 遗留的契约不一致）：
    #      plan_one 的 skip 分支是直接透传 analyze 的结果，**没有 'src' 键**！
    #      所以 skip 分支不能写 plan['src'].name（会 KeyError）。
    #      两个选择：
    #        ① 这里用 zip(files, plans) 用 f.name（本骨架建议，不动 S3）
    #        ② 回头把 plan_one 统一成「任何分支都带 'src': f」（契约更整齐，但 S3 要重跑 9/9）
    for f, plan in zip(files, plans):
        if plan['status'] == 'plan':
            if dry_run:
                print(f"[PLAN] {f.name} -> {plan['dst']}")
            else:
                r = do_move(plan['src'], plan['dst'])
                if r == 'ok':
                    print(f"[DONE] {f.name} -> {plan['dst']}")
                else:
                    plan['status'] = 'failed'
        elif plan['status'] == 'conflict':
            print(f"[WARN] {f.name} 目标已存在，跳过")
        else:
            label = '[WARN]' if '未找到' in plan['reason'] else '[SKIP]'
            print(f"{label} {f.name} ({plan['reason']})")

    # TODO-D: 写索引 + 打印 SUMMARY（TC10）
    #   1) records = [p for p in plans if p['status'] == 'plan']
    #      注意：必须是「执行成功后 status 仍为 plan」的记录，失败/冲突/跳过都不入索引
    #   2) 只有 run 模式且 records 非空才 append_index(dest, records)
    #      （dry-run 绝不写索引 —— PRD §6.3）
    #   3) print(summarize(plans, dry_run))
    #   4) return 0（批次内个别失败也返回 0 —— TECH §11 T1 已确认）
    records = [p for p in plans if p['status'] == 'plan']
    if not dry_run and records:
        append_index(dest, records)
    print(summarize(plans, dry_run))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
