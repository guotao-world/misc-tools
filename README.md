# misc-tools

> 个人开发小工具集合，涵盖代码分析、文件处理、效率脚本等，按需取用。

## 📑 目录

<!-- TOC START -->
- [CFileTreeAnalyzer](./CFileTreeAnalyzer)
  C Call Tree Analyzer
- [Excel操作](./Excel操作)
- [GBK转UTF-8](./GBK转UTF-8)
- [PCM转WAV](./PCM转WAV)
  PCM转WAV
<!-- TOC END -->

---

## 📝 说明

- 本仓库收集日常开发中写的小工具，每个子目录是一个独立工具
- 每个工具包含源码和独立的 README 说明文档
- 新增工具时，在根目录新建子目录即可，README 目录会在 push 后自动更新

## 📂 目录结构

- `CFileTreeAnalyzer/` — C 代码调用树分析工具（预处理 + 调用关系提取 + 可折叠树输出）
- `Excel操作/` — Excel 读写与处理脚本
- `GBK转UTF-8/` — 批量编码转换工具（GBK → UTF-8）
- `PCM转WAV/` — 裸 PCM 封装为标准 WAV 文件
