/*
 * pcm2wav.c —— 把裸 PCM 封装成标准 WAV 文件
 *
 * 输入: 裸 PCM 文件 (16-bit signed, little-endian, 单声道, 无文件头)
 * 输出: 标准 RIFF/WAVE 文件 (44 字节头 + PCM 数据)
 *       默认参数: 8000 Hz / 16 bit / 单声道 / 小端
 *
 * 用法:
 *     pcm2wav <输入pcm> [输出wav] [采样率]
 *     不指定输出时默认 output.wav; 不指定采样率时默认 8000
 *
 * 编译(Windows 下 MinGW / MSVC 均可):
 *     gcc -O2 -o pcm2wav.exe pcm2wav.c
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

/* 小端写入 16 位整数 */
static void put_u16le(unsigned char *p, uint16_t v)
{
    p[0] = (unsigned char)(v & 0xFF);
    p[1] = (unsigned char)((v >> 8) & 0xFF);
}

/* 小端写入 32 位整数 */
static void put_u32le(unsigned char *p, uint32_t v)
{
    p[0] = (unsigned char)(v & 0xFF);
    p[1] = (unsigned char)((v >> 8) & 0xFF);
    p[2] = (unsigned char)((v >> 16) & 0xFF);
    p[3] = (unsigned char)((v >> 24) & 0xFF);
}

int main(int argc, char *argv[])
{
    const char *in_path  = (argc >= 2) ? argv[1] : "input.pcm";
    const char *out_path = (argc >= 3) ? argv[2] : "output.wav";
    uint32_t sample_rate = (argc >= 4) ? (uint32_t)strtoul(argv[3], NULL, 10) : 8000;

    /* ---- 读入整个 PCM 文件 ---- */
    FILE *fin = fopen(in_path, "rb");
    if (!fin) {
        fprintf(stderr, "Error: cannot open input file %s\n", in_path);
        return 1;
    }
    if (fseek(fin, 0, SEEK_END) != 0) {
        fprintf(stderr, "Error: cannot seek in file %s\n", in_path);
        fclose(fin);
        return 1;
    }
    long fsize = ftell(fin);
    if (fsize < 0) {
        fprintf(stderr, "Error: cannot get file size\n");
        fclose(fin);
        return 1;
    }
    rewind(fin);

    /* 16bit 单声道: 每个采样 2 字节, 数据长度必须是偶数 */
    if (fsize % 2 != 0) {
        fprintf(stderr, "Warning: odd PCM size (%ld bytes), last byte will be dropped\n", fsize);
        fsize -= 1;
    }

    unsigned char *data = (unsigned char *)malloc((size_t)fsize);
    if (!data) {
        fprintf(stderr, "Error: out of memory\n");
        fclose(fin);
        return 1;
    }
    size_t got = fread(data, 1, (size_t)fsize, fin);
    fclose(fin);
    if (got != (size_t)fsize) {
        fprintf(stderr, "Error: short read\n");
        free(data);
        return 1;
    }

    /* ---- 组装 44 字节 WAV 头 ---- */
    unsigned char hdr[44];
    memset(hdr, 0, sizeof(hdr));

    /* RIFF 块 */
    memcpy(hdr + 0,  "RIFF", 4);
    put_u32le(hdr + 4, 36 + (uint32_t)fsize);   /* 文件总长 - 8 */
    memcpy(hdr + 8,  "WAVE", 4);
    /* fmt 子块 (PCM: 固定 16 字节) */
    memcpy(hdr + 12, "fmt ", 4);
    put_u32le(hdr + 16, 16);                    /* fmt 块大小 */
    put_u16le(hdr + 20, 1);                     /* AudioFormat = 1 (PCM) */
    put_u16le(hdr + 22, 1);                     /* NumChannels = 1 (单声道) */
    put_u32le(hdr + 24, sample_rate);           /* SampleRate */
    put_u32le(hdr + 28, sample_rate * 1 * 2);   /* ByteRate = 采样率*声道*字节 */
    put_u16le(hdr + 32, 1 * 2);                 /* BlockAlign = 声道*字节 */
    put_u16le(hdr + 34, 16);                    /* BitsPerSample */
    /* data 子块 */
    memcpy(hdr + 36, "data", 4);
    put_u32le(hdr + 40, (uint32_t)fsize);       /* PCM 数据字节数 */

    /* ---- 写出头 + 数据 ---- */
    FILE *fout = fopen(out_path, "wb");
    if (!fout) {
        fprintf(stderr, "Error: cannot create output file %s\n", out_path);
        free(data);
        return 1;
    }
    if (fwrite(hdr, 1, 44, fout) != 44 ||
        fwrite(data, 1, (size_t)fsize, fout) != (size_t)fsize) {
        fprintf(stderr, "Error: write failed\n");
        fclose(fout);
        free(data);
        return 1;
    }

    fclose(fout);
    free(data);

    long samples = fsize / 2;
    printf("Done: %ld samples -> %s (%lu Hz, 16-bit, mono, little-endian)\n",
           samples, out_path, (unsigned long)sample_rate);
    printf("Info: duration = %.3f s\n", (double)samples / sample_rate);
    return 0;
}
