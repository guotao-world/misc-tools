# PCM转WAV

把裸 PCM 数据封装成标准 WAV 文件。

## 功能

- 输入：裸 PCM 文件（16-bit signed, little-endian, 单声道，无文件头）
- 输出：标准 RIFF/WAVE 文件（44 字节 WAV 头 + PCM 数据）
- 默认参数：8000 Hz / 16 bit / 单声道 / 小端

## 编译

```bash
make
```

或手动：

```bash
gcc -O2 -o pcm2wav pcm2wav.c
```

## 用法

```bash
pcm2wav <输入pcm> [输出wav] [采样率]
```

| 参数 | 默认值 | 说明 |
|---|---|---|
| 输入pcm | `input.pcm` | 裸 PCM 文件路径 |
| 输出wav | `output.wav` | 输出 WAV 文件路径 |
| 采样率 | `8000` | 采样率（Hz） |

## 示例

```bash
# 默认参数：8000 Hz
./pcm2wav voice.pcm

# 指定输出和采样率：16000 Hz
./pcm2wav voice.pcm voice.wav 16000
```

运行后会打印采样点数、输出路径和音频时长。

## 依赖

- C 编译器（GCC / MinGW 均可）
- 无第三方库
