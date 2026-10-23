"""
S4 阶段：do_move —— 两步走移动 + 失败保护
==========================================
对应 TECH.md §7、§10 步骤 S4。这是整个工具最关键的一段：**任何失败都不能丢源文件**。

五步流程（顺序不能变）：
  1) dst.parent.mkdir(parents=True, exist_ok=True)  建目标父目录
  2) shutil.copy2(src, dst)                          复制（保留元数据）
     1~2 任一步抛 OSError → 返回 'copy_failed'
  3) 校验 dst.exists()：不存在 → 'copy_failed'
  4) src.unlink()                                    删源
     抛 OSError → 返回 'unlink_failed'
  5) 校验 src.exists()：仍存在 → 'unlink_failed'
     否则 → 'ok'

三种返回值含义：
  'ok'            移动完成（源已消失、目标已存在）
  'copy_failed'   复制没成功，源文件原样保留
  'unlink_failed' 复制成功但源删不掉，源与目标都存在（留一份重复，不丢数据）

填写说明：
  - 四个 TODO，注意 try 的范围：mkdir 也要在 try 里（目录被文件占位时会抛错）；
  - 写完跑 python s4_move.py，期望 3/3 通过；
  - 三条用例（正常移动 / 复制失败 / 删源失败）全部可自动化，无需手工验证。
"""

import errno
import shutil
import tempfile
from pathlib import Path


def explain_oserror(exc: OSError) -> str:
    """
    把建目录 / 复制时抛出的 OSError 归类成可读原因。

    Python 会把常见 errno 映射成具体子类（PermissionError 等），
    其余（如磁盘满 ENOSPC）仍是普通 OSError，只能看 errno 判断。
    """
    if isinstance(exc, PermissionError):
        return '权限不足：目标目录不可写，或目标文件正被其他程序占用'
    if isinstance(exc, FileExistsError):
        return '目标目录路径已被同名文件占用，无法建目录'
    if isinstance(exc, NotADirectoryError):
        return '目标路径中间有一段是文件而不是目录'
    if isinstance(exc, IsADirectoryError):
        return '目标位置已存在同名目录'
    if isinstance(exc, FileNotFoundError):
        return '源文件或上级目录不存在（可能已被其他进程移动/删除）'
    if exc.errno == errno.ENOSPC:
        return '磁盘空间不足，清理空间后重试'
    if exc.errno == errno.EDQUOT:
        return '超出用户磁盘配额'
    if exc.errno == errno.EROFS:
        return '目标位于只读文件系统或只读介质'
    if exc.errno == errno.ENAMETOOLONG:
        return '路径过长（Windows 默认上限约 260 字符）'
    if exc.errno == errno.EXDEV:
        return '跨设备操作被拒绝'
    return f'未归类错误（errno={exc.errno}）'


def do_move(src: Path, dst: Path) -> str:
    """
    参数: src 源文件 Path; dst 目标文件 Path（含文件名）
    返回: 'ok' | 'copy_failed' | 'unlink_failed'
    """

    # TODO-1: 建父目录 + 复制，包在 try/except OSError 里
    #   失败时 return 'copy_failed'
    #   提示：dst.parent.mkdir(parents=True, exist_ok=True)
    #         shutil.copy2(src, dst)
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    except OSError as exc:
        print(f"复制失败：{src} -> {dst}")
        print(f"  原因：{explain_oserror(exc)}")
        print(f"  原始异常：{type(exc).__name__}: {exc}")
        return 'copy_failed'
    
    # TODO-2: 复制后复核目标是否真的存在
    #   if not dst.exists(): return 'copy_failed'
    #   为什么要复核？因为「没抛异常」不等于「文件真的落地了」
    if not dst.exists():
        print(f"复制失败：{src} -> {dst}")
        return 'copy_failed'

    # TODO-3: 删源，包在 try/except OSError 里
    #   失败时 return 'unlink_failed'（注意：此时源文件必须保留）
    #   提示：src.unlink()
    try:
        src.unlink()
    except OSError:
        print(f"删除源失败：{src}")
        return 'unlink_failed'

    # TODO-4: 删源后复核源是否真的消失
    #   if src.exists(): return 'unlink_failed'
    if src.exists():
        print(f"删除源失败：{src}")
        return 'unlink_failed'

    # 全部通过
    return 'ok'


# ============================================================
# 自测台（不用改）
# ============================================================

def run_selftest() -> int:
    passed, total = 0, 0

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)

        # 用例 1：正常移动 → ok（源消失、目标存在、内容一致）
        total += 1
        src = root / 'W34_test.py'
        src.write_text('hello')
        dst = root / 'out' / 'W34' / 'code' / 'W34_test.py'
        r = do_move(src, dst)
        ok = (r == 'ok' and dst.exists() and not src.exists()
              and dst.read_text(encoding='utf-8') == 'hello')
        print(f"{'PASS' if ok else 'FAIL'}  正常移动 -> {r} (dst={dst.exists()}, src={src.exists()})")
        passed += ok

        # 用例 2：目标父路径被文件占位 → 建目录就失败 → copy_failed，源必须还在
        total += 1
        src2 = root / 'W35_test.py'
        src2.write_text('keep me')
        blocker = root / 'out2' / 'W35' / 'code'
        blocker.parent.mkdir(parents=True)
        blocker.write_text('i am a file, not a dir')
        dst2 = blocker / 'W35_test.py'
        r2 = do_move(src2, dst2)
        ok2 = (r2 == 'copy_failed' and src2.exists()
               and src2.read_text(encoding='utf-8') == 'keep me')
        print(f"{'PASS' if ok2 else 'FAIL'}  父路径被占位 -> {r2} (src 保留={src2.exists()})")
        passed += ok2

        # 用例 3：源文件被占用 → 删源失败 → unlink_failed，源与目标必须同时存在
        # 说明：Windows 下「只读属性」并不会阻止 unlink（实测 attrib +R 仍能删除），
        #       真正能阻止删除的是「文件被打开占用」（共享锁）。所以这里持一个句柄。
        total += 1
        src3 = root / 'W36_test.py'
        src3.write_text('duplicate me')
        dst3 = root / 'out3' / 'W36' / 'code' / 'W36_test.py'
        handle = open(src3, 'rb')
        try:
            r3 = do_move(src3, dst3)
        finally:
            handle.close()
        ok3 = (r3 == 'unlink_failed' and src3.exists() and dst3.exists()
               and dst3.read_text(encoding='utf-8') == 'duplicate me')
        print(f"{'PASS' if ok3 else 'FAIL'}  源被占用 -> {r3} "
              f"(src 保留={src3.exists()}, dst 存在={dst3.exists()})")
        passed += ok3

    print(f"\n{passed}/{total} 通过")
    return 0 if passed == total else 1


if __name__ == '__main__':
    raise SystemExit(run_selftest())


# ============================================================
# 关于 unlink_failed 的验证方式（重要纠错）
# ------------------------------------------------------------
# 网上常见的「attrib +R 造只读文件」在本场景**无效**：Windows 的只读属性
# 可以被 os.unlink 无视（实测属性为 ReadOnly 时仍删除成功，返回 'ok'）。
# 真正能阻止删除的是文件被其它句柄占用（共享锁冲突 → PermissionError）。
# 用例 3 用 open(src, 'rb') 持句柄的方式覆盖了这个分支，已自动化。
# ============================================================
