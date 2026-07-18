# 音视频转录整理 Agent（media-transcriber）

> 基于 Hermes Agent 框架的音视频/网页转录整理 Agent，支持 YouTube/B站/小宇宙/抖音/小红书等平台视频下载转录，网页文章正文抽取，本地音视频文件处理，最终交付飞书文档。
>
> 本 Agent 参考了"小D"的成熟设计，最大化复用其角色 Prompt、整理稿标准、质量检查清单和踩坑经验，并扩展了网页文章抽取和本地文件处理能力。

## 核心能力

- **多平台支持**：YouTube、B站、小宇宙播客、抖音、小红书视频
- **多素材类型**：视频链接、音频链接、网页文章、本地音视频文件
- **智能路径分流**：优先取字幕/官方稿 → 无字幕才走 ASR → 网页文章直接抽正文
- **分享式提纯稿**：不是摘要，保留原意、关键判断、案例、数字、类比、论证链
- **飞书文档交付**：自动创建飞书文档 + 授权本人为协作者
- **飞书 Bot 触发**：在飞书聊天框发链接即自动处理

## 目录结构

```
media-transcriber-agent/
├── README.md                          # 本文件
├── profile/                           # Hermes Profile 配置
│   ├── SOUL.md                        # Agent 人格定义
│   ├── config.yaml                    # 模型/工具/平台配置
│   └── .env.example                   # 环境变量模板（凭据）
├── prompts/                           # 角色 Prompt
│   └── system-prompt.md               # 核心系统提示词
├── skills/                            # 自定义 Skills
│   ├── web-content-extractor/         # 网页正文抽取
│   │   └── SKILL.md
│   └── local-file-transcriber/        # 本地文件转录
│       └── SKILL.md
├── scripts/                           # 核心流水线脚本
│   ├── download.py                    # 下载模块（yt-dlp 封装）
│   ├── transcribe.py                  # 转录模块（faster-whisper 封装）
│   ├── extract_web.py                 # 网页抽取模块（trafilatura 封装）
│   ├── refine.py                      # 提纯模块（LLM 调用）
│   └── pipeline.py                    # 主流水线（串联上述模块）
├── checklist/                         # 质量检查清单
│   └── quality-checklist.md           # 交付前 9 项检查
└── docs/                              # 文档
    ├── installation.md                # 安装部署指南
    ├── usage.md                       # 使用说明
    └── troubleshooting.md             # 常见坑与排查
```

## 快速开始

详见 [docs/installation.md](docs/installation.md) 和 [docs/usage.md](docs/usage.md)。

### 1. 安装依赖

```bash
pip install yt-dlp faster-whisper trafilatura lark-oapi openai
# ffmpeg: winget install ffmpeg 或 pip install imageio-ffmpeg
```

### 2. 配置 Hermes Agent

参考 [profile/config.yaml](profile/config.yaml) 和 [profile/.env.example](profile/.env.example)。

### 3. 创建 Profile 并启用

```bash
hermes profile create media-transcriber
hermes -p media-transcriber chat
```

## 分阶段实施

- **Phase 1（MVP）**：本地命令行跑通"链接 → 提纯稿 Markdown"
- **Phase 2**：接入飞书文档交付
- **Phase 3**：接入飞书 Bot 触发
- **Phase 4**：扩展网页/本地文件/抖音/小红书
- **Phase 5**：接入微信 Bot

## 致谢

本 Agent 的角色 Prompt、整理稿标准、质量检查清单和常见坑设计，参考了"小D"的成熟方案，并基于个人使用场景做了裁剪和扩展。
