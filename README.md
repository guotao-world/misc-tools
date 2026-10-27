# misc-tools

Personal collection of small development tools and scripts.

## Tools

### [CFileTreeAnalyzer](./CFileTreeAnalyzer)

C 代码调用树分析工具。自动预处理（展开头文件、裁剪条件编译），提取函数调用关系，输出可折叠的树形结构。

- 输入：C 源码目录
- 输出：`tree.txt`（文本树）+ `tree.html`（浏览器可折叠树）
- 依赖：Python 3.8+、[pcpp](https://github.com/ned14/pcpp)

详细用法见 [CFileTreeAnalyzer/README.md](./CFileTreeAnalyzer/README.md)。

## License

MIT
