#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C Call Tree Analyzer
读取 c-preprocessor.py 生成的预处理产物，提取函数定义与调用关系，
以树形结构展示调用层次。

工作流程：
    1. 先运行 c-preprocessor.py，根据 call_tree_defines.txt 做宏裁剪，
       生成预处理产物目录（默认 ./_preprocessed）。
    2. 再运行本脚本，直接读取该目录下的 .c 文件进行调用分析。

Usage:
    python c_call_tree.py [preprocessed_dir] [--define MACRO1] ...
    （不传目录时，默认读取 call_tree_defines.txt 里的 output: 目录）

Examples:
    python c_call_tree.py
    python c_call_tree.py ./_preprocessed
    python c_call_tree.py ./_preprocessed --define CHIP_X

Configuration (call_tree_defines.txt):
    output: ./_preprocessed     # 预处理产物目录（c-preprocessor.py 生成）
    LINUX                        # 宏开关（仅作信息提示，实际裁剪由预处理器完成）

Output:
    tree.txt                 - 完整调用树（当前目录下）
"""

import os
import re
import sys
import shutil
from collections import defaultdict


# ==================== 输出工具：同时打印到控制台和写入 tree.txt ====================

_output_file = None   # 全局输出文件句柄，在 main() 里打开


def log(*args, **kwargs):
    """同时输出到 tree.txt 文件和控制台。
    先写文件确保数据完整；控制台打印用 try 包裹，
    避免 Windows GBK 控制台无法打印 Unicode 字符（如 ↩）时崩溃。
    """
    if _output_file is not None:
        print(*args, **kwargs, file=_output_file)
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        pass


# ==================== 配置项 ====================

# 标准库 / 常见外部函数（不画进调用树，避免树太乱）
EXCLUDE_FUNCS = {
    # stdio
    'printf', 'sprintf', 'snprintf', 'fprintf', 'sscanf', 'scanf',
    'puts', 'putchar', 'getchar', 'fopen', 'fclose', 'fread', 'fwrite',
    'fseek', 'ftell', 'fflush', 'feof', 'fgets', 'fputs',
    # stdlib
    'malloc', 'free', 'calloc', 'realloc', 'exit', 'abort', 'assert',
    'atoi', 'atol', 'atof', 'strtol', 'strtoul', 'rand', 'srand',
    'qsort', 'bsearch', 'abs', 'system',
    # string
    'memset', 'memcpy', 'memmove', 'memcmp', 'strlen', 'strcmp', 'strncmp',
    'strcpy', 'strncpy', 'strcat', 'strncat', 'strchr', 'strrchr', 'strstr',
    'strtok', 'strdup',
    # math
    'sin', 'cos', 'tan', 'asin', 'acos', 'atan', 'sqrt', 'pow', 'exp',
    'log', 'fabs', 'floor', 'ceil',
    # time
    'time', 'clock', 'difftime',
    # ctype
    'isalpha', 'isdigit', 'isalnum', 'isspace', 'isupper', 'islower',
    'toupper', 'tolower',
}

# 控制语句关键字（不是函数调用，要排除）
CONTROL_KEYWORDS = {
    'if', 'for', 'while', 'switch', 'return', 'sizeof', 'else', 'do',
    'case', 'goto', 'typeof', '__typeof__',
}

# 扫描时跳过的目录名（编译产物目录等）
SKIP_DIRS = {
    'build', 'Build', 'DEBUG', 'release', 'Release',
    '.git', '.svn', 'Debug', 'Output', 'output',
    'Listings', 'Objects', 'bin', 'obj',
    # 我们自己生成的临时目录
    '._preprocessed_tmp',
}


# ==================== 以下预处理逻辑已废弃（迁移到 c-preprocessor.py） ====================
# 历史上本脚本自己做去注释 + 条件编译裁剪，输出到 ._preprocessed_tmp。
# 现在这一步统一由 c-preprocessor.py（基于 pcpp）完成，功能更强更准确。
# 本脚本直接读取 c-preprocessor.py 生成的预处理产物目录（默认 ./_preprocessed）。
# 以下函数保留仅作参考，main() 不再调用。

# ---------- 旧实现：去注释和字符串 ----------

def remove_comments_and_strings(code: str) -> str:
    """去掉 C 代码中的注释和字符串字面量"""
    # 去掉块注释 /* ... */
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    # 去掉行注释 // ...
    code = re.sub(r'//[^\n]*', '', code)
    # 去掉字符串字面量 "..."
    code = re.sub(r'"(?:[^"\\\n]|\\.)*"', '""', code)
    # 去掉字符字面量 '...'
    code = re.sub(r"'(?:[^'\\\n]|\\.)*'", "''", code)
    return code


# ==================== 预处理第二步：条件编译裁剪 ====================

def preprocess_conditional(code: str, defines: set) -> str:
    """
    根据 defines 集合裁剪条件编译块。
    支持：#ifdef / #ifndef / #else / #endif / #if defined(MACRO) / #if !defined(MACRO)
          #if MACRO / #if !MACRO / #if 0 / #if 1
    同时：逐行收集本文件里的 #define 宏，后面的 #if 可以用到。
    不支持复杂表达式（如 #if X > 5），遇到默认保留代码块。
    """
    lines = code.split('\n')
    result = []
    stack = []   # 栈：每个元素是 bool，表示当前层条件是否为真
    local_defines = set(defines)   # 本文件生效的宏（复制一份，逐行新增）

    for line in lines:
        stripped = line.strip()

        # 遇到预处理指令
        if stripped.startswith('#'):
            directive = stripped[1:].strip()

            # #define MACRO 或 #define MACRO value
            if directive.startswith('define '):
                # 提取宏名
                rest = directive[7:].strip()
                # 宏名是第一个标识符
                m = re.match(r'([A-Za-z_][A-Za-z0-9_]*)', rest)
                if m:
                    macro = m.group(1)
                    # 简单判断值是否为 0：如果值里全是 0，就不算有效宏
                    value_part = rest[len(macro):].strip()
                    if value_part not in ('', '0', '(0)'):
                        local_defines.add(macro)
                    # 值为 0 的宏也加进去，但标记为假？
                    # 简化处理：只要 #define 了就算，#if XXX 时就认为是真
                    # 值为 0 的情况先不精确处理，用户可以手动排除
                continue

            # #undef MACRO
            elif directive.startswith('undef '):
                macro = directive[6:].strip()
                local_defines.discard(macro)
                continue

            # #ifdef MACRO
            elif directive.startswith('ifdef '):
                macro = directive[6:].strip()
                condition = macro in local_defines
                stack.append(condition)
                continue

            # #ifndef MACRO
            elif directive.startswith('ifndef '):
                macro = directive[7:].strip()
                condition = macro not in local_defines
                stack.append(condition)
                continue

            # #if ...
            elif directive.startswith('if '):
                expr = directive[3:].strip()

                # #if 0 / #if 1
                if expr == '0':
                    stack.append(False)
                    continue
                if expr == '1':
                    stack.append(True)
                    continue

                # #if !MACRO
                m = re.match(r'!\s*([A-Za-z_][A-Za-z0-9_]*)\s*$', expr)
                if m:
                    macro = m.group(1)
                    condition = macro not in local_defines
                    stack.append(condition)
                    continue

                # #if MACRO
                m = re.match(r'([A-Za-z_][A-Za-z0-9_]*)\s*$', expr)
                if m:
                    macro = m.group(1)
                    condition = macro in local_defines
                    stack.append(condition)
                    continue

                # #if defined(MACRO) / #if !defined(MACRO)
                m = re.match(r'!\s*defined\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)', expr)
                if m:
                    macro = m.group(1)
                    condition = macro not in local_defines
                    stack.append(condition)
                    continue
                m = re.match(r'defined\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)', expr)
                if m:
                    macro = m.group(1)
                    condition = macro in local_defines
                    stack.append(condition)
                    continue

                # 其他复杂表达式，默认保留
                stack.append(True)
                continue

            # #else
            elif directive == 'else':
                if stack:
                    stack[-1] = not stack[-1]
                continue

            # #elif：简化处理，等同于 #else
            elif directive.startswith('elif'):
                if stack:
                    stack[-1] = not stack[-1]
                continue

            # #endif
            elif directive == 'endif':
                if stack:
                    stack.pop()
                continue

            else:
                # 其他预处理指令（#include, #pragma 等），直接保留
                pass

        # 判断当前行是否应该保留：栈里所有层都为真
        all_true = all(stack) if stack else True
        if all_true:
            result.append(line)

    return '\n'.join(result)


# ==================== 预处理：对单个文件做完整处理 ====================

def preprocess_file(raw_code: str, defines: set) -> str:
    """完整预处理：去注释字符串 → 条件编译裁剪"""
    code = remove_comments_and_strings(raw_code)
    code = preprocess_conditional(code, defines)
    return code


# ==================== 扫描目录，收集所有 .c 文件 ====================

def scan_c_files(root_dir: str) -> list:
    """递归扫描目录，返回所有 .c 文件的绝对路径列表"""
    c_files = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if fn.endswith('.c'):
                c_files.append(os.path.join(dirpath, fn))
    return c_files


# ==================== 预处理所有文件，输出到临时目录 ====================

def preprocess_to_tempdir(c_files: list, src_root: str, temp_dir: str,
                          defines: set) -> list:
    """
    对所有 .c 文件做预处理，输出到临时目录（保持目录结构）。
    返回临时目录下的 .c 文件路径列表。
    """
    # 清空并重建临时目录
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)

    temp_files = []

    for src_path in c_files:
        # 计算相对路径，保持目录结构
        rel_path = os.path.relpath(src_path, src_root)
        dst_path = os.path.join(temp_dir, rel_path)
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)

        # 读取原始文件
        try:
            with open(src_path, 'r', encoding='utf-8', errors='ignore') as f:
                raw = f.read()
        except Exception as e:
            log(f"  [WARN] Cannot read {src_path}: {e}")
            continue

        # 预处理
        processed = preprocess_file(raw, defines)

        # 写到临时目录
        with open(dst_path, 'w', encoding='utf-8') as f:
            f.write(processed)

        temp_files.append(dst_path)

    return temp_files


# ==================== 提取函数定义 ====================

# 函数定义正则：
#   行首空白 + 可选修饰符(static/extern/inline/...) + 返回类型 + 至少一个空格 + 可选指针 + 函数名 + (参数) + {
FUNC_DEF_PATTERN = re.compile(
    r'^[ \t]*'
    r'(?:static\s+|extern\s+|inline\s+|const\s+|volatile\s+|'
    r'unsigned\s+|signed\s+|long\s+|short\s+|__attribute__[^\n]*\s+)*'
    r'([A-Za-z_][A-Za-z0-9_:]*)'           # 返回类型第一段
    r'(?:\s+[A-Za-z_][A-Za-z0-9_:]*)*'      # 返回类型后续段
    r'\s+'                                   # 返回类型和函数名之间必须有至少一个空格
    r'(\*+\s*)?'                             # 返回类型的指针符号
    r'([A-Za-z_][A-Za-z0-9_]*)\s*'         # 函数名（捕获组3）
    r'\([^;{]*?\)\s*\{\s*$',               # 参数列表 + {
    re.MULTILINE
)


def extract_functions(code: str, filename: str) -> dict:
    """从预处理后的代码中提取函数定义。"""
    functions = {}

    for match in FUNC_DEF_PATTERN.finditer(code):
        func_name = match.group(3)

        if func_name in CONTROL_KEYWORDS:
            continue

        # 从 { 开始，花括号配对找到函数体结束位置
        brace_start = match.end() - 1
        depth = 1
        pos = brace_start + 1
        while pos < len(code) and depth > 0:
            if code[pos] == '{':
                depth += 1
            elif code[pos] == '}':
                depth -= 1
            pos += 1

        body = code[brace_start + 1:pos - 1]
        functions[func_name] = {
            'file': os.path.basename(filename),
            'body': body,
        }

    return functions


# ==================== 提取函数调用 ====================

CALL_PATTERN = re.compile(r'\b([A-Za-z_][A-Za-z0-9_]*)\s*\(')


def extract_calls(body: str, known_funcs: set) -> list:
    """从函数体中提取它调用了哪些函数（只保留工程内已知的函数名）。
    返回按代码中首次出现顺序排列的列表（去重）。
    """
    calls = []
    seen = set()
    for match in CALL_PATTERN.finditer(body):
        name = match.group(1)
        if name in CONTROL_KEYWORDS:
            continue
        if name in EXCLUDE_FUNCS:
            continue
        if name in known_funcs and name not in seen:
            calls.append(name)
            seen.add(name)
    return calls


# ==================== 构建调用图 ====================

def build_call_graph(c_files: list) -> tuple:
    """两遍扫描：收集函数定义 → 分析调用关系"""
    all_funcs = {}
    func_bodies = {}

    # ---- 第一遍：收集函数定义 ----
    for filepath in c_files:
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                code = f.read()
        except Exception as e:
            log(f"  [WARN] Cannot read {filepath}: {e}")
            continue

        funcs = extract_functions(code, filepath)

        for fname, info in funcs.items():
            if fname in all_funcs:
                log(f"  [NOTE] Duplicate function '{fname}()' in {info['file']}, "
                    f"already seen in {all_funcs[fname]}, keeping first.")
            else:
                all_funcs[fname] = info['file']
                func_bodies[fname] = info['body']

    # ---- 第二遍：分析调用关系 ----
    known = set(all_funcs.keys())
    call_graph = defaultdict(list)

    for fname in all_funcs:
        body = func_bodies[fname]
        callees = extract_calls(body, known)
        # 去掉自调用
        if fname in callees:
            callees.remove(fname)
        call_graph[fname] = callees

    return all_funcs, call_graph


# ==================== 树形打印 ====================

def print_call_node(name: str, file_tag: str, prefix: str,
                    visited: set, call_graph: dict, all_funcs: dict,
                    is_last: bool, is_root: bool = False):
    """递归打印一个函数节点及其所有子调用。
    子节点行首加空格缩进，让 VS Code 的 indentation folding 能识别层级。
    """
    connector = '' if is_root else ('  └── ' if is_last else '  ├── ')
    loop_tag = '  (*) loop' if name in visited else ''
    log(f"{prefix}{connector}{name}()  [{file_tag}]{loop_tag}")

    if name in visited:
        return

    visited = visited | {name}

    callees = call_graph.get(name, [])
    if not callees:
        return

    extension = '' if is_root else ('      ' if is_last else '  │   ')
    child_prefix = prefix + extension

    for i, callee in enumerate(callees):
        last = (i == len(callees) - 1)
        child_file = all_funcs.get(callee, '?')
        print_call_node(callee, child_file, child_prefix,
                        visited, call_graph, all_funcs, last)


# ==================== HTML 折叠树生成 ====================

def build_html_node(name: str, file_tag: str, visited: set,
                    call_graph: dict, all_funcs: dict,
                    prefix: str = '', is_last: bool = True,
                    is_root: bool = False) -> str:
    """递归生成一个 <details> 折叠节点。
    prefix:  当前节点前面的竖线/空格前缀（和 txt 版本一致）。
    is_last: 是否是父节点的最后一个子节点（决定画 ├── 还是 └──）。
    is_root: 是否是根节点（根节点不画 branch 前缀）。
    """
    loop_tag = ' <span class="loop">(*)</span>' if name in visited else ''
    branch = '' if is_root else ('└── ' if is_last else '├── ')
    parts = [
        f'<details>',
        f'<summary><span class="prefix">{prefix}</span>'
        f'<span class="branch">{branch}</span>'
        f'<span class="fname">{name}()</span> '
        f'<span class="file">[{file_tag}]</span>{loop_tag}</summary>'
    ]

    if name not in visited:
        visited = visited | {name}
        callees = call_graph.get(name, [])
        if callees:
            # 子节点的前缀：如果当前节点后面还有兄弟，用 │ 延续竖线；
            # 如果当前节点是最后一个，用空格（后面没有兄弟了）。
            if is_root:
                child_prefix = ''
            else:
                child_prefix = prefix + ('│   ' if not is_last else '    ')
            parts.append('<div class="children">')
            for i, callee in enumerate(callees):
                child_file = all_funcs.get(callee, '?')
                child_last = (i == len(callees) - 1)
                parts.append(build_html_node(callee, child_file, visited,
                                             call_graph, all_funcs,
                                             child_prefix, child_last))
            parts.append('</div>')

    parts.append('</details>')
    return '\n'.join(parts)


HTML_HEAD = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>C Call Tree</title>
<style>
  body { font-family: "Cascadia Code", Consolas, "Courier New", monospace;
         background: #fafafa; color: #2c3e50; padding: 24px;
         font-size: 15px; line-height: 1.7; }
  h2 { color: #1a5fb4; border-bottom: 2px solid #d0d7de;
       padding-bottom: 8px; margin-top: 0; }
  h3 { color: #2e7d32; margin-top: 20px; margin-bottom: 4px;
       font-size: 15px; }
  .children { margin-left: 0; }
  details { margin: 1px 0; }
  summary { cursor: pointer; padding: 2px 8px; user-select: none;
            list-style: none; border-radius: 4px; }
  summary::-webkit-details-marker { display: none; }
  summary:hover { background: #e8f0fe; }
  summary::before { content: '▸'; color: #6a737d; display: inline-block;
                    width: 1em; transition: transform 0.1s; }
  details[open] > summary::before { content: '▾'; }
  .prefix { color: #9aa5b1; white-space: pre; }
  .branch { color: #9aa5b1; }
  .fname { color: #1a5fb4; font-weight: 600; }
  .file { color: #6a737d; font-size: 13px; }
  .loop { color: #c62828; font-weight: bold; }
  .stats { color: #57606a; margin: 12px 0; padding: 8px 12px;
           background: #eef1f4; border-radius: 6px; display: inline-block; }
</style>
</head>
<body>
<h2>C Call Tree Analysis</h2>
"""

