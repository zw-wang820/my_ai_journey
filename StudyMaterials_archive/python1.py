# archive.py
import sys, re, shutil
from pathlib import Path

src, dest, mode = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
pattern = re.compile(r'[W](\d{2})...')  # TODO: 你定的周号规则

for f in src.iterdir():
    m = pattern.search(f.name)
    # TODO: 匹配到 → 算出周目录名（如 archive/W01）
    if m:
        week_dir = dest / f'W{m.group(1)}'
        week_dir.mkdir(parents=True, exist_ok=True)
        if week_dir / f.name.exists():
            print(f'Warning: {week_dir / f.name} already exists')
            continue
        else:
            if mode == 'run':
                shutil.copy(f, week_dir / f.name)
            else:
                print(f'Copied {f} to {week_dir / f.name}')
    # TODO: mode == "dry-run" 只 print 计划；否则执行移动（想好冲突策略）
    # TODO: 没匹配到 → 你的策略 3
    else:
        print(f'No match for {f}')
    
# TODO: 生成 INDEX.md（想好索引里每行记什么）
with open(dest / 'INDEX.md', 'w') as f:
    f.write('# Index\n\n')
    for week_dir in dest.iterdir():
        if week_dir.is_dir():
            f.write(f'## {week_dir.name}\n\n')
            for f in week_dir.iterdir():
                f.write(f'* {f.name}\n')
            f.write('\n\n')


