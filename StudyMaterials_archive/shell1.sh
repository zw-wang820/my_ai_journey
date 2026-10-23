#!/bin/bash
# archive.sh
SRC=$1        # 待归档目录
DEST=$2       # 归档根目录，如 ./archive
# TODO: 检查 $SRC 是否存在，不存在则报错退出
if [ ! -d "$SRC" ]; then
    echo "Error: $SRC does not exist"
    exit 1
else
    python3 archive.py "$SRC" "$DEST" "${3:-run}"
fi

# TODO: 调用 python3 archive.py "$SRC" "$DEST" "${3:-run}"