HTML_TAIL = """</body>
</html>
"""


# ==================== 读取配置文件 ====================

CONFIG_FILE_NAME = 'call_tree_defines.txt'


def load_config(config_path: str) -> tuple:
    """
    从配置文件读取分析所需配置。
    返回: (defines_set, output_dir_str, input_dir_str)
        - defines_set: 宏名集合（仅作信息提示，实际裁剪由 c-preprocessor.py 完成）
        - output_dir:  预处理产物目录（即 c-preprocessor.py 的输出）
        - input_dir:   原始源码目录（分析器不直接使用，仅记录）

    配置格式与 c-preprocessor.py 保持一致：
        output: ./_preprocessed
        include: ./PDT/src
        LINUX
    """
    defines = set()
    output_dir = None
    input_dir = None

    if not os.path.exists(config_path):
        return defines, output_dir, input_dir

    with open(config_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            # 去掉行内注释（# 后面的内容）
            if '#' in line:
                line = line[:line.index('#')].strip()
            if not line:
                continue

            low = line.lower()
            if low.startswith('output:'):
                output_dir = line[7:].strip()
            elif low.startswith('input:'):
                input_dir = line[6:].strip()
            elif low.startswith('include:'):
                # include 路径只对预处理器有意义，分析器忽略
                continue
            else:
                defines.add(line)

    return defines, output_dir, input_dir


# ==================== 解析命令行参数 ====================

def parse_args():
    """
    解析命令行参数：
    - 第一个非 --define 参数当作要分析的预处理产物目录
    - --define XXX 收集宏定义（仅作信息提示）
    返回: (root_dir_or_None, defines_set)
    """
    args = sys.argv[1:]
    root_dir = None   # None 表示未指定，将回退到配置文件里的 output:
    defines = set()

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == '--define':
            if i + 1 < len(args):
                defines.add(args[i + 1])
                i += 2
            else:
                print("Error: --define requires a macro name.")
                sys.exit(1)
        elif arg.startswith('--define='):
            macro = arg.split('=', 1)[1]
            defines.add(macro)
            i += 1
        else:
            root_dir = arg
            i += 1

    return root_dir, defines


# ==================== 主流程 ====================

def main():
    global _output_file

    # 解析命令行参数
    root_cmd, defines_cmd = parse_args()

    # 从配置文件读取（放在当前工作目录下）
    config_path = os.path.join(os.getcwd(), CONFIG_FILE_NAME)
    defines_file, output_cfg, input_cfg = load_config(config_path)

    # 合并宏：配置文件 + 命令行（命令行优先）
    # 注意：宏不再用于条件编译裁剪，那一步由 c-preprocessor.py 完成。
    # 这里合并只是为了在日志里展示当前生效的是哪套配置。
    defines = defines_file | defines_cmd

    # 确定要分析的目录：
    #   命令行显式传了目录   → 用命令行的（覆盖配置）
    #   否则用配置文件里的 output:（c-preprocessor.py 的预处理产物）
    #   都没有              → 报错退出
    if root_cmd:
        root = os.path.abspath(root_cmd)
    elif output_cfg:
        root = os.path.abspath(output_cfg)
    else:
        print("Error: No preprocessed source directory specified.")
        print("  Option 1: pass a directory on the command line:")
        print("             python c-call-tree-analyzer.py ./_preprocessed")
        print("  Option 2: set 'output: <dir>' in call_tree_defines.txt")
        print("  Hint: run c-preprocessor.py first to generate preprocessed sources.")
        sys.exit(1)

    if not os.path.isdir(root):
        print(f"Error: '{root}' is not a valid directory.")
        print("  Hint: run c-preprocessor.py first to generate preprocessed sources.")
        sys.exit(1)

    # 打开输出文件 tree.txt
    output_path = os.path.join(os.getcwd(), 'tree.txt')
    _output_file = open(output_path, 'w', encoding='utf-8-sig')

    try:
        log(f"Reading preprocessed sources from: {root}")
        log("=" * 60)

        if defines:
            log(f"Configured defines ({len(defines)}): {', '.join(sorted(defines))}")
            log(f"  (these were applied by c-preprocessor.py when generating the above sources)")
            log()

        # 1. 扫描预处理产物目录里的所有 .c 文件
        c_files = scan_c_files(root)
        log(f"Found {len(c_files)} C file(s):")
        for f in c_files:
            rel = os.path.relpath(f, root)
            log(f"  - {rel}")
        log()

        if not c_files:
            log("No .c files found in this directory.")
            log("Hint: run c-preprocessor.py first to generate preprocessed sources.")
            return

        # 2. 直接在预处理产物上分析函数定义与调用关系
        #    （宏展开、条件编译裁剪、去注释都已由 c-preprocessor.py 完成）
        log("Analyzing function definitions and calls...")
        all_funcs, call_graph = build_call_graph(c_files)
        log(f"Total functions detected: {len(all_funcs)}")
        log()

        if not all_funcs:
            log("No functions detected.")
            return

        # 3. 找出顶层函数
        called_by_anyone = set()
        for callees in call_graph.values():
            called_by_anyone.update(callees)
        top_level = sorted(set(all_funcs.keys()) - called_by_anyone)

        # 4. 打印调用树（txt）
        if 'main' in all_funcs:
            log("=" * 60)
            log("Call Tree (root: main)")
            log("=" * 60)
            root_file = all_funcs['main']
            print_call_node('main', root_file, '', set(),
                            call_graph, all_funcs, is_last=True, is_root=True)
            total_calls = sum(len(v) for v in call_graph.values())
            log(f"\n{len(all_funcs)} functions, {total_calls} call relations")
        else:
            log("=" * 60)
            log(f"No 'main' function found. {len(top_level)} top-level entry points:")
            log("=" * 60)

            total_calls = sum(len(v) for v in call_graph.values())

            for idx, root_func in enumerate(top_level):
                root_file = all_funcs[root_func]
                log()
                log(f"--- Tree {idx+1}/{len(top_level)}: {root_func}() ---")
                print_call_node(root_func, root_file, '', set(),
                                call_graph, all_funcs, is_last=True, is_root=True)

            log(f"\n{len(all_funcs)} functions, {total_calls} call relations, "
                f"{len(top_level)} entry points")

        log()
        log(f"Note: Sources read from preprocessed directory: {root}")

        # 5. 生成 HTML 折叠树
        total_calls = sum(len(v) for v in call_graph.values())
        html_parts = [HTML_HEAD]
        html_parts.append(
            f'<p class="stats">{len(all_funcs)} functions, '
            f'{total_calls} call relations, '
            f'{len(top_level)} entry points</p>')

        if 'main' in all_funcs:
            html_parts.append(f'<h3>Root: main()</h3>')
            html_parts.append(build_html_node('main', all_funcs['main'],
                                              set(), call_graph, all_funcs,
                                              is_root=True))
        else:
            for idx, root_func in enumerate(top_level):
                html_parts.append(
                    f'<h3>Tree {idx+1}/{len(top_level)}: {root_func}()</h3>')
                html_parts.append(
                    build_html_node(root_func, all_funcs[root_func],
                                    set(), call_graph, all_funcs, is_root=True))

        html_parts.append(HTML_TAIL)
        html_path = os.path.join(os.getcwd(), 'tree.html')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(html_parts))
        log(f"HTML tree saved to: {html_path}")
    finally:
        _output_file.close()
        print(f"\n[Done] Output saved to: {output_path}")


if __name__ == '__main__':
    main()
