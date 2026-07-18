---
name: local-file-transcriber
description: >
  本地音视频文件转录 Skill。用于处理用户发来的本地音频/视频文件，
  或已下载到本地的媒体文件，直接走转码 + ASR 转录流程。
  支持 mp4, mp3, wav, m4a, flac, aac, ogg 等常见格式。
  当用户发来本地文件路径或飞书/微信附件时调用此 Skill。
version: 1.0.0
author: media-transcriber
tags:
  - local
  - file
  - transcribe
  - audio
  - video
---

# local-file-transcriber Skill

## 触发条件

当用户发来的素材满足以下条件时调用：
- 本地文件路径（如 `D:\videos\meeting.mp4`）
- 飞书消息附件（需先用 lark-cli 下载到本地）
- 微信群文件（需先下载到本地）
- 文件格式为音视频：mp4, mp3, wav, m4a, flac, aac, ogg, webm, mkv, mov

## 职责

1. 接收本地文件路径
2. 验证文件存在、格式、大小、时长
3. 用 `ffmpeg` 转码为 16kHz 单声道 wav（ASR 标准输入）
4. 用 `faster-whisper` 转录为文字
5. 将原始转录稿传给 `refine` 模块做提纯整理

## 执行步骤

### Step 1: 文件验证
- 检查文件是否存在
- 检查文件格式是否支持
- 检查文件大小（过大文件需要分段处理）
- 用 ffprobe 获取时长（如可用）

```bash
python scripts/transcribe.py --input "<文件路径>" --check-only
```

### Step 2: 转码
将音视频文件转码为 ASR 标准输入格式：

```bash
python scripts/transcribe.py --input "<文件路径>" --transcode-only
```

转码参数（参考 config.yaml）：
- 采样率：16000 Hz
- 声道：1（单声道）
- 编码：pcm_s16le
- 输出：./tmp/wav/<文件名>.wav

### Step 3: ASR 转录
调用 faster-whisper 转录：

```bash
python scripts/transcribe.py --input "<文件路径>" --transcribe
```

参数（参考 config.yaml）：
- 模型：medium（Phase 1）/ large-v3（Phase 2）
- 设备：cpu（Phase 1）/ cuda（Phase 2）
- 量化：int8（CPU）/ float16（GPU）
- 语言：zh（强制中文）
- 束搜索：beam_size=5

### Step 4: 输出原始转录稿
- 格式：带时间戳的 SRT 或 JSON
- 输出路径：./tmp/transcripts/<文件名>.srt
- 将结果传给 `refine` 模块

## 依赖工具

- `ffmpeg`：音频转码（或 `imageio-ffmpeg` 作为替代）
- `faster-whisper`：语音转文字
- `ffprobe`（可选）：获取媒体元信息

## 文件格式支持

| 格式 | 扩展名 | 备注 |
|---|---|---|
| 视频 | .mp4, .mkv, .mov, .webm, .avi | 自动抽取音轨 |
| 音频 | .mp3, .wav, .m4a, .flac, .aac, .ogg | 直接转码 |

## 异常处理

| 场景 | 处理方式 |
|---|---|
| 文件不存在 | 回复"文件不存在，请检查路径：[路径]" |
| 格式不支持 | 回复"不支持的格式 [后缀]，支持：mp4/mp3/wav/m4a 等" |
| ffmpeg 未安装 | 自动降级到 `imageio-ffmpeg`；仍失败则回复"需要安装 ffmpeg" |
| 文件过大（>500MB） | 提示"文件较大，处理可能需要 X 分钟，后台运行中" |
| 音频时长过长（>2小时） | 提示"音频较长，建议分段处理或升级到 large-v3 模型" |
| ASR 转录失败 | 检查 wav 格式是否正确；尝试 small 模型降级 |
| 无音轨（纯视频） | 回复"该视频没有音轨，无法转录" |

## 与其他 Skill 的协作

```
用户发文件
  ├─ 飞书/微信附件 → 先下载到本地
  └─ 本地文件路径 → 直接处理
                      ↓
                    local-file-transcriber（本 Skill）
                      ├─ 转码（ffmpeg）
                      └─ ASR（faster-whisper）
                            ↓
                    refine 模块（LLM 提纯）
                            ↓
                    交付（本地 Markdown / 飞书文档）
```

## 飞书/微信文件下载

### 飞书文件
```bash
# 使用 lark-cli 下载飞书消息附件
lark-cli drive download --file-token "<token>" --output "./tmp/downloads/"
```

### 微信文件
微信群文件通过 Hermes Gateway 接收后，会自动保存到本地临时目录，
Agent 获取本地路径后直接处理。

## 示例

**输入**：
```
用户：D:\meetings\weekly_standup.mp4
```

**处理**：
1. 验证文件存在 + 格式支持（mp4 ✅）
2. 转码：ffmpeg -i weekly_standup.mp4 -ar 16000 -ac 1 -c:a pcm_s16le weekly_standup.wav
3. ASR：faster-whisper medium 模型转录
4. 输出原始稿 → 传给 refine 模块

**输出**：
```
正在处理文件：weekly_standup.mp4
- 格式：mp4（视频）
- 时长：32 分钟
- 转码中...
- 转录中（预计 25 分钟）...
- 原始转录稿已生成：./tmp/transcripts/weekly_standup.srt
- 正在提纯整理...
- 完成！提纯稿已保存：./output/weekly_standup.md
```
