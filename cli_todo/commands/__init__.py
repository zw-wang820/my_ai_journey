"""子命令注册表：将命令名映射到对应模块的 run 函数。"""

from .add import run as add
from .list_cmd import run as list_cmd
from .done import run as done
from .edit import run as edit
from .delete import run as delete

COMMANDS = {
    "add": add,
    "list": list_cmd,
    "done": done,
    "edit": edit,
    "del": delete,
}

__all__ = ["COMMANDS"]
