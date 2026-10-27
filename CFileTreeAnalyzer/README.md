# C Call Tree Analyzer

一个轻量级的 C 代码调用树分析工具。自动预处理（展开头文件、裁剪条件编译），提取函数定义与调用关系，输出可折叠的树形结构。

## 功能特性

- **自动预处理**：基于 [pcpp](https://github.com/ned14/pcpp) 展开 `#include`、裁剪 `#ifdef` 条件编译、展开宏
- **调用树生成**：递归提取函数调用关系，按代码中的实际调用顺序排列
- **双格式输出**：
  - `tree.txt` — 纯文本树，VS Code 中可按缩进折叠
  - `tree.html` — 浏览器可折叠的交互式树，亮色主题
- **循环检测**：递归调用自动标记 `(*)` 避免无限展开
- **配置驱动**：所有输入/输出/宏开关统一在 `call_tree_defines.txt` 管理
- **编码兼容**：自动检测 GBK / UTF-8 / UTF-16 源码编码

## 文件说明

| 文件 | 作用 |
|---|---|
| `build_call_tree.py` | 一键入口：先预处理，再分析，输出 tree.txt + tree.html |
| `c-preprocessor.py` | 预处理器：展开头文件、裁剪条件编译，输出到 `_preprocessed/` |
| `c-call-tree-analyzer.py` | 调用树分析器：扫描预处理产物，提取函数定义与调用关系 |
| `call_tree_defines.txt` | 配置文件：输入目录、输出目录、头文件路径、宏开关 |
| `convert-to-utf8.py` | 工具脚本：批量将 GBK 源码转为 UTF-8 |

## 快速开始

### 1. 安装依赖

```bash
pip install pcpp
```

### 2. 配置

编辑 `call_tree_defines.txt`：

```ini
# 输入目录（要分析的 C 代码根目录）
input: ./src

# 预处理输出目录
output: ./_preprocessed

# 头文件搜索路径（可多行）
include: ./inc
include: ./src

# 宏开关（直接写宏名，不带值的宏自动定义为 1）
LINUX
# CHIP_RK3568
```

### 3. 运行

```bash
python build_call_tree.py
```

完成后在当前目录生成：
- `tree.txt` — 文本调用树
- `tree.html` — 可折叠的 HTML 调用树
- `_preprocessed/` — 预处理后的源码（可检查裁剪是否正确）

## 配置说明

`call_tree_defines.txt` 支持以下配置项：

| 配置项 | 格式 | 说明 |
|---|---|---|
| `input:` | `input: ./src` | 要分析的 C 代码根目录 |
| `output:` | `output: ./_preprocessed` | 预处理产物输出目录 |
| `include:` | `include: ./inc` | 头文件搜索路径，可写多行 |
| 宏名 | `LINUX` | 直接写宏名，预处理时自动定义为 `1` |

以 `#` 开头的行是注释，空行忽略。

## 输出示例

### tree.txt

```
NVOC_VoEncoder()  [userapi.c]
  ├── Init_Coder()  [Encoder.c]
  │     ├── IniAgcPara_Fix()  [AGC.c]
  │     └── IniAgcNoise_Fix()  [AGC.c]
  ├── init_NS()  [noise_lib.c]
  │     └── initialize()  [noise_core.c]
  ├── Encoder()  [Encoder.c]
  │     ├── AgcCalWave_Fix()  [AGC.c]
  │     ├── BPVCQuant()  [quant.c]
  │     └── GainQuant()  [gain.c]
  └── ...
```

- 子函数按**代码中的实际调用顺序**排列
- `(*)` 标记表示递归调用（循环），不会无限展开

### tree.html

浏览器打开后，每个函数节点前有展开箭头 `▸` / `▾`，点击即可折叠/展开子调用树。亮色主题，函数名蓝色高亮。

## 单独使用各脚本

也可以单独运行预处理或分析：

```bash
# 只做预处理
python c-preprocessor.py ./src

# 只分析（读 _preprocessed 目录）
python c-call-tree-analyzer.py ./_preprocessed
```

## VS Code 折叠 tree.txt

在 VS Code 设置中加入：

```json
"editor.foldingStrategy": "indentation"
```

即可在文本编辑器中按缩进层级折叠调用树。

## 依赖

- Python 3.8+
- [pcpp](https://github.com/ned14/pcpp) — C 预处理器

## License

MIT
