#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键生成 C 函数调用树
流程：预处理（展开头文件+裁剪条件编译） → 分析函数调用关系 → 输出 tree.txt

配置全部从 call_tree_defines.txt 读取，直接跑就行：
    python build_call_tree.py
"""

import os
import sys
import subprocess


# ==================== 配置文件读取 ====================

CONFIG_FILE_NAME = 'call_tree_defines.txt'


def load_config(config_path: str) -> dict:
    """读取配置文件，返回字典"""
    config = {
        'input': '.',
        'output': './_preprocessed',
        'include': [],
        'defines': set(),
    }

    if not os.path.exists(config_path):
        return config

    with open(config_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '#' in line:
                line = line[:line.index('#')].strip()
            if not line:
                continue

            if line.lower().startswith('input:'):
                config['input'] = line[6:].strip()
            elif line.lower().startswith('output:'):
                config['output'] = line[7:].strip()
            elif line.lower().startswith('include:'):
                path = line[8:].strip()
                if path:
                    config['include'].append(path)
            else:
                config['defines'].add(line)

    return config


# ==================== 主流程 ====================

def main():
    config_path = os.path.join(os.getcwd(), CONFIG_FILE_NAME)
    config = load_config(config_path)

    input_dir = config['input']
    output_dir = config['output']

    print("=" * 60)
    print("Step 1: Preprocessing (expand headers, trim conditional code)")
    print("=" * 60)
    print(f"  Input:  {input_dir}")
    print(f"  Output: {output_dir}")
    print()

    # 第一步：调用预处理器
    preprocessor_script = os.path.join(os.path.dirname(__file__), 'c-preprocessor.py')
    cmd = [sys.executable, preprocessor_script, input_dir]
    # 输出目录已经在配置文件里了，不用传

    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
    print(result.stdout)
    if result.stderr:
        print(result.stderr)

    if result.returncode != 0:
        print("Preprocessing failed!")
        sys.exit(1)

    print()
    print("=" * 60)
    print("Step 2: Analyzing call graph (generate call tree)")
    print("=" * 60)

    # 第二步：调用调用树分析工具，分析预处理后的目录
    analyzer_script = os.path.join(os.path.dirname(__file__), 'c-call-tree-analyzer.py')
    cmd = [sys.executable, analyzer_script, output_dir]

    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
    print(result.stdout)
    if result.stderr:
        print(result.stderr)

    if result.returncode != 0:
        print("Call tree analysis failed!")
        sys.exit(1)

    print()
    print("=" * 60)
    print("All done!")
    print(f"  Call tree:  {os.path.join(os.getcwd(), 'tree.txt')}")
    print(f"  Preprocessed source:  {output_dir}")
    print("=" * 60)


if __name__ == '__main__':
    main()
