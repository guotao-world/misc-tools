#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动生成 README.md 目录（TOC）— 适用于 misc-tools 工具集合仓库

功能：
1. 扫描仓库根目录下的所有工具子目录
2. 为每个工具生成 Markdown 链接
3. 只替换 README.md 中 <!-- TOC START --> 和 <!-- TOC END --> 之间的内容
4. 不修改 README.md 其他内容

用法：
    python scripts/generate_toc.py
"""

import os
import re
import sys

# 仓库根目录（脚本所在目录的上一级）
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# README.md 路径
README_PATH = os.path.join(REPO_ROOT, "README.md")

# TOC 标记
TOC_START = "<!-- TOC START -->"
TOC_END = "<!-- TOC END -->"

# 忽略的目录
IGNORE_DIRS = {".git", "scripts", "images", ".github", "__pycache__"}


def scan_tools(repo_root):
    """
    扫描仓库根目录下的所有工具子目录。

    返回：
        list: 工具目录名列表（已排序）
    """
    tools = []

    for entry in sorted(os.listdir(repo_root)):
        full_path = os.path.join(repo_root, entry)

        # 只处理目录
        if not os.path.isdir(full_path):
            continue

        # 过滤忽略的目录
        if entry in IGNORE_DIRS:
            continue

        tools.append(entry)

    return tools


def generate_toc(tools):
    """
    根据工具目录列表生成 TOC 内容。

    格式：
        - [CFileTreeAnalyzer](./CFileTreeAnalyzer)
          C 代码调用树分析工具
    """
    lines = []

    for tool in sorted(tools):
        # 生成 Markdown 链接
        link_path = f"./{tool}"
        lines.append(f"- [{tool}]({link_path})")

        # 尝试读取工具自己的 README.md 第一行标题作为描述
        tool_readme = os.path.join(repo_root := REPO_ROOT, tool, "README.md")
        if os.path.exists(tool_readme):
            try:
                with open(tool_readme, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("# "):
                            desc = line[2:].strip()
                            lines.append(f"  {desc}")
                            break
            except Exception:
                pass

    return "\n".join(lines)


def update_readme_toc(readme_path, toc_content):
    """
    更新 README.md 中的 TOC 区域。
    只替换 <!-- TOC START --> 和 <!-- TOC END --> 之间的内容。
    如果标记不存在，返回 False。
    """
    try:
        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"Error: cannot read README.md: {e}", file=sys.stderr)
        return False

    # 检查 TOC 标记是否存在
    if TOC_START not in content or TOC_END not in content:
        print(f"Error: {TOC_START} or {TOC_END} not found in README.md", file=sys.stderr)
        return False

    # 构建新的 TOC 区域（包含标记）
    new_toc_block = f"{TOC_START}\n{toc_content}\n{TOC_END}"

    # 使用正则替换 TOC 区域（非贪婪匹配）
    pattern = re.escape(TOC_START) + r".*?" + re.escape(TOC_END)
    new_content = re.sub(pattern, new_toc_block, content, flags=re.DOTALL)

    # 检查内容是否有变化
    if new_content == content:
        print("TOC already up to date, no changes needed.")
        return False

    # 写入新内容
    try:
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("README.md TOC updated.")
        return True
    except Exception as e:
        print(f"Error: cannot write README.md: {e}", file=sys.stderr)
        return False


def main():
    """主函数"""
    print(f"Repo root: {REPO_ROOT}")
    print(f"README.md: {README_PATH}")
    print()

    # 1. 扫描工具目录
    print("Scanning tool directories...")
    tools = scan_tools(REPO_ROOT)
    print(f"Found {len(tools)} tools: {', '.join(tools)}")
    print()

    # 2. 生成 TOC
    print("Generating TOC...")
    toc_content = generate_toc(tools)
    print()

    # 3. 更新 README.md
    print("Updating README.md...")
    updated = update_readme_toc(README_PATH, toc_content)

    if updated:
        print()
        print("Done. README.md TOC has been updated.")
        sys.exit(0)
    else:
        print()
        print("Done. No changes needed.")
        sys.exit(0)


if __name__ == "__main__":
    main()
