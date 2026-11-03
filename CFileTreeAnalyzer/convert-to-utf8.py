#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量把目录下的 .c / .h 文件从 GBK 转成 UTF-8 无 BOM。
自动检测编码，已经是 UTF-8 的跳过。

Usage:
    python convert-to-utf8.py <directory>
    python convert-to-utf8.py E:\Project
"""

import os
import sys


def detect_and_convert(file_path: str) -> str:
    """
    检测文件编码并转成 UTF-8 无 BOM。
    返回: 转换结果说明
    """
    with open(file_path, 'rb') as f:
        raw = f.read()

    # 已经是 UTF-8 BOM，去掉 BOM 就行
    if raw.startswith(b'\xef\xbb\xbf'):
        with open(file_path, 'wb') as f:
            f.write(raw[3:])  # 去掉 BOM
        return 'UTF-8 BOM -> UTF-8 no BOM'

    # 已经是 UTF-8 无 BOM，跳过
    try:
        raw.decode('utf-8')
        return 'already UTF-8, skip'
    except UnicodeDecodeError:
        pass

    # 试试 GBK
    try:
        text = raw.decode('gbk')
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            f.write(text)
        return 'GBK -> UTF-8'
    except UnicodeDecodeError:
        pass

    # 试试 Latin-1 兜底
    try:
        text = raw.decode('latin-1')
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            f.write(text)
        return 'Latin-1 -> UTF-8'
    except Exception as e:
        return f'failed: {e}'


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    root_dir = sys.argv[1]
    if not os.path.isdir(root_dir):
        print(f"Error: '{root_dir}' is not a directory.")
        sys.exit(1)

    count = 0
    converted = 0
    skipped = 0

    for dirpath, dirnames, filenames in os.walk(root_dir):
        for fn in filenames:
            if fn.endswith('.c') or fn.endswith('.h'):
                src = os.path.join(dirpath, fn)
                result = detect_and_convert(src)
                count += 1
                if 'skip' in result:
                    skipped += 1
                else:
                    converted += 1
                    print(f"  {src}: {result}")

    print()
    print(f"Done. Total: {count}, Converted: {converted}, Skipped: {skipped}")


if __name__ == '__main__':
    main()
