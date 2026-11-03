#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C Preprocessor - 基于 pcpp 的完整 C 预处理器
展开 #include 头文件 + 宏定义收集 + 条件编译裁剪 + 去注释。

Configuration file (call_tree_defines.txt):
    output: ./_preprocessed       # 预处理输出目录
    include: ./PDT/src            # 头文件搜索路径（可多行）
    LINUX                         # 宏开关（直接写宏名）

Usage:
    python c-preprocessor.py <input_dir_or_file>
"""

import os
import sys
import io
import pcpp


# ==================== 自定义预处理器（解决编码混乱问题） ====================

class MyPreprocessor(pcpp.Preprocessor):
    """重写文件打开方法，自动检测编码，避免 GBK/UTF-8 混编报错"""

    def on_file_open(self, is_system_include, filename):
        # 先读原始字节，检测编码
        with open(filename, 'rb') as f:
            raw = f.read()

        # 检测 UTF-8 BOM
        if raw.startswith(b'\xef\xbb\xbf'):
            encoding = 'utf-8-sig'
        # 检测 UTF-16 BOM
        elif raw.startswith(b'\xff\xfe') or raw.startswith(b'\xfe\xff'):
            encoding = 'utf-16'
        else:
            # 没有 BOM，先试 GBK，失败就用 latin-1 兜底
            try:
                raw.decode('gbk')
                encoding = 'gbk'
            except UnicodeDecodeError:
                encoding = 'latin-1'

        # 用检测到的编码打开文件
        return io.StringIO(raw.decode(encoding, errors='ignore'))


# ==================== 配置文件读取 ====================

CONFIG_FILE_NAME = 'call_tree_defines.txt'


def load_config(config_path: str) -> tuple:
    """
    从配置文件读取配置。
    返回: (defines_set, include_paths_list, output_dir_str, input_dir_str)
    """
    defines = set()
    include_paths = []
    output_dir = None
    input_dir = None

    if not os.path.exists(config_path):
        return defines, include_paths, output_dir, input_dir

    with open(config_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '#' in line:
                line = line[:line.index('#')].strip()
            if not line:
                continue

            if line.lower().startswith('include:'):
                path = line[8:].strip()
                if path:
                    include_paths.append(path)
            elif line.lower().startswith('output:'):
                output_dir = line[7:].strip()
            elif line.lower().startswith('input:'):
                input_dir = line[6:].strip()
            else:
                defines.add(line)

    return defines, include_paths, output_dir, input_dir


# ==================== 核心预处理函数 ====================

def preprocess_c_file(input_path: str, output_path: str,
                      include_paths: list = None, defines: set = None):
    """用 pcpp 预处理单个 .c 文件"""
    if include_paths is None:
        include_paths = []
    if defines is None:
        defines = set()

    # 展开成绝对路径
    include_paths = [os.path.abspath(p) for p in include_paths]

    # 创建预处理器（用自定义的，解决编码混乱问题）
    pp = MyPreprocessor()

    # 添加头文件搜索路径
    for p in include_paths:
        pp.add_path(p)

    # 定义宏（不带值的宏自动定义成 =1，这样在 #if 表达式里才能正常计算）
    for macro in defines:
        if '=' in macro:
            # 配置里写的是 MACRO=value 格式，转成 pcpp 要的 MACRO value 格式
            name, value = macro.split('=', 1)
            pp.define(f'{name} {value}')
        else:
            # 不带值的宏，默认定义成 1
            pp.define(f'{macro} 1')

    # 解析输入文件（先读文件内容，parse() 接收的是代码文本）
    with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
        code = f.read()
    pp.parse(code, source=input_path)

    # 把预处理结果写到内存
    import io
    buf = io.StringIO()
    pp.write(buf)
    raw_output = buf.getvalue()

    # 保留所有展开后的代码（头文件内容也保留），这样：
    #   - typedef（SINT/Word16/UCHAR 等类型定义）可见
    #   - 宏展开生效（如 MAXMATIRC -> 32）
    #   - extern 函数声明、结构体定义可见
    # 只去掉 pcpp 生成的 #line 行号指令。
    # 注意：本项目头文件里只有 typedef/#define/extern 声明和结构体，
    # 没有 static inline 函数定义，所以展开后不会产生重复函数。
    filtered_lines = []
    for line in raw_output.splitlines(keepends=True):
        if line.startswith('#line'):
            continue
        filtered_lines.append(line)

    # 输出到文件
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(filtered_lines)


def preprocess_dir(input_dir: str, output_dir: str,
                   include_paths: list = None, defines: set = None,
                   skip_dirs=None):
    """递归预处理目录下所有 .c 文件，保持目录结构"""
    if skip_dirs is None:
        skip_dirs = {'build', 'Build', 'Debug', 'Release',
                     '.git', '.svn', 'Output', 'bin', 'obj',
                     '._preprocessed_tmp'}

    import shutil
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

    count = 0
    for dirpath, dirnames, filenames in os.walk(input_dir):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for fn in filenames:
            if fn.endswith('.c'):
                src = os.path.join(dirpath, fn)
                rel = os.path.relpath(src, input_dir)
                dst = os.path.join(output_dir, rel)
                preprocess_c_file(src, dst, include_paths, defines)
                count += 1

    return count


# ==================== 命令行参数解析 ====================

def parse_args():
    args = sys.argv[1:]
    input_path = None
    output_path = None
    include_paths_cmd = []
    defines_cmd = set()

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == '-o' or arg == '--output':
            if i + 1 < len(args):
                output_path = args[i + 1]
                i += 2
            else:
                print("Error: -o requires a path.")
                sys.exit(1)
        elif arg == '-I' or arg == '--include':
            if i + 1 < len(args):
                include_paths_cmd.append(args[i + 1])
                i += 2
            else:
                print("Error: -I requires a directory path.")
                sys.exit(1)
        elif arg.startswith('-I'):
            include_paths_cmd.append(arg[2:])
            i += 1
        elif arg.startswith('--define='):
            defines_cmd.add(arg.split('=', 1)[1])
            i += 1
        elif arg == '--define':
            if i + 1 < len(args):
                defines_cmd.add(args[i + 1])
                i += 2
            else:
                print("Error: --define requires a macro name.")
                sys.exit(1)
        else:
            input_path = arg
            i += 1

    if input_path is None:
        print(__doc__)
        sys.exit(1)

    return input_path, output_path, include_paths_cmd, defines_cmd


# ==================== 主流程 ====================

def main():
    input_path_cmd, output_path, include_paths_cmd, defines_cmd = parse_args()

    # 从配置文件读取
    config_path = os.path.join(os.getcwd(), CONFIG_FILE_NAME)
    defines_file, include_paths_file, output_file, input_file = load_config(config_path)

    # 合并：配置文件 + 命令行（命令行优先）
    defines = defines_file | defines_cmd
    include_paths = include_paths_file + include_paths_cmd

    # 输入路径：命令行 > 配置文件 > 默认当前目录
    if input_path_cmd is not None:
        input_path = input_path_cmd
    elif input_file is not None:
        input_path = input_file
    else:
        input_path = '.'

    # 输出路径：命令行 > 配置文件 > 默认值
    if output_path is None:
        output_path = output_file

    input_path = os.path.abspath(input_path)

    if not os.path.exists(input_path):
        print(f"Error: '{input_path}' not found.")
        sys.exit(1)

    print(f"Input:  {input_path}")
    if os.path.isfile(input_path):
        if output_path is None:
            base, ext = os.path.splitext(input_path)
            output_path = base + '.processed' + ext
        print(f"Output: {output_path}")
    else:
        if output_path is None:
            output_path = input_path + '.processed'
        print(f"Output dir: {output_path}")

    if include_paths:
        print(f"Include paths: {include_paths}")
    if defines:
        print(f"Defines ({len(defines)}): {', '.join(sorted(defines))}")
    if os.path.exists(config_path):
        print(f"Config file: {config_path}")

    print()

    if os.path.isfile(input_path):
        preprocess_c_file(input_path, output_path, include_paths, defines)
        print("Done.")
    elif os.path.isdir(input_path):
        count = preprocess_dir(input_path, output_path, include_paths, defines)
        print(f"Done. {count} files processed.")
    else:
        print(f"Error: '{input_path}' is neither file nor directory.")
        sys.exit(1)


if __name__ == '__main__':
    main()
