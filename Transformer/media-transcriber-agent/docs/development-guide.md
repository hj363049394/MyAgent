# 音视频转录 Agent 完整开发文档

> **从需求讨论到云上部署的全流程指南**
> 面向小白读者：跟着本文档一步步操作，即可从零开发并部署一个能将音视频/网页内容自动转换为可读文稿的飞书 Bot。
>
> **项目仓库**：https://github.com/hj363049394/MyAgent/tree/main/Transformer/media-transcriber-agent
>
> **文档版本**：2026-07
>
> **已验证平台**：B 站、抖音、小红书、YouTube、微信公众号、本地音视频文件

---

## 目录

- [一、项目背景与需求](#一项目背景与需求)
  - [1.1 痛点与目标](#11-痛点与目标)
  - [1.2 核心功能需求](#12-核心功能需求)
  - [1.3 技术选型决策](#13-技术选型决策)
  - [1.4 分阶段开发计划](#14-分阶段开发计划)
- [二、整体架构设计](#二整体架构设计)
  - [2.1 系统架构图](#21-系统架构图)
  - [2.2 代码目录结构](#22-代码目录结构)
  - [2.3 数据流](#23-数据流)
  - [2.4 技术栈一览](#24-技术栈一览)
- [三、环境准备与依赖安装](#三环境准备与依赖安装)
  - [3.1 本地 Windows 开发环境](#31-本地-windows-开发环境)
  - [3.2 配置 GLM API Key](#32-配置-glm-api-key)
  - [3.3 验证依赖](#33-验证依赖)
- [四、飞书应用创建与配置（关键章节）](#四飞书应用创建与配置关键章节)
  - [4.1 为什么需要飞书应用](#41-为什么需要飞书应用)
  - [4.2 创建飞书自建应用](#42-创建飞书自建应用)
  - [4.3 添加机器人能力](#43-添加机器人能力)
  - [4.4 配置权限（详细）](#44-配置权限详细)
  - [4.5 配置事件订阅](#45-配置事件订阅)
  - [4.6 创建版本并发布](#46-创建版本并发布)
  - [4.7 获取 FEISHU_USER_ID（最容易出错的一步）](#47-获取-feishu_user_id最容易出错的一步)
  - [4.8 获取 FEISHU_FOLDER_TOKEN（云空间权限）](#48-获取-feishu_folder_token云空间权限)
  - [4.9 飞书配置常见问题](#49-飞书配置常见问题)
- [五、核心代码模块开发](#五核心代码模块开发)
  - [5.1 下载模块 download.py](#51-下载模块-downloadpy)
  - [5.2 转录模块 transcribe_funasr.py](#52-转录模块-transcribe_funasrpy)
  - [5.3 网页抽取模块 extract_web.py](#53-网页抽取模块-extract_webpy)
  - [5.4 提纯模块 refine.py](#54-提纯模块-refinepy)
  - [5.5 飞书文档交付 deliver_feishu.py](#55-飞书文档交付-deliver_feishupy)
  - [5.6 主流水线 pipeline.py](#56-主流水线-pipelinepy)
  - [5.7 飞书 Bot bot.py](#57-飞书-bot-botpy)
- [六、开发过程中遇到的问题与解决方案](#六开发过程中遇到的问题与解决方案)
- [七、本地启动与使用](#七本地启动与使用)
- [八、云服务器部署](#八云服务器部署)
- [九、后续优化方向](#九后续优化方向)
- [十、附录](#十附录)

---

## 一、项目背景与需求

### 1.1 痛点与目标

**痛点**：
- 每天接收大量音视频内容（B 站、抖音、小红书、YouTube、播客），没时间一个个看完
- 现有字幕/文稿质量参差不齐，机器字幕没有标点、分段，难以阅读
- 手动整理文稿耗时，且需要保留原文链接以便回溯

**目标**：
构建一个飞书 Bot，用户在飞书里发送音视频/网页链接，Bot 自动：
1. 下载音视频或抓取网页正文
2. 转录语音为文字（ASR）
3. 用 LLM 提纯为结构化、可读性强的文稿
4. 生成 AI 核心总结
5. 交付到飞书文档，并在文档开头标注原文链接

**最终效果**：

用户发送一个 B 站链接，2-4 分钟后收到飞书文档链接，打开后看到：
- 顶部引用块：原文链接
- 高亮块：💡 AI 总结（1-2 句概括 + 3-5 个要点）
- 正文：结构化提纯稿（带标题、段落、要点列表）

### 1.2 核心功能需求

| 需求 | 说明 | 优先级 |
|------|------|--------|
| 视频转录 | B 站、抖音、小红书、YouTube | P0 |
| 网页文章提取 | 微信公众号、博客 | P0 |
| 本地文件转录 | mp3/mp4/m4a | P1 |
| LLM 提纯 | 去除口语化、分段、加标点 | P0 |
| 飞书文档交付 | 自动创建文档并授权 | P0 |
| 飞书 Bot 触发 | 飞书内直接发链接 | P0 |
| AI 核心总结 | 文档顶部高亮块 | P1 |
| 原文链接引用 | 文档顶部标注来源 | P1 |
| 云服务器部署 | 7×24 稳定运行 | P1 |

### 1.3 技术选型决策

| 组件 | 选型 | 理由 |
|------|------|------|
| 下载工具 | yt-dlp | 支持多平台、社区活跃、支持 cookies |
| ASR 引擎 | FunASR SenseVoiceSmall | 国内可用、CPU int8 推理快、rtf≈0.1 |
| LLM | 智谱 GLM-4.7 + glm-4.5-air 兜底 | 国内访问稳定、中文效果好、价格便宜 |
| 网页抽取 | trafilatura | 专为正文抽取设计，效果好于 readability |
| 飞书 SDK | lark-oapi（WebSocket 长连接） | 无需公网 IP，本地直接跑 |
| Bot 框架 | 自建轻量 Bot（bot.py ~600 行） | 不依赖 Hermes Agent，避开 Linux 限制 |
| 部署方式 | Docker Compose | 与服务器已有应用共存、资源隔离 |

**关键技术决策说明**：

1. **为什么不用 Hermes Agent 框架？**
   - Hermes 要求 Linux 环境，与"先本地 Windows 测试"目标冲突
   - 功能上我们只需要消息收发 + 任务队列，自建轻量 Bot 更简单可控

2. **为什么 ASR 选 FunASR 而不是 faster-whisper？**
   - faster-whisper 的 medium 模型在 CPU 上 rtf≈0.3（9 分钟视频需 2.7 分钟）
   - FunASR SenseVoiceSmall 在 CPU int8 上 rtf≈0.05（9 分钟视频 30 秒）
   - FunASR 国内 modelscope 下载快，无需 HF 镜像

3. **为什么用飞书 WebSocket 长连接而不用 Webhook？**
   - WebSocket 模式无需公网 IP/域名，本地直接跑
   - Webhook 模式需要 HTTPS 域名，部署门槛高

### 1.4 分阶段开发计划

| Phase | 目标 | 状态 |
|-------|------|------|
| Phase 1 | MVP：命令行 + 本地文件 + ASR + 提纯 | ✅ 完成 |
| Phase 2 | 飞书文档交付（REST API） | ✅ 完成 |
| Phase 3 | 飞书 Bot 触发 + 多平台 + AI 总结 | ✅ 完成 |
| Phase 4 | 云服务器 Docker 部署 | ✅ 完成 |
| Phase 5 | 微信 Bot（已评估，暂不开发） | ⏸ 暂缓 |

---

## 二、整体架构设计

### 2.1 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│  用户在飞书发送链接                                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  飞书服务器 → WebSocket 长连接 → 本地/云上 Bot                   │
│                                                              │
│  bot.py（飞书 Bot）                                          │
│    ├─ 消息接收：lark-oapi WebSocket                          │
│    ├─ 任务队列：queue.Queue + 工作线程                         │
│    └─ 命令处理：/help /status /progress                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  pipeline.py（主流水线）                                       │
│                                                              │
│  根据输入类型分流：                                              │
│  ├─ URL → detect_platform                                    │
│  │   ├─ web → extract_web → refine                           │
│  │   └─ bilibili/douyin/... → download → ASR → refine        │
│  └─ 本地文件 → transcode → ASR → refine                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  飞书文档交付 deliver_feishu.py                                 │
│                                                              │
│  ├─ Markdown → 飞书 blocks 转换                               │
│  ├─ 插入原文链接引用块                                          │
│  ├─ 插入 AI 总结引用块（调用 generate_ai_summary）              │
│  ├─ 创建文档 + 写入 blocks                                     │
│  └─ 添加协作者（FEISHU_USER_ID）                               │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 代码目录结构

```
media-transcriber-agent/
├── scripts/                    # 核心代码
│   ├── bot.py                  # 飞书 Bot（消息收发、任务队列）
│   ├── pipeline.py             # 主流水线（串联各模块）
│   ├── download.py             # 下载模块（yt-dlp 封装）
│   ├── transcribe.py           # ASR 入口（转码 + 调用 ASR 引擎）
│   ├── transcribe_funasr.py    # FunASR 引擎实现
│   ├── extract_web.py          # 网页文章抽取（trafilatura）
│   ├── refine.py               # LLM 提纯 + AI 总结生成
│   └── deliver_feishu.py       # 飞书文档交付
├── prompts/
│   └── system-prompt.md        # LLM 提纯 prompt
├── config/
│   ├── bilibili_cookies.txt    # B 站 cookies（Netscape 格式）
│   ├── douyin_cookies.txt      # 抖音 cookies
│   ├── xiaohongshu_cookies.txt # 小红书 cookies
│   └── youtube_cookies.txt     # YouTube cookies
├── profile/
│   ├── .env.example            # 环境变量模板
│   ├── config.yaml             # 配置文件
│   └── SOUL.md                 # Agent 人设
├── docs/                       # 文档
│   ├── development-guide.md    # 本文档
│   ├── installation.md         # 详细安装指南
│   ├── startup.md              # 日常启动指南
│   ├── deploy.md               # 服务器部署指南
│   ├── usage.md                # 使用说明
│   └── troubleshooting.md      # 故障排查
├── tmp/                        # 运行时临时文件（下载缓存、日志）
│   ├── downloads/              # 下载的音视频
│   ├── bot.log                 # Bot 日志
│   ├── create_folder.py        # 一次性脚本：Bot 创建文件夹
│   └── grant_folder_permission.py  # 一次性脚本：给用户授权
├── output/                     # 提纯稿 Markdown 输出
├── Dockerfile                  # Docker 镜像构建
├── docker-compose.yml          # Docker Compose 编排
├── requirements.txt            # Python 依赖
├── .env                        # 环境变量（不入 git）
├── .gitignore
└── .dockerignore
```

### 2.3 数据流

以"B 站视频链接"为例：

```
1. 用户发送：https://www.bilibili.com/video/BVxxxxx
2. bot.py 接收消息 → 入队 → 工作线程取出
3. pipeline.py.process(url)
4.   ├─ download.py.download_media(url)
5.   │   ├─ yt-dlp 提取 info（标题、时长）
6.   │   ├─ 尝试下载字幕（B 站有 CC 字幕）
7.   │   └─ 下载音频（.m4a）
8.   ├─ [有字幕] 直接读字幕 → raw_text
9.   │  [无字幕] transcribe_funasr.py.transcribe_audio_funasr(audio_path)
10.  │           ├─ ffmpeg 转 wav
11.  │           └─ FunASR 推理 → raw_text
12.  ├─ refine.py.refine_text(raw_text, title, metadata)
13.  │   ├─ 分段（每段 ≤ 3000 字）
14.  │   ├─ ThreadPoolExecutor 并行提纯（max_workers=3）
15.  │   └─ 合并分段 → refined_text
16.  ├─ save_refined(refined_text) → output/标题.md
17.  └─ _deliver_to_feishu(title, markdown_path, source_url)
18.      ├─ 读 Markdown 内容
19.      ├─ 插入原文链接引用块
20.      ├─ generate_ai_summary(refined_text) → summary
21.      ├─ 插入 AI 总结引用块
22.      ├─ extract_first_heading → 飞书文档标题
23.      └─ deliver_feishu.deliver_to_feishu(...)
24.          ├─ 创建文档
25.          ├─ Markdown → blocks 转换
26.          ├─ 写入 blocks
27.          └─ 添加协作者
28. bot.py 收到 feishu_url → 回复用户
```

### 2.4 技术栈一览

| 层 | 技术 | 版本 |
|----|------|------|
| 语言 | Python | 3.11+ |
| 下载 | yt-dlp | latest |
| 转码 | ffmpeg / imageio-ffmpeg | 4.x |
| ASR | FunASR (SenseVoiceSmall) | 1.x |
| LLM | 智谱 GLM-4.7 / glm-4.5-air | - |
| 网页抽取 | trafilatura | 1.12+ |
| 飞书 SDK | lark-oapi | 1.x |
| HTTP | requests | 2.x |
| 容器 | Docker / Docker Compose | 20.10+ / v2 |

---

## 三、环境准备与依赖安装

### 3.1 本地 Windows 开发环境

**前置要求**：
- Windows 10/11
- Python 3.11+（从 https://python.org 下载，安装时勾选 "Add to PATH"）

**步骤**：

```powershell
# 1. 克隆代码
git clone https://github.com/hj363049394/MyAgent.git
cd MyAgent\Transformer\media-transcriber-agent

# 2. 创建虚拟环境
python -m venv venv

# 3. 激活虚拟环境
venv\Scripts\activate

# 4. 安装依赖
pip install -r requirements.txt

# 5. 安装飞书 SDK（不在 requirements.txt 中）
pip install lark-oapi
```

### 3.2 配置 GLM API Key

1. 访问 https://open.bigmodel.cn/ 注册并实名认证
2. 进入「API Keys」页面创建 Key
3. 复制 Key（格式：`xxxxxxxx.xxxxxxxx`）

在项目根目录创建 `.env`（参考 `profile/.env.example`）：

```bash
# GLM API（必填）
OPENAI_API_KEY=你的真实API Key
OPENAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4
```

> **注意**：用 `OPENAI_API_KEY` 和 `OPENAI_BASE_URL` 而不是 `GLM_API_KEY`，
> 这样切换 LLM 后端时只需改 `base_url` 和 `model`，更通用。

### 3.3 验证依赖

```powershell
# 验证 GLM 连通性
python -c "
from openai import OpenAI
import os
from dotenv import dotenv_values
config = dotenv_values('.env')
client = OpenAI(api_key=config['OPENAI_API_KEY'], base_url=config['OPENAI_BASE_URL'])
r = client.chat.completions.create(model='glm-4.7', messages=[{'role':'user','content':'回复 PONG'}])
print(r.choices[0].message.content)
"
# 预期输出: PONG
```

---

## 四、飞书应用创建与配置（关键章节）

> ⚠️ **这是最容易出错的一章**。很多读者卡在飞书配置上，请仔细阅读。
> 涉及 4 个关键 ID：App ID、App Secret、User ID（open_id）、Folder Token。

### 4.1 为什么需要飞书应用

我们的 Bot 需要：
1. **接收消息**：用户在飞书发链接，Bot 能收到
2. **发送消息**：处理完成后，Bot 能回复用户
3. **创建文档**：自动创建飞书文档并写入内容
4. **授权协作者**：把文档所有者加为协作者，否则用户打不开文档

这些都需要通过飞书开放平台的 API 实现，必须创建一个飞书应用。

### 4.2 创建飞书自建应用

1. **访问飞书开放平台**：https://open.feishu.cn/app

2. **登录飞书账号**（个人账号即可，无需企业版）

3. 点击 **"创建企业自建应用"**

4. 填写应用信息：
   - **应用名称**：音视频转录整理 Bot（自定义）
   - **应用描述**：将视频/音频/网页链接转为可读文稿
   - **应用图标**：上传任意图标（可选）

5. 创建完成 → 进入应用详情页

6. **记录关键凭证**：
   - 进入「凭证与基础信息」→ 「应用凭证」
   - 复制 **App ID**（格式：`cli_xxxxxxxxxxxxxxxx`）
   - 复制 **App Secret**（格式：32 位字符串）

   > 这两个值就是 `.env` 中的 `FEISHU_APP_ID` 和 `FEISHU_APP_SECRET`，**务必保密**。

### 4.3 添加机器人能力

1. 应用详情页 → **应用能力** → **添加应用能力**

2. 勾选 **"机器人"** → 保存

3. 配置机器人信息：
   - **机器人名称**：显示在飞书消息中（可与应用名不同）
   - **机器人描述**：可选
   - **机器人头像**：可选

> 没有机器人能力，用户在飞书里搜不到你的应用。

### 4.4 配置权限（详细）

应用详情页 → **权限管理** → 开通以下权限：

| 权限名称 | 权限标识 | 用途 |
|----------|---------|------|
| 获取与发送单聊、群组消息 | `im:message` | 消息读写基础权限 |
| 读取用户发给机器人的单聊消息 | `im:message.p2p_msg:readonly` | 私聊接收消息 |
| 读取群聊中用户@机器人的消息 | `im:message.group_at_msg:readonly` | 群聊@接收消息 |
| 以应用的身份发消息 | `im:message:send_as_bot` | Bot 发送回复消息 |
| 获取与更新文档信息 | `docx:document` | 创建/写入飞书文档 |
| 添加协作者 | `drive:drive:permission` | 文档授权 |
| 获取云空间信息 | `drive:drive` | 文件夹操作 |

**操作步骤**：
1. 在权限管理页面，搜索上述权限标识
2. 点击"开通"按钮
3. 全部开通后，页面顶部会提示"权限变更需重新发版"

### 4.5 配置事件订阅

应用详情页 → **事件订阅**

1. **选择接收方式**：选 **"使用长连接接收事件"**（重要！）

   > ⚠️ **不要选 Webhook 模式**，那需要公网 HTTPS 域名。
   > 长连接模式（WebSocket）本地直接跑，无需公网 IP。

2. **添加事件**：
   - 搜索并添加 **"接收消息 v2.0"**
   - 事件标识：`im.message.receive_v1`

3. 保存

### 4.6 创建版本并发布

应用详情页 → **版本管理与发布** → **创建版本**

- **应用版本号**：1.0.0
- **可用范围**：选"所有员工"或指定成员（至少包含自己）
- **提交审核**：自建应用通常立即通过

> ⚠️ **重要**：每次修改权限或事件订阅后，**必须重新创建版本并发布**，否则变更不生效。

### 4.7 获取 FEISHU_USER_ID（最容易出错的一步）

**用途**：文档创建后，把**你本人**加为协作者，否则你打不开 Bot 创建的文档。

**关键概念**：飞书里同一个人在不同应用下有不同的 `open_id`。你从飞书个人主页复制的 ID 可能是 `user_id`，而 Bot 看到你的 `open_id` 是另一串。

**正确获取方法**：

1. **启动 Bot**（参考第七章）
2. **在飞书里找到你的 Bot，给它发任意消息**（比如"hello"）
3. **查看日志**：在终端或 `tmp/bot.log` 中找到类似记录：
   ```
   收到消息 from ou_xxxxxxxxxxxxxxxx: hello
   ```
4. **`ou_xxxxxxxxxxxxxxxx` 就是你的 open_id**

填到 `.env`：

```bash
FEISHU_USER_ID=ou_xxxxxxxxxxxxxxxx
```

> ⚠️ **常见错误**：把 App ID（`cli_xxx`）填到 `FEISHU_USER_ID`。App ID 是应用标识，User ID 是用户标识，两者完全不同。

### 4.8 获取 FEISHU_FOLDER_TOKEN（云空间权限）

**用途**：指定文档创建到哪个文件夹。如果不配，文档会创建到 Bot 的根目录（也能用，但不好管理）。

**关键坑**：飞书云空间共享面板搜索的是**用户**，搜不到 Bot 应用，所以不能通过界面手动加 Bot 为协作者。

**推荐方法：用 Bot API 自己创建文件夹**

Bot 用自己的身份创建文件夹，自动拥有完整权限。在项目根目录执行：

```powershell
venv\Scripts\activate
python tmp\create_folder.py
```

脚本会：
1. 用 Bot 凭据获取 `tenant_access_token`
2. 调用飞书 API 获取 Bot 的根目录 token
3. 在根目录下创建名为 "Bot 转录文稿" 的子文件夹
4. 输出 `folder_token`

把输出的 token 填到 `.env`：

```bash
FEISHU_FOLDER_TOKEN=<脚本输出的 token>
```

**给用户授权访问该文件夹**：

```powershell
python tmp\grant_folder_permission.py
```

脚本会给 `FEISHU_USER_ID` 对应的用户授予该文件夹的 `full_access` 权限。

### 4.9 飞书配置常见问题

| 问题 | 根因 | 解决 |
|------|------|------|
| 启动后看不到 `connected to wss://` | App ID/Secret 错误 | 检查 `.env` 凭据 |
| Bot 搜不到 | 未发布或可用范围不含自己 | 版本管理→创建版本→发布 |
| 发消息无响应 | 未订阅 `im.message.receive_v1` | 事件订阅→添加事件 |
| 私聊无响应 | 缺 `im:message.p2p_msg` 权限 | 权限管理→开通→重新发版 |
| 群聊@无响应 | 缺 `im:message.group_at_msg` 权限 | 权限管理→开通→重新发版 |
| 文档创建失败 403 | Bot 没有目标文件夹权限 | 用 `create_folder.py` 自建文件夹 |
| 用户打不开文档 | 未授权用户为协作者 | 检查 `FEISHU_USER_ID` 是否正确 |
| 权限变更不生效 | 未重新发版 | 版本管理→创建新版本→发布 |
| 把 App ID 填到 USER_ID | 概念混淆 | USER_ID 必须是 `ou_` 开头 |

---

## 五、核心代码模块开发

### 5.1 下载模块 download.py

**职责**：用 yt-dlp 下载视频/音频，优先下载字幕。

**核心函数**：

```python
def download_media(
    url: str,
    output_dir: str = "./tmp/downloads",
    prefer_subtitle: bool = True,
    cookies_file: Optional[str] = None,
    cookies_from_browser: Optional[str] = None,
) -> Dict[str, Any]:
    """下载音视频 + 字幕"""
```

**关键实现点**：

1. **平台识别**：通过 URL 域名识别平台（bilibili/douyin/xiaohongshu/youtube/web）

2. **按平台自动选择 cookies**：
   ```python
   platform_cookies_map = {
       "bilibili": "bilibili_cookies.txt",
       "douyin": "douyin_cookies.txt",
       "xiaohongshu": "xiaohongshu_cookies.txt",
       "youtube": "youtube_cookies.txt",
   }
   ```
   优先用 `config/<platform>_cookies.txt`，没有则用全局 `cookies_file`。

3. **精确识别本次下载的文件**（关键 bug 修复）：
   - 下载前记录 `existing_files` 集合
   - 下载后用 `ydl.prepare_filename(info)` 获取预期文件名
   - 按标题前缀匹配，避免误用旧文件

4. **支持视频扩展名**：抖音只返回 `.mp4`，扩展名列表加入 `.mp4`、`.mkv`、`.mov`、`.avi`

### 5.2 转录模块 transcribe_funasr.py

**职责**：用 FunASR SenseVoiceSmall 模型将音频转为文字。

**核心函数**：

```python
def transcribe_audio_funasr(
    audio_path: str,
    model_name: str = "iic/SenseVoiceSmall",
    device: str = "cpu",
    compute_type: str = "int8",
) -> Dict[str, Any]:
    """ASR 转录"""
```

**关键实现点**：

1. **模型加载**：FunASR 从 modelscope 下载模型（~500 MB），缓存在 `~/.cache/modelscope`
2. **CPU int8 推理**：无 GPU 也能跑，rtf≈0.05（9 分钟视频 30 秒）
3. **ffmpeg 转码**：输入可能是 mp4，先用 ffmpeg 转 wav 再送入 ASR
4. **ffmpeg 路径**：优先用系统 ffmpeg，没有则用 `imageio_ffmpeg.get_ffmpeg_exe()`

### 5.3 网页抽取模块 extract_web.py

**职责**：从网页 URL 抽取正文内容（用于微信公众号、博客等）。

**核心函数**：

```python
def extract_content(url: str, output_path: str = None) -> Dict[str, Any]:
    """抽取网页正文"""
```

**实现**：用 trafilatura 库，支持正文、作者、发布时间提取。

### 5.4 提纯模块 refine.py

**职责**：用 LLM 将原始转录稿（口语化、无标点）提纯为结构化文稿。

**核心函数**：

```python
def refine_text(
    raw_text: str,
    title: Optional[str] = None,
    metadata: Optional[Dict] = None,
    api_key: Optional[str] = None,
    model: str = "glm-4.7",
    fallback_model: str = "glm-4.5-air",
) -> Dict[str, Any]:
    """LLM 提纯"""

def generate_ai_summary(
    refined_text: str,
    title: Optional[str] = None,
    api_key: Optional[str] = None,
    model: str = "glm-4.5-air",  # 总结用 air 模型，速度快
    fallback_model: str = "glm-4.5-flash",
) -> Dict[str, Any]:
    """生成 AI 核心总结"""
```

**关键实现点**：

1. **分段并行提纯**：长文本按 ≤3000 字分段，用 `ThreadPoolExecutor(max_workers=3)` 并行处理
   - max_workers=3 是为了避免 GLM API 429 限流（4 并发会触发）
   - 分段间用 `\n\n---\n\n` 分隔符合并，不再做 LLM 统一格式化

2. **模型降级**：主模型失败 → 降级模型 → 返回失败

3. **AI 总结单独生成**：
   - 基于提纯稿生成（不是原始转录稿）
   - 用 `glm-4.5-air` 而非 `glm-4.7`（速度快 5-10 倍）
   - 输出格式：1-2 句概括 + 3-5 个要点

### 5.5 飞书文档交付 deliver_feishu.py

**职责**：创建飞书文档，写入内容，授权协作者。

**核心函数**：

```python
def deliver_to_feishu(
    title: str,
    markdown_content: str,
    user_id: Optional[str] = None,
    folder_token: Optional[str] = None,
) -> Dict[str, Any]:
    """交付到飞书文档"""
```

**关键实现点**：

1. **Markdown → 飞书 blocks 转换**：`_markdown_to_blocks()` 将 Markdown 转为飞书 docx block 结构
   - 支持：heading、paragraph、quote、bullet list、ordered list、code block
   - 特殊处理：`<!--AI_SUMMARY_START-->` / `<!--AI_SUMMARY_END-->` 标记转为引用块

2. **创建文档**：调用 `create_document` API，返回 `document_id`

3. **写入 blocks**：分批写入（每批 ≤50 个 block），避免请求过大

4. **添加协作者**：调用 `add_permission` API，把 `FEISHU_USER_ID` 加为 `full_access`

### 5.6 主流水线 pipeline.py

**职责**：串联各模块，根据输入类型选择处理路径。

**核心类**：

```python
class MediaTranscriberPipeline:
    def process(self, input_source: str, title: Optional[str] = None) -> Dict[str, Any]:
        # 判断输入类型：URL / 本地文件
        # 调用对应处理方法
        # 成功后调用 _deliver_to_feishu
```

**关键实现点**：

1. **飞书文档标题用正文首个标题**：
   ```python
   feishu_title = self._extract_first_heading(markdown_content) or title
   ```
   从 Markdown 正文提取第一个 `#` 标题，提取不到则用视频原标题兜底。

2. **插入原文链接引用块**：
   ```python
   if source_url:
       markdown_content = f"> 原文链接：{source_url}\n\n" + markdown_content
   ```

3. **插入 AI 总结引用块**：
   ```python
   summary_result = generate_ai_summary(refined_text, ...)
   if summary_result["success"]:
       summary_block = f"<!--AI_SUMMARY_START-->\n{summary_result['summary']}\n<!--AI_SUMMARY_END-->\n\n"
       markdown_content = source_block + summary_block + original_body
   ```

### 5.7 飞书 Bot bot.py

**职责**：通过 WebSocket 长连接接收飞书消息，解析链接/命令，异步调用 pipeline 处理。

**核心组件**：

1. **WebSocket 连接**：用 `lark-oapi` 的 `ws.Client` 建立长连接
2. **任务队列**：`queue.Queue` + 工作线程，避免阻塞消息接收
3. **命令处理**：
   - `/help`：显示帮助
   - `/status`：查看队列状态
   - `/progress`：查看当前任务进度 + 最近 20 行日志
4. **消息回复**：处理完成后回复飞书文档链接

---

## 六、开发过程中遇到的问题与解决方案

> 这一章记录了实际开发中遇到的所有关键 bug 和解决方案，对小白复现非常有帮助。

### 问题 1：飞书文档创建 403 Forbidden

**现象**：配置 `FEISHU_FOLDER_TOKEN` 后，创建文档返回 403。

**根因**：飞书 API 校验 **Bot 应用本身**对该文件夹的权限，与 `FEISHU_USER_ID` 无关。Bot 没有目标文件夹的写入权限。

**解决方案**：用 Bot API 自己创建文件夹（`tmp/create_folder.py`），Bot 自动有完整权限。

### 问题 2：飞书云空间搜索不到 Bot

**现象**：在文件夹共享面板搜索"音视频转录"找不到 Bot。

**根因**：飞书共享面板搜索的是**用户**（通讯录中的人），不是应用。

**解决方案**：用 API 直接给用户授权（`tmp/grant_folder_permission.py`），不通过共享面板。

### 问题 3：抖音下载需要 cookies

**现象**：`ERROR: [Douyin] Fresh cookies (not necessarily logged in) are needed`

**根因**：抖音要求登录态 cookies。

**解决方案**：
1. 浏览器登录抖音
2. 用 "Get cookies.txt" 扩展导出 Netscape 格式 cookies
3. 保存到 `config/douyin_cookies.txt`
4. `download.py` 自动按平台选择 cookies 文件

### 问题 4：下载误匹配旧文件（严重 bug）

**现象**：抖音下载成功，但返回了之前 B 站的旧 `.m4a` 文件。

**根因**：`download.py` 遍历整个 `output_dir` 找文件，没有区分新旧文件。

**解决方案**：
1. 下载前记录 `existing_files` 集合
2. 下载后只在新文件中查找
3. 用 `ydl.prepare_filename(info)` 获取预期标题，按前缀匹配

### 问题 5：抖音下载的是 MP4 不被识别

**现象**：抖音下载的 `.mp4` 视频文件，代码只识别音频扩展名，报"未找到音频文件"。

**根因**：抖音的 `format: bestaudio/best` 会 fallback 到 `best`，返回 `.mp4`。

**解决方案**：扩展名列表加入视频格式：
```python
media_exts = [".m4a", ".mp3", ".wav", ".webm", ".opus", ".mp4", ".mkv", ".mov", ".avi"]
```

### 问题 6：ffmpeg 不可用

**现象**：ASR 转录时报 `ffmpeg 不可用`。

**根因**：用系统 Python 启动 Bot，系统 Python 没装 `imageio-ffmpeg`。

**解决方案**：**必须用 venv 的 Python 启动**：
```powershell
venv\Scripts\python.exe scripts\bot.py
```

### 问题 7：GLM API 429 限流

**现象**：LLM 提纯时报 429，部分分段降级到 `glm-4.5-air`。

**根因**：4 并发触发 GLM QPS 限制。

**解决方案**：
1. `max_workers` 从 4 降到 3
2. 连续任务间隔 ≥1 分钟
3. 已有降级机制兜底，不阻塞主流程

### 问题 8：飞书文档标题用了视频原标题

**现象**：用户反馈飞书文档标题应该是正文第一个标题，而不是视频原标题。

**解决方案**：`pipeline.py` 新增 `_extract_first_heading`，从 Markdown 提取首个 `#` 标题作为飞书文档标题。

### 问题 9：飞书 callout block 创建失败

**现象**：用 callout block (block_type=34) 写入飞书文档，返回 HTTP 400。

**根因**：飞书 callout block 是容器型 block，需要两步 API 调用（先建 callout，再往里加子 block），与一次写入模型不兼容。

**解决方案**：降级为 quote block (15) 模拟高亮块，加粗标题行 + 引用块视觉。

### 问题 10：飞书文档为空（只有标题没有内容）

**现象**：飞书文档创建成功，但内容为空。

**根因**：`callout.border_color` 只接受 `1-7`，传了 `11` 导致整个文档写入失败。

**解决方案**：`background_color` 和 `border_color` 都改为 `1`。

### 问题 11：视频二次发送失败

**现象**：同一视频第二次发送，报"下载完成但未找到音频文件"。

**根因**：yt-dlp 发现目标文件已存在会跳过下载，但 `download.py` 只在新文件中查找。

**解决方案**：增加兜底逻辑——按标题前缀在所有文件中查找（含旧文件）。

### 问题 12：Docker 构建时缺失 trafilatura

**现象**：容器启动报 `ModuleNotFoundError: No module named 'trafilatura'`。

**根因**：`requirements.txt` 不完整。

**解决方案**：补充 `trafilatura`、`beautifulsoup4`、`lxml`、`faster-whisper`、`transformers`、`tiktoken` 到 `requirements.txt`。

### 问题 13：Docker 构建慢

**现象**：Docker 构建耗时 30+ 分钟，卡在 apt 和 pip 下载。

**根因**：默认源在国外。

**解决方案**：Dockerfile 加国内镜像源：
- apt 源：`deb.debian.org` → `mirrors.aliyun.com`
- pip 源：默认 PyPI → `pypi.tuna.tsinghua.edu.cn`
- torch 源：清华 PyTorch 镜像

### 问题 14：GitHub clone 失败

**现象**：`git clone` 报 `Password authentication is not supported`。

**根因**：GitHub 从 2021 年起停止支持 HTTPS 密码认证。

**解决方案**：
- 仓库改为 public，用 `curl` 下载 ZIP
- 或用 Personal Access Token 替代密码

---

## 七、本地启动与使用

### 7.1 配置 .env

项目根目录创建 `.env`：

```bash
# GLM API（必填）
OPENAI_API_KEY=你的Key
OPENAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4

# 飞书应用凭据（必填）
FEISHU_APP_ID=cli_xxxxx
FEISHU_APP_SECRET=xxxxxx

# 你的飞书 open_id（必填，参考 4.7 节获取）
FEISHU_USER_ID=ou_xxxxx

# 飞书文档保存目录（可选，参考 4.8 节获取）
FEISHU_FOLDER_TOKEN=xxxxxx

# Bot 权限策略
FEISHU_ALLOW_ALL_USERS=true
FEISHU_DM_POLICY=open
FEISHU_GROUP_POLICY=open
```

### 7.2 启动 Bot

```powershell
cd d:\trae_projects\Agent\Transformer\media-transcriber-agent

# 必须用 venv 的 Python
venv\Scripts\python.exe scripts\bot.py
```

预期输出：

```
============================================================
音视频转录整理 Bot 启动
  App ID: cli_xxxxx
  User ID: ou_xxxxx
  Folder Token: xxxxxx
  允许所有用户: True
  群聊策略: open
  私聊策略: open
============================================================
正在连接飞书 WebSocket...
[INFO] Lark: connected to wss://msg-frontier.feishu.cn/ws/v2?...
```

### 7.3 在飞书中使用

1. 打开飞书 → 搜索你的 Bot 名称 → 私聊
2. 发送链接：
   - B 站：`https://www.bilibili.com/video/BVxxxxx`
   - 抖音：`https://www.douyin.com/video/xxxxx`
   - 小红书：`https://www.xiaohongshu.com/xxx`
   - 微信公众号：`https://mp.weixin.qq.com/s/xxxxx`
3. Bot 回复"⏳ 开始处理"
4. 2-4 分钟后收到"✅ 处理成功"+ 飞书文档链接

**支持命令**：
- `/help`：显示帮助
- `/status`：查看队列状态
- `/progress`：查看当前任务进度 + 最近 20 行日志

---

## 八、云服务器部署

> 详细步骤参考 [deploy.md](deploy.md)，这里给出关键流程。

### 8.1 服务器要求

- **规格**：4 核 CPU / 8 GB 内存（已验证可与寺庙应用共存）
- **系统**：Linux（Alibaba Cloud Linux 4 / Ubuntu / CentOS 均可）
- **网络**：出站访问飞书 API、GLM API、视频网站
- **磁盘**：剩余空间 ≥ 10 GB

### 8.2 部署步骤

```bash
# 1. 拉取代码
sudo mkdir -p /opt/transcriber-agent
cd /opt/transcriber-agent
git clone https://github.com/hj363049394/MyAgent.git tmp-repo
cp -r tmp-repo/Transformer/media-transcriber-agent/* .
cp tmp-repo/Transformer/media-transcriber-agent/.dockerignore .
rm -rf tmp-repo

# 2. 配置 .env
cat > .env <<'EOF'
FEISHU_APP_ID=cli_xxxxx
FEISHU_APP_SECRET=xxxxxx
FEISHU_USER_ID=ou_xxxxx
FEISHU_FOLDER_TOKEN=xxxxxx
OPENAI_API_KEY=xxxxxx
FEISHU_ALLOW_ALL_USERS=true
FEISHU_DM_POLICY=open
FEISHU_GROUP_POLICY=open
EOF
chmod 600 .env

# 3. 上传 cookies（在本地执行 scp）
scp -r config/*_cookies.txt root@<IP>:/opt/transcriber-agent/config/

# 4. 构建并启动
docker compose build
docker compose up -d
docker compose logs -f bot
```

### 8.3 资源隔离

`docker-compose.yml` 配置了资源限制，避免与服务器上其他应用冲突：

```yaml
deploy:
  resources:
    limits:
      cppus: '2.5'    # 最多用 2.5 核
      memory: 4G       # 最多用 4G 内存
```

### 8.4 日常运维

```bash
# 查看日志
docker compose logs -f bot

# 重启
docker compose restart bot

# 更新代码
git pull
docker compose up -d --build

# 资源监控
docker stats transcriber-bot
```

---

## 九、后续优化方向

### 9.1 已评估但暂不实施

| 方向 | 评估结论 |
|------|----------|
| 微信 Bot | 个人订阅号无法异步推送（5 秒超时限制）；个人微信第三方协议封号风险高；暂不开发 |
| 并行化提纯 + 总结 | 可能影响总结质量，暂不实施 |
| GPU 加速 ASR | CPU int8 已足够快（9 分钟视频 30 秒），无需 GPU |

### 9.2 未来可探索

| 方向 | 说明 |
|------|------|
| 飞书 callout block 真实支持 | 需两步 API 调用（先建 callout 容器，再往里加子 block） |
| 更多平台 | 小宇宙播客、YouTube 字幕优先 |
| 批量处理 | 一次发送多个链接，并行处理 |
| 用户偏好 | 每个用户独立的提纯风格偏好 |

---

## 十、附录

### 10.1 完整 .env 配置示例

```bash
# ============ LLM API ============
OPENAI_API_KEY=xxxxxxxx.xxxxxxxx
OPENAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4

# ============ 飞书应用 ============
FEISHU_APP_ID=cli_xxxxxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# ============ 飞书用户 ============
# 获取方法：启动 Bot 后给它发消息，查看日志中 sender=ou_xxx
FEISHU_USER_ID=ou_xxxxxxxxxxxxxxxx

# ============ 飞书文档目录 ============
# 获取方法：python tmp/create_folder.py
FEISHU_FOLDER_TOKEN=xxxxxxxxxxxxxxxx

# ============ Bot 权限策略 ============
FEISHU_ALLOW_ALL_USERS=true
FEISHU_DM_POLICY=open
FEISHU_GROUP_POLICY=open

# ============ 管理员白名单（可选） ============
# FEISHU_ADMIN_IDS=ou_user1,ou_user2
```

### 10.2 常用命令速查

```powershell
# 本地启动
cd d:\trae_projects\Agent\Transformer\media-transcriber-agent
venv\Scripts\python.exe scripts\bot.py

# 命令行测试（不开 Bot）
venv\Scripts\python.exe scripts\pipeline.py --input "URL" --deliver-to-feishu
```

```bash
# 服务器部署
cd /opt/transcriber-agent
docker compose build
docker compose up -d
docker compose logs -f bot

# 服务器运维
docker compose ps
docker compose restart bot
docker stats transcriber-bot
```

### 10.3 相关文档

- [installation.md](installation.md)：详细安装指南
- [startup.md](startup.md)：日常启动指南
- [usage.md](usage.md)：使用说明
- [deploy.md](deploy.md)：服务器部署指南
- [troubleshooting.md](troubleshooting.md)：故障排查

### 10.4 项目仓库

- GitHub：https://github.com/hj363049394/MyAgent/tree/main/Transformer/media-transcriber-agent

### 10.5 关键依赖版本

```
yt-dlp>=2024.1.0
funasr>=1.0.0
torch>=2.0.0
torchaudio>=2.0.0
openai>=1.0.0
trafilatura>=1.12.0
lark-oapi>=1.0.0
requests>=2.28.0
imageio-ffmpeg>=0.4.9
```

---

**文档结束**

如有问题，请先查阅 [troubleshooting.md](troubleshooting.md)，或提交 GitHub Issue。
