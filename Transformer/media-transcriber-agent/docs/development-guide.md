# 音视频转录 Agent 完整开发文档

> **从零开始，构建一个能自动把视频/网页转成文稿的飞书机器人**
>
> 这是一个"小白也能看懂"的开发指南。不需要专业知识，跟着步骤一步步操作就行。
>
> **项目仓库**：https://github.com/hj363049394/MyAgent/tree/main/Transformer/media-transcriber-agent
>
> **文档版本**：2026-07
>
> **已验证平台**：B 站、抖音、小红书、YouTube、微信公众号、本地音视频文件

---

## 目录

- [零、前置知识：你需要了解的几个概念](#零前置知识你需要了解的几个概念)
- [一、这个项目是什么](#一这个项目是什么)
  - [1.1 它能做什么](#11-它能做什么)
  - [1.2 我们为什么选择这些技术](#12-我们为什么选择这些技术)
  - [1.3 开发分几步走](#13-开发分几步走)
- [二、整体架构：各个部分怎么配合](#二整体架构各个部分怎么配合)
  - [2.1 一张图看懂整体流程](#21-一张图看懂整体流程)
  - [2.2 项目文件是干什么的](#22-项目文件是干什么的)
  - [2.3 一个链接的完整旅程](#23-一个链接的完整旅程)
- [三、准备工作：安装软件和工具](#三准备工作安装软件和工具)
  - [3.1 在电脑上安装 Python](#31-在电脑上安装-python)
  - [3.2 下载项目代码](#32-下载项目代码)
  - [3.3 申请智谱 AI 的 API Key](#33-申请智谱-ai-的-api-key)
- [四、飞书应用配置（最关键的步骤）](#四飞书应用配置最关键的步骤)
  - [4.1 为什么要创建飞书应用](#41-为什么要创建飞书应用)
  - [4.2 创建飞书应用](#42-创建飞书应用)
  - [4.3 添加机器人功能](#43-添加机器人功能)
  - [4.4 开通权限](#44-开通权限)
  - [4.5 设置消息接收方式](#45-设置消息接收方式)
  - [4.6 发布上线](#46-发布上线)
  - [4.7 获取你的用户 ID（最容易出错的一步）](#47-获取你的用户-id最容易出错的一步)
  - [4.8 设置文档保存目录（推荐）](#48-设置文档保存目录推荐)
  - [4.9 飞书配置常见问题速查](#49-飞书配置常见问题速查)
- [五、写代码：各个模块做了什么](#五写代码各个模块做了什么)
  - [5.1 下载视频 download.py](#51-下载视频-downloadpy)
  - [5.2 语音转文字 transcribe_funasr.py](#52-语音转文字-transcribe_funasrpy)
  - [5.3 提取网页正文 extract_web.py](#53-提取网页正文-extract_webpy)
  - [5.4 AI 润色稿件 refine.py](#54-ai-润色稿件-refinepy)
  - [5.5 发布到飞书文档 deliver_feishu.py](#55-发布到飞书文档-deliver_feishupy)
  - [5.6 总指挥 pipeline.py](#56-总指挥-pipelinepy)
  - [5.7 飞书机器人 bot.py](#57-飞书机器人-botpy)
- [六、踩坑记录：14 个实际问题及解决方法](#六踩坑记录14-个实际问题及解决方法)
- [七、本地运行：在你自己电脑上启动](#七本地运行在你自己电脑上启动)
- [八、搬到云服务器上运行](#八搬到云服务器上运行)
  - [8.1 为什么上云](#81-为什么上云)
  - [8.2 服务器够不够用](#82-服务器够不够用)
  - [8.3 上云后能快多少](#83-上云后能快多少)
  - [8.4 部署步骤](#84-部署步骤)
  - [8.5 本地和云上不能同时跑](#85-本地和云上不能同时跑)
  - [8.6 怎么确认是云上在处理](#86-怎么确认是云上在处理)
  - [8.7 日常维护](#87-日常维护)
- [九、未来可以做什么](#九未来可以做什么)
- [十、附录](#十附录)

---

## 零、前置知识：你需要了解的几个概念

在开始之前，先花 5 分钟了解一下项目中会提到的几个关键词。**不需要完全理解，有个印象就行**。

### Python 是什么？

Python 是一门编程语言，你可以把它理解为"给电脑下指令的语言"。这个项目的所有代码都是用 Python 写的。

你需要做的：在电脑上安装 Python（第三章会教你怎么装）。

### 虚拟环境（venv）是什么？

虚拟环境是 Python 的一个功能，它能给每个项目创造一个"独立的小房间"，房间里安装的软件不会跟其他项目搞混。

**打个比方**：就像你有一个工具箱，项目 A 需要锤子，项目 B 需要扳手。如果所有工具都混在一起，你也不知道哪个是哪个。虚拟环境就是给每个项目一个专属工具箱。

你需要做的：创建虚拟环境 → 激活虚拟环境 → 在虚拟环境里安装依赖。第三章会手把手教你。

### API Key 是什么？

API Key 就像一把"钥匙"。你要用别人的服务（比如智谱 AI），就需要用这把钥匙证明"我有权限使用"。

**打个比方**：就像你住酒店，前台给你一张房卡。你每次进房间都要刷卡。API Key 就是这张房卡。

你需要做的：去智谱 AI 官网注册，拿到一把钥匙（免费），然后填到配置文件里。

### LLM（大语言模型）是什么？

LLM 就是像 ChatGPT 这样的 AI 程序。给它一段文字，它能帮你润色、总结、翻译。

本项目用了智谱 AI 的模型（GLM-4.7），因为它是国产的，国内访问快，价格便宜。

你需要做的：只负责申请 Key，调用 AI 的代码已经写好了。

### ASR（语音识别）是什么？

ASR 就是把语音转成文字。比如你把一段录音丢进去，它输出："今天天气真好，我们出去玩吧"。

本项目用了阿里巴巴的 FunASR 模型，因为它在普通电脑上跑得很快，10 分钟的视频 30 秒就能转完。

你需要做的：不用管，代码会自动处理。

### Docker 是什么？

Docker 是一个"打包工具"。它能把你的程序和所有依赖打包成一个"集装箱"，放到任何服务器上都能直接运行，不用担心环境不一致。

**打个比方**：就像搬家时用纸箱打包，不管搬到哪个房子，箱子里的东西都不会乱。

你需要做的：如果只在本地电脑跑，不需要 Docker。如果要部署到云服务器，需要用 Docker（第八章会教）。

### WebSocket 是什么？

WebSocket 是一种通信方式。普通的网页请求是"你问一句，服务器答一句"。WebSocket 是"建立一条电话线，双方可以随时说话"。

飞书 Bot 用 WebSocket 跟飞书服务器保持连接，这样用户发消息，Bot 能立刻收到。

你需要做的：不用管，代码已经写好了。

### 飞书应用是什么？

飞书应用就是在飞书开放平台上创建的一个"程序身份"。有了这个身份，你的程序才能：
- 接收用户在飞书里发的消息
- 给用户回复消息
- 创建飞书文档

你需要做的：在飞书开放平台手动创建应用，配置权限（第四章会手把手教）。

---

## 一、这个项目是什么

### 1.1 它能做什么

**遇到的问题是**：
- 每天收到很多视频链接，没时间看
- 机器字幕没有标点、分段，很难读
- 看完想保存，但记不住原文在哪

**这个项目做的事情**：

你在飞书里发一个视频链接 → 机器人自动下载视频 → 把语音转成文字 → 用 AI 润色成可读的文稿 → 生成一个 AI 总结 → 发布到飞书文档，并在文档顶部标注原文链接。

**最终效果**（用户视角）：

```
你在飞书里发：https://www.bilibili.com/video/BVxxxxx

机器人回复：⏳ 开始处理

2-4 分钟后机器人回复：✅ 处理完成
飞书文档：https://feishu.cn/docx/xxxxx

打开飞书文档，看到：
┌─────────────────────────────────┐
│ > 原文链接：https://www.bilibili.com/... │
├─────────────────────────────────┤
│ 💡 AI 总结                       │
│ 本文讨论了 XXX，核心观点是 YYY。  │
│ - 要点1：...                     │
│ - 要点2：...                     │
│ - 要点3：...                     │
├─────────────────────────────────┤
│ # 视频正文的第一个标题            │
│ 结构化、可读性很强的文稿...       │
└─────────────────────────────────┘
```

**支持的内容类型**：
- B 站视频链接
- 抖音视频链接
- 小红书链接
- YouTube 视频链接
- 微信公众号文章链接
- 本地电脑上的音视频文件（mp3、mp4 等）

### 1.2 我们为什么选择这些技术

| 要做什么 | 用什么工具 | 为什么选它 |
|---------|-----------|-----------|
| 下载视频 | yt-dlp | 支持几乎所有视频网站，免费 |
| 语音转文字 | FunASR（阿里达摩院） | 在国内下载快，普通电脑也跑得快 |
| AI 润色 | 智谱 GLM-4.7 | 国内访问稳定，中文效果好，价格便宜 |
| 提取网页正文 | trafilatura | 专门从网页里提取正文，效果好 |
| 连接飞书 | lark-oapi | 飞书官方工具，本地就能跑，不需要服务器 |
| 机器人框架 | 自己写（~600 行代码） | 简单、可控、不需要学复杂的框架 |
| 部署到服务器 | Docker | 打包成集装箱，搬到任何服务器都能跑 |

**几个关键决策的解释**：

1. **为什么不用 Hermes Agent 框架？**
   - Hermes 是一个成熟的 AI 机器人框架，但它要求 Linux 系统
   - 我们想先在 Windows 电脑上测试，所以自己写了一个简单的机器人

2. **为什么语音识别用 FunASR 而不是 faster-whisper？**
   - faster-whisper 在普通电脑上跑得慢：10 分钟的视频要 2-3 分钟才能转完
   - FunASR 快得多：10 分钟的视频 30 秒就能转完
   - FunASR 的模型在国内下载也更快

3. **为什么用飞书 WebSocket 而不是 Webhook？**
   - WebSocket 模式就像打电话，建立连接后就能一直保持
   - Webhook 模式需要你有公网域名和 HTTPS 证书，门槛高
   - 用 WebSocket，你的本地电脑直接就能跑，不需要额外配置

### 1.3 开发分几步走

| 阶段 | 目标 | 说明 |
|------|------|------|
| 第一步 | 命令行能跑通 | 在命令行里输入链接，能下载视频、转文字、润色 |
| 第二步 | 能发布到飞书文档 | 结果自动生成飞书文档，并给你授权 |
| 第三步 | 飞书机器人触发 | 在飞书里发链接就能触发，不用开命令行 |
| 第四步 | 部署到云服务器 | 24 小时在线，不用自己电脑一直开着 |
| 第五步 | 微信机器人 | 评估后决定暂不做（风险太高） |

---

## 二、整体架构：各个部分怎么配合

### 2.1 一张图看懂整体流程

```
你在飞书里发链接
        │
        ▼
┌──────────────────────────┐
│  飞书机器人（bot.py）      │
│  收到链接，放进任务队列    │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  主流程（pipeline.py）     │
│  判断是什么类型的链接      │
│                          │
│  ├─ 视频链接 → 下载视频   │
│  ├─ 网页文章 → 提取正文   │
│  └─ 本地文件 → 直接处理   │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  语音转文字（ASR）        │
│  把视频里的语音转成文字    │
│  （如果有字幕，直接读字幕） │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  AI 润色 + AI 总结       │
│  把粗糙的文字润色成可读的  │
│  文稿，并生成核心要点总结  │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  发布到飞书文档           │
│  创建文档 → 写内容 → 授权  │
│  顶部加原文链接 + AI 总结  │
└──────────┬───────────────┘
           │
           ▼
机器人回复你：飞书文档链接
```

### 2.2 项目文件是干什么的

```
media-transcriber-agent/           ← 项目根目录
│
├── scripts/                       ← 所有代码都在这里
│   ├── bot.py                     ← 飞书机器人，负责收发消息
│   ├── pipeline.py                ← 总指挥，串联所有步骤
│   ├── download.py                ← 下载视频
│   ├── transcribe.py              ← 语音转文字的入口
│   ├── transcribe_funasr.py       ← 语音转文字的具体实现
│   ├── extract_web.py             ← 提取网页正文
│   ├── refine.py                  ← AI 润色 + AI 总结
│   └── deliver_feishu.py          ← 发布到飞书文档
│
├── prompts/                       ← AI 的提示词
│   └── system-prompt.md           ← 告诉 AI 怎么润色文稿
│
├── config/                        ← 配置文件（不提交到 git）
│   ├── bilibili_cookies.txt       ← B 站的登录凭证
│   ├── douyin_cookies.txt         ← 抖音的登录凭证
│   ├── xiaohongshu_cookies.txt    ← 小红书的登录凭证
│   └── youtube_cookies.txt        ← YouTube 的登录凭证
│
├── docs/                          ← 文档
│   ├── development-guide.md       ← 就是本文档
│   ├── installation.md            ← 安装指南
│   ├── startup.md                 ← 启动指南
│   ├── deploy.md                  ← 服务器部署指南
│   ├── usage.md                   ← 使用说明
│   └── troubleshooting.md         ← 故障排查
│
├── tmp/                           ← 临时文件（下载的视频、日志）
├── output/                        ← 生成的 Markdown 文稿
├── Dockerfile                     ← Docker 打包配置
├── docker-compose.yml             ← Docker 运行配置
├── requirements.txt               ← Python 依赖清单
├── .env                           ← 你的密钥配置（不提交到 git）
└── .gitignore                     ← 告诉 git 哪些文件不要提交
```

### 2.3 一个链接的完整旅程

以 B 站视频链接为例，看一个链接是怎么从你手里变成飞书文档的：

```
1. 你在飞书里发：https://www.bilibili.com/video/BVxxxxx

2. bot.py 收到这条消息，放进任务队列
   （相当于餐厅里服务员记下你的点菜单）

3. pipeline.py 从队列里取出任务，开始工作：
   "这是一个 B 站链接，走视频处理流程"

4. download.py 调用 yt-dlp 下载视频：
   - 获取视频标题、时长
   - 尝试下载字幕（B 站通常有字幕）
   - 下载音频文件（.m4a 格式）

5. 如果有字幕，直接读字幕 → 拿到文字
   如果没有字幕，调用语音识别把音频转成文字

6. refine.py 把文字交给 AI 润色：
   - 如果文字很长，切成几段同时处理
   - 每段交给 AI："请把这段话润色成可读的文稿"
   - 把处理完的段落拼起来
   - 保存到 output/ 目录下

7. generate_ai_summary 生成 AI 总结：
   - 把润色好的文稿交给 AI（用更快的模型）
   - AI 输出：1-2 句概括 + 3-5 个要点

8. deliver_feishu.py 发布到飞书：
   - 创建飞书文档
   - 在顶部插入"原文链接"引用
   - 在顶部插入"AI 总结"引用
   - 把文稿内容转成飞书文档的格式，写进去
   - 把你加为协作者（这样你才能打开文档）

9. bot.py 收到飞书文档链接，回复你：
   "✅ 处理完成！飞书文档：https://feishu.cn/docx/xxxxx"
```

---

## 三、准备工作：安装软件和工具

### 3.1 在电脑上安装 Python

**如果你的电脑是 Windows**：

1. 打开浏览器，访问：https://python.org
2. 点击黄色的 "Download Python" 按钮（下载最新版，3.11 以上就行）
3. 下载完成后，双击安装包
4. **重要**：安装界面最下面有个复选框 "Add Python to PATH"，**一定要勾上**
5. 点击 "Install Now" 开始安装
6. 安装完成后，测试一下安装是否成功：

```powershell
# 打开 PowerShell（在开始菜单搜索 "PowerShell"）
# 输入下面命令，按回车
python --version
# 应该看到类似输出：Python 3.11.9
```

### 3.2 下载项目代码

```powershell
# 在 PowerShell 中执行

# 1. 先装 git（如果还没装的话）
#    去 https://git-scm.com 下载安装

# 2. 找一个你喜欢的目录，把代码下载下来
cd D:\
git clone https://github.com/hj363049394/MyAgent.git
cd MyAgent\Transformer\media-transcriber-agent

# 3. 创建虚拟环境（给项目一个独立的工具箱）
python -m venv venv

# 4. 激活虚拟环境（进入项目的工具箱）
venv\Scripts\activate
# 激活成功后，命令行前面会显示 (venv)

# 5. 安装项目需要的工具
pip install -r requirements.txt

# 6. 安装飞书相关的工具（单独装，不在 requirements.txt 里）
pip install lark-oapi
```

> **注意**：以后每次打开新的命令行窗口，都要先执行 `venv\Scripts\activate` 激活虚拟环境，然后再运行项目。

### 3.3 申请智谱 AI 的 API Key

项目的 AI 能力来自智谱 AI（清华大学开发的模型），需要注册一个账号获取密钥。

1. 打开浏览器，访问：https://open.bigmodel.cn/
2. 点击"注册"，用手机号注册
3. 登录后，完成实名认证（必须实名才能用）
4. 进入「API Keys」页面
5. 点击"创建新的 API Key"
6. 复制生成的 Key（格式像这样：`xxxxxxxx.xxxxxxxx`）
7. **把 Key 保存好，只显示一次，离开页面就看不到了**

然后在项目目录创建 `.env` 文件，把 Key 填进去：

```powershell
# 在 PowerShell 中执行（确保在项目根目录）
cd D:\MyAgent\Transformer\media-transcriber-agent

# 创建 .env 文件
New-Item -Path .env -ItemType File -Force

# 用记事本打开
notepad .env
```

在记事本中输入：

```
OPENAI_API_KEY=你的Key
OPENAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4
```

保存关闭。

验证一下是否配置成功：

```powershell
# 在 PowerShell 中执行（确保在项目根目录，且 venv 已激活）
python -c "from openai import OpenAI; import os; from dotenv import dotenv_values; config = dotenv_values('.env'); client = OpenAI(api_key=config['OPENAI_API_KEY'], base_url=config['OPENAI_BASE_URL']); r = client.chat.completions.create(model='glm-4-flash', messages=[{'role':'user','content':'回复 PONG'}]); print(r.choices[0].message.content)"
# 如果输出 PONG，说明配置成功
```

---

## 四、飞书应用配置（最关键的步骤）

> ⚠️ **这是最容易出错的环节**。很多人卡在飞书配置上，请仔细阅读每一步。
>
> 你需要获取 4 个关键信息：App ID、App Secret、你的 User ID、文件夹 Token。

### 4.1 为什么要创建飞书应用

你的机器人需要"飞书官方认证的身份"才能：
1. **收到消息**：用户在飞书发消息，机器人能收到
2. **发出消息**：机器人能回复用户
3. **创建文档**：机器人能自动创建飞书文档
4. **授权给你**：机器人创建的文档，你能打开和编辑

这些都需要通过飞书开放平台来配置。**不配置的话，机器人什么也做不了**。

### 4.2 创建飞书应用

1. 打开浏览器，访问：https://open.feishu.cn/app
2. 用飞书账号登录（**个人账号就行，不需要企业版**）
3. 点击"**创建企业自建应用**"
4. 填写信息：
   - **应用名称**：随便填，比如"我的转录机器人"
   - **应用描述**：随便写一句
   - **应用图标**：可以不上传
5. 点击创建

创建完成后，你会进入应用详情页。现在要记录两个重要信息：

6. 点击左侧菜单「**凭证与基础信息**」
7. 找到「**应用凭证**」区域
8. 你会看到：
   - **App ID**：格式如 `cli_xxxxxxxxxxxxxxxx`（复制下来）
   - **App Secret**：格式如 32 位随机字符串（复制下来）

> ⚠️ **App Secret 只显示一次**，务必备份好。如果忘了，只能重置。

### 4.3 添加机器人功能

1. 在应用详情页，点击左侧「**应用能力**」
2. 点击「**添加应用能力**」
3. 勾选"**机器人**"
4. 点击保存
5. 可以设置机器人的名字和头像（可选）

> 没有这一步，用户在飞书里搜不到你的机器人。

### 4.4 开通权限

1. 点击左侧「**权限管理**」
2. 在搜索框中搜索以下权限，逐个点击"开通"：

| 搜索关键词 | 这个权限是干什么的 |
|-----------|-------------------|
| `im:message` | 收发消息的基础权限 |
| `im:message.p2p_msg` | 接收私聊消息 |
| `im:message.group_at_msg` | 接收群聊中 @机器人 的消息 |
| `im:message:send_as_bot` | 机器人发消息 |
| `docx:document` | 创建和编辑飞书文档 |
| `drive:drive` | 操作云空间 |
| `drive:permission` | 管理文档权限 |

3. 全部开通后，页面顶部会提示"**权限变更需要重新发版**"（别急，4.6 节会做）

### 4.5 设置消息接收方式

1. 点击左侧「**事件订阅**」
2. 在"接收方式"中，选择"**使用长连接接收事件**"

   > ⚠️ **不要选 Webhook 模式**！Webhook 需要公网域名，很麻烦。
   > 长连接模式（WebSocket）本地电脑就能直接跑。

3. 在"添加事件"中，搜索"**接收消息**"
4. 找到"**接收消息 v2.0**"，点击添加
5. 保存

### 4.6 发布上线

每次修改权限或事件后，**必须发布新版本才能生效**。

1. 点击左侧「**版本管理与发布**」
2. 点击「**创建版本**」
3. 填写：
   - **应用版本号**：填 `1.0.0`
   - **可用范围**：选"**所有员工**"（或至少包含你自己）
4. 点击"保存"
5. 点击"**申请发布**"
6. 自建应用通常立即通过，不需要审核

### 4.7 获取你的用户 ID（最容易出错的一步）

**这个 ID 是干什么的**：机器人创建文档后，需要把你的飞书账号加为协作者，这样你才能打开文档。这个 ID 就是告诉机器人"你是谁"。

**最容易搞错的地方**：飞书里有好几种 ID（用户 ID、开放 ID、Union ID），同一个人的不同 ID 长得不一样。**一定要用机器人日志里显示的 ID**。

**正确获取方法**：

1. 先启动机器人（第七章会教，这里先做个标记）
2. 在飞书里找到你的机器人，给它发一条消息（比如"hello"）
3. 查看机器人的日志，找到类似这行：
   ```
   收到消息 from ou_xxxxxxxxxxxxxxxx: hello
   ```
4. `ou_xxxxxxxxxxxxxxxx` 就是你的用户 ID

把用户 ID 填到 `.env` 文件：

```
FEISHU_USER_ID=ou_xxxxxxxxxxxxxxxx
```

> ⚠️ **不要把 App ID（`cli_xxx`）填到这里**。App ID 是机器人的身份，User ID 是你的身份，完全不一样。

### 4.8 设置文档保存目录（推荐）

如果不设置，机器人生成的文档会散落在根目录，不好管理。推荐设置一个专门的文件夹。

**坑点**：飞书云空间的共享面板搜索的是"人"，搜不到机器人应用，所以不能通过界面手动加权限。

**正确做法：让机器人自己创建文件夹**

在项目根目录执行：

```powershell
# 确保 venv 已激活
venv\Scripts\activate
python tmp\create_folder.py
```

这个脚本会：
1. 用机器人的身份登录飞书
2. 在机器人的云空间里创建一个叫"Bot 转录文稿"的文件夹
3. 输出一个文件夹 ID（folder_token）

把输出的 ID 填到 `.env`：

```
FEISHU_FOLDER_TOKEN=输出的folder_token
```

然后给**你自己**授权访问这个文件夹：

```powershell
python tmp\grant_folder_permission.py
```

### 4.9 飞书配置常见问题速查

| 你遇到的问题 | 可能的原因 | 怎么解决 |
|-------------|-----------|---------|
| 启动后看不到 `connected to wss://` | App ID 或 App Secret 填错了 | 检查 `.env` 文件 |
| 在飞书里搜不到机器人 | 没有发布版本 | 去版本管理页面创建版本并发布 |
| 发了消息机器人没反应 | 没有订阅"接收消息"事件 | 去事件订阅页面添加事件 |
| 私聊没反应，群聊可以 | 缺少私聊权限 | 去权限管理页面开通 `im:message.p2p_msg` |
| 群聊@机器人没反应 | 缺少群聊权限 | 去权限管理页面开通 `im:message.group_at_msg` |
| 文档创建失败（403 错误） | 机器人没有文件夹权限 | 用 `create_folder.py` 让机器人自己建文件夹 |
| 文档创建了但打不开 | 没有给你授权 | 检查 `FEISHU_USER_ID` 是否正确 |
| 改了权限还是不行 | 没有重新发布 | 每次改权限都必须重新创建版本并发布 |

---

## 五、写代码：各个模块做了什么

> 这一章介绍每个代码文件是干什么的。**不需要看懂代码**，只需要知道每个文件的作用，方便以后修改或排查问题时知道去哪个文件找。

### 5.1 下载视频 download.py

**作用**：根据链接下载视频或音频。

**怎么做的**：
- 用 yt-dlp 这个工具下载（它支持几乎所有视频网站）
- 优先下载字幕（如果视频有字幕的话）
- 不同平台用不同的 cookies（登录凭证），避免被反爬

**文件位置**：[scripts/download.py](scripts/download.py)

### 5.2 语音转文字 transcribe_funasr.py

**作用**：把音频文件转成文字。

**怎么做的**：
- 用 FunASR 模型（阿里达摩院开发的）
- 先把音频转成 WAV 格式（用 ffmpeg 工具）
- 再把 WAV 丢给模型，模型输出文字
- 速度很快：10 分钟的视频约 30 秒转完

**文件位置**：[scripts/transcribe_funasr.py](scripts/transcribe_funasr.py)

### 5.3 提取网页正文 extract_web.py

**作用**：从网页链接里提取正文内容（去掉广告、导航栏、侧边栏等）。

**怎么做的**：用 trafilatura 这个库，它专门从网页里提取正文，效果很好。

**文件位置**：[scripts/extract_web.py](scripts/extract_web.py)

### 5.4 AI 润色稿件 refine.py

**作用**：用 AI 把粗糙的文字润色成可读的文稿，并生成 AI 总结。

**怎么做的**：
- 把文字按 3000 字分段，每段交给 AI 处理
- 同时开 3 个线程处理（避免 AI 接口限流）
- 如果 AI 主模型太慢，自动换备用模型
- 总结用更快的模型（glm-4.5-air），比主模型快 5-10 倍

**文件位置**：[scripts/refine.py](scripts/refine.py)

### 5.5 发布到飞书文档 deliver_feishu.py

**作用**：把 Markdown 格式的文稿转成飞书文档，并发布。

**怎么做的**：
- 把 Markdown 转成飞书文档的格式（block 结构）
- 识别 `<!--AI_SUMMARY_START-->` 标记，转成引用块
- 创建飞书文档 → 写入内容 → 给你授权

**文件位置**：[scripts/deliver_feishu.py](scripts/deliver_feishu.py)

### 5.6 总指挥 pipeline.py

**作用**：串联所有步骤，是整个流程的"总指挥"。

**怎么做的**：
- 判断输入是什么类型：URL 还是本地文件
- 如果是 URL，识别是视频平台还是网页文章
- 按类型调用不同的处理流程
- 处理完后，把结果交给飞书发布模块

**文件位置**：[scripts/pipeline.py](scripts/pipeline.py)

### 5.7 飞书机器人 bot.py

**作用**：在飞书里接收消息、回复消息。

**怎么做的**：
- 用 WebSocket 长连接跟飞书服务器保持通信
- 收到消息后，检查是不是链接
- 如果是链接，放进任务队列（避免同时处理太多）
- 任务完成后，回复用户飞书文档链接

**支持的命令**：
- `/help`：显示帮助
- `/status`：查看队列状态
- `/progress`：查看当前任务进度

**文件位置**：[scripts/bot.py](scripts/bot.py)

---

## 六、踩坑记录：14 个实际问题及解决方法

> 这一章记录了实际开发中踩过的所有坑。**如果你遇到问题，先来这里查**。

### 问题 1：飞书文档创建报 403 错误

**现象**：配置了 `FEISHU_FOLDER_TOKEN` 后，创建文档失败，返回 403。

**原因**：你填的文件夹，机器人没有写入权限。飞书 API 校验的是机器人本身，跟你有没有权限无关。

**解决**：让机器人自己创建文件夹（`python tmp/create_folder.py`），机器人自动有完整权限。

### 问题 2：飞书云空间搜不到机器人

**现象**：在文件夹共享面板搜索机器人名字，找不到。

**原因**：飞书共享面板搜索的是"人"，搜不到"机器人应用"。

**解决**：用 API 直接授权（`python tmp/grant_folder_permission.py`），不通过界面。

### 问题 3：抖音下载需要 cookies

**现象**：下载抖音视频时报错，提示需要 cookies。

**原因**：抖音要求登录态才能下载。

**解决**：
1. 浏览器登录抖音
2. 安装 "Get cookies.txt" 浏览器扩展
3. 导出 cookies 保存为 `config/douyin_cookies.txt`
4. 代码会自动使用这个文件

### 问题 4：下载到了旧文件（严重 bug）

**现象**：下载抖音视频，但返回了之前下载的 B 站旧文件。

**原因**：代码遍历下载目录找文件，把旧文件当成了新下好的文件。

**解决**：
1. 下载前先记录目录里已有哪些文件
2. 下载后只在新出现的文件里找
3. 按视频标题匹配，避免找错

### 问题 5：下载的 MP4 文件不被识别

**现象**：抖音下载了 .mp4 文件，但代码报"未找到音频文件"。

**原因**：代码只识别音频格式（.m4a、.mp3），不识别视频格式（.mp4）。

**解决**：把 .mp4、.mkv、.mov、.avi 也加入识别列表。

### 问题 6：ffmpeg 找不到

**现象**：语音转文字时报"ffmpeg 不可用"。

**原因**：用系统 Python 启动机器人，系统 Python 没有装 ffmpeg 相关工具。

**解决**：**必须用虚拟环境的 Python 启动**：
```powershell
venv\Scripts\python.exe scripts\bot.py
# 不要用: python scripts\bot.py
```

### 问题 7：AI 接口报 429（请求太频繁）

**现象**：调用 AI 润色时，部分文字被降级到备用模型处理。

**原因**：同时发 4 个请求，超过了 AI 接口的 QPS 限制。

**解决**：
1. 把并发数从 4 降到 3
2. 两次任务之间至少间隔 1 分钟
3. 即使被限流，也有备用模型兜底，不会失败

### 问题 8：飞书文档标题用了视频原标题

**现象**：用户觉得飞书文档标题应该是正文第一个标题，而不是视频的原标题。

**解决**：代码从文稿正文中提取第一个 `#` 标题作为飞书文档标题。

### 问题 9：飞书高亮块创建失败

**现象**：往飞书文档写入高亮块（callout）时，返回 400 错误。

**原因**：飞书的高亮块需要两步操作（先创建容器，再往里填内容），和一次写入的方式不兼容。

**解决**：降级方案——用引用块（quote）模拟高亮块，把标题加粗，视觉上也能区分。

### 问题 10：飞书文档只有标题没有内容

**现象**：文档创建成功，但正文为空。

**原因**：高亮块的颜色参数传了 11，飞书只接受 1-7，导致整个写入失败。

**解决**：颜色参数改为 1。

### 问题 11：同一个视频第二次发送失败

**现象**：第一次发送处理成功，第二次发同一个链接失败。

**原因**：yt-dlp 发现文件已经下载过了，跳过下载。但代码只在新文件里查找，找不到。

**解决**：增加兜底逻辑——在所有文件里按标题查找（包括已存在的文件）。

### 问题 12：Docker 启动报缺少模块

**现象**：Docker 容器启动后报 `ModuleNotFoundError: No module named 'trafilatura'`。

**原因**：`requirements.txt` 依赖清单不完整。

**解决**：补充了 trafilatura、beautifulsoup4、lxml、faster-whisper、transformers、tiktoken 到依赖清单。

### 问题 13：Docker 构建太慢（30+ 分钟）

**现象**：Docker 构建镜像时，下载依赖卡了半个小时。

**原因**：默认下载源在国外，国内访问慢。

**解决**：Dockerfile 里配置了国内镜像源：
- 系统软件源 → 阿里云镜像
- Python 包源 → 清华大学镜像
- PyTorch 源 → 清华大学镜像

### 问题 14：GitHub 拉代码失败

**现象**：`git clone` 报 `Password authentication is not supported`。

**原因**：GitHub 2021 年起不可以用密码登录，必须用 Token 或 SSH。

**解决**：
- 把仓库设为公开（public），直接用 `curl` 下载 ZIP 包
- 或者用 Personal Access Token 替代密码

---

## 七、本地运行：在你自己电脑上启动

### 7.1 最终配置 .env 文件

回顾一下，你的 `.env` 文件最终应该包含这些内容：

```
# 智谱 AI 的 Key（第三章申请的）
OPENAI_API_KEY=xxxxxxxx.xxxxxxxx
OPENAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4

# 飞书应用凭据（第四章创建的）
FEISHU_APP_ID=cli_xxxxxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 你的飞书用户 ID（第四章 4.7 节获取的）
FEISHU_USER_ID=ou_xxxxxxxxxxxxxxxx

# 文档保存目录（第四章 4.8 节获取的，可以不填）
FEISHU_FOLDER_TOKEN=xxxxxxxxxxxxxxxx

# 机器人权限设置
FEISHU_ALLOW_ALL_USERS=true
FEISHU_DM_POLICY=open
FEISHU_GROUP_POLICY=open
```

### 7.2 启动机器人

```powershell
# 1. 进入项目目录
cd D:\MyAgent\Transformer\media-transcriber-agent

# 2. 激活虚拟环境（重要！）
venv\Scripts\activate

# 3. 启动机器人
python scripts\bot.py
```

如果一切正常，你会看到：

```
============================================================
音视频转录整理 Bot 启动
  App ID: cli_xxxxx
  User ID: ou_xxxxx
  Folder Token: xxxxxx
  允许所有用户: True
============================================================
正在连接飞书 WebSocket...
[INFO] connected to wss://msg-frontier.feishu.cn/ws/v2?...
```

看到 `connected to wss://` 就成功了！

> **注意**：机器人启动后会一直运行，**不要关掉命令行窗口**。按 `Ctrl+C` 可以停止。

### 7.3 在飞书中使用

1. 打开飞书 App
2. 在搜索框搜你的机器人名字
3. 点进去，给它发链接
4. 机器人会回复"⏳ 开始处理"
5. 等 2-4 分钟，收到"✅ 处理完成"和飞书文档链接

**可以发的链接类型**：
- B 站：`https://www.bilibili.com/video/BVxxxxx`
- 抖音：`https://www.douyin.com/video/xxxxx`
- 小红书：`https://www.xiaohongshu.com/xxx`
- YouTube：`https://youtube.com/watch?v=xxxxx`
- 微信公众号文章：`https://mp.weixin.qq.com/s/xxxxx`

**可以用的命令**：
- 发 `/help` → 查看帮助
- 发 `/status` → 查看有多少任务在排队
- 发 `/progress` → 查看当前正在处理的任务进度

---

## 八、搬到云服务器上运行

> 本地运行有一个问题：你的电脑关机了，机器人就停了。
> 部署到云服务器上，机器人可以 24 小时在线。

### 8.1 为什么上云

| 对比维度 | 本地电脑 | 云服务器 |
|---------|---------|---------|
| 运行时间 | 你开机时才运行 | 24 小时在线 |
| 网络稳定性 | 家庭宽带可能波动 | 机房网络稳定 |
| AI 调用速度 | 家庭宽带到 AI 服务器可能有延迟 | 机房到 AI 服务器更快 |
| 资源占用 | 占用你的电脑 | 不影响你的电脑 |

**本项目实际部署的服务器**：阿里云 4 核 8G，上海机房，系统是 Alibaba Cloud Linux 4。

### 8.2 服务器够不够用

这台服务器上已经跑了一个"寺庙项目"（包含一个后端和 3 个前端页面），用的是 Docker 部署。

**资源占用情况**：

| 服务 | CPU 占用 | 内存占用 |
|------|---------|---------|
| 寺庙项目（已有） | 约 0.4 核（10%） | 约 2.4 GB（30%） |
| 系统 + Docker | 约 0.2 核 | 约 0.5 GB |
| 转录机器人（新增） | 最多 2.5 核 | 最多 4 GB |
| **合计** | **约 3.1 核（78%）** | **约 6.9 GB（86%）** |
| **剩余** | **约 0.9 核** | **约 1.1 GB** |

**结论**：✅ **够用**。机器人在空闲时几乎不耗资源，只在处理任务时短暂占用 CPU。通过 Docker 的资源限制功能，可以确保机器人不会影响寺庙项目。

**Docker 里设置的限制**（在 `docker-compose.yml` 中）：
```yaml
deploy:
  resources:
    limits:
      cpus: '2.5'     # 最多用 2.5 个 CPU 核心
      memory: 4G       # 最多用 4G 内存
```

### 8.3 上云后能快多少

| 环节 | 本地电脑 | 云服务器 | 提升 |
|------|---------|---------|------|
| 下载视频 | 3-30 秒 | 3-30 秒 | 差不多 |
| 语音转文字 | 约 30 秒 | 约 20-25 秒 | 略快 |
| AI 润色 | 约 2 分钟 | 约 1.5-2 分钟 | 网络更稳定 |
| AI 总结 | 约 3.5 分钟（常有重试） | 约 30 秒-1 分钟 | 重试概率大降 |
| 发布到飞书 | 约 4 秒 | 约 2-3 秒 | 略快 |
| **总计** | **约 7-8 分钟** | **约 2.5-3.5 分钟** | **提升 50-60%** |

**为什么云上快这么多**：
- 上海机房到智谱 AI 的网络延迟低（< 50ms），而家庭宽带可能 100-300ms
- 网络稳定，AI 调用很少需要重试

### 8.4 部署步骤

**前提**：服务器上已经装了 Docker（寺庙项目用的就是 Docker，所以已经有了）。

> 详细部署指南见 [deploy.md](deploy.md)，这里说关键步骤。

**Step 1：在服务器上拉代码**

```bash
# SSH 登录服务器
ssh root@你的服务器IP

# 创建工作目录
mkdir -p /opt/transcriber-agent
cd /opt/transcriber-agent
```

> ⚠️ **实际踩坑**：服务器上可能没有 git 命令，GitHub 也可能认证失败。
> 如果 `git clone` 报 `git: command not found`，先装 git：
> ```bash
> dnf install -y git        # Alibaba Cloud Linux
> # 或 apt install -y git   # Ubuntu/Debian
> ```
> 
> 如果 `git clone` 报 `Password authentication is not supported`：
> - 方式一：把 GitHub 仓库设为 public，用 `curl` 下载 ZIP 包
> - 方式二：用 Personal Access Token 替代密码

```bash
# 拉代码（仓库是 public 的话）
git clone https://github.com/hj363049394/MyAgent.git tmp-repo
cp -r tmp-repo/Transformer/media-transcriber-agent/* .
cp tmp-repo/Transformer/media-transcriber-agent/.dockerignore .
rm -rf tmp-repo

# 如果 git clone 失败，用 ZIP 下载（不需要认证）
# curl -L -o repo.zip https://github.com/hj363049394/MyAgent/archive/refs/heads/main.zip
# unzip repo.zip
# cp -r MyAgent-main/Transformer/media-transcriber-agent/* .
# cp MyAgent-main/Transformer/media-transcriber-agent/.dockerignore .
# rm -rf MyAgent-main repo.zip
```

**Step 2：配置 .env**

```bash
cd /opt/transcriber-agent

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
```

**Step 3：上传 cookies**

在**本地电脑**上执行（把 cookies 文件传到服务器）：

```powershell
scp -r config\*.txt root@服务器IP:/opt/transcriber-agent/config/
```

在服务器上设置权限：

```bash
chmod 600 /opt/transcriber-agent/config/*.txt
```

**Step 4：构建并启动**

```bash
cd /opt/transcriber-agent

# 构建 Docker 镜像（首次约 5-10 分钟）
docker compose build

# 后台启动
docker compose up -d

# 查看日志
docker compose logs -f bot
```

看到 `connected to wss://` 就表示部署成功了。

### 8.5 本地和云上不能同时跑

⚠️ **重要**：同一个飞书应用（同一个 App ID）只能有一个 WebSocket 连接。

- 如果本地电脑和云服务器同时启动机器人，消息会**随机发给其中一个**
- 如果你本地电脑关机了，云上会自动接管

**正确的做法**：
1. 云上部署成功后，**停止本地电脑上的机器人**（在命令行按 Ctrl+C）
2. 在飞书发一个链接，确认云上能正常处理
3. 以后只用云上的，本地只在调试代码时临时启动

### 8.6 怎么确认是云上在处理

**方法 1：看云上日志**（最可靠）

在服务器上执行：

```bash
docker compose logs -f bot
```

然后在飞书发链接，如果服务器日志出现"收到消息"，说明云上在处理。

**方法 2：看耗时**

- 云上处理一个 9 分钟的视频约 2.5-3.5 分钟
- 本地处理约 7-8 分钟
- 如果明显变快了，就是云上在处理

**方法 3：检查本地进程**

在本地 Windows 上执行：

```powershell
# 查看有没有 python 进程在跑
Get-Process python -ErrorAction SilentlyContinue
```

如果没有 python 进程，说明本地已停，云上在跑。

### 8.7 日常维护

```bash
# 查看日志
docker compose logs -f bot          # 实时日志
docker compose logs --tail 100 bot  # 最近 100 行

# 重启机器人
docker compose restart bot

# 更新代码后重建
docker compose up -d --build

# 查看资源占用
docker stats transcriber-bot

# 查看下载的文件
ls -lh /opt/transcriber-agent/tmp/downloads/

# 清理临时文件（磁盘不够时）
rm -rf /opt/transcriber-agent/tmp/downloads/*
```

**cookies 过期了怎么办**：

1. 在本地电脑用浏览器重新登录平台
2. 导出新的 cookies 文件
3. scp 上传到服务器：
   ```powershell
   scp douyin_cookies.txt root@IP:/opt/transcriber-agent/config/
   ```
4. 重启容器：
   ```bash
   docker compose restart bot
   ```

---

## 九、未来可以做什么

### 已经评估过，暂不实施

| 方向 | 为什么不做 |
|------|-----------|
| 微信机器人 | 个人订阅号无法主动推送消息（5 秒必须回复，但视频处理要几分钟）；个人微信第三方协议封号风险极高 |
| GPU 加速语音识别 | 现在 CPU 上已经够快了（10 分钟视频 30 秒），不需要 GPU |
| 同时处理更多视频 | 并发太多会被 AI 接口限流，反而影响稳定性 |

### 未来可以探索

| 方向 | 说明 |
|------|------|
| 更多平台 | 小宇宙播客、YouTube 优先用字幕 |
| 真正的飞书高亮块 | 需要改飞书 API 调用方式（分两步操作） |
| 批量处理 | 一次发多个链接，排队处理 |
| 用户偏好设置 | 每个人可以定制润色风格 |

---

## 十、附录

### 10.1 完整 .env 配置模板

```
# ========== AI 配置 ==========
OPENAI_API_KEY=xxxxxxxx.xxxxxxxx
OPENAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4

# ========== 飞书应用 ==========
FEISHU_APP_ID=cli_xxxxxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# ========== 飞书用户 ==========
# 获取方法：启动机器人后给它发消息，看日志里 sender=ou_xxx
FEISHU_USER_ID=ou_xxxxxxxxxxxxxxxx

# ========== 文档目录（可选） ==========
# 获取方法：python tmp/create_folder.py
FEISHU_FOLDER_TOKEN=xxxxxxxxxxxxxxxx

# ========== 机器人权限 ==========
FEISHU_ALLOW_ALL_USERS=true
FEISHU_DM_POLICY=open
FEISHU_GROUP_POLICY=open
```

### 10.2 常用命令速查

**本地 Windows**：
```powershell
# 启动
cd D:\MyAgent\Transformer\media-transcriber-agent
venv\Scripts\python.exe scripts\bot.py

# 命令行测试（不用机器人，直接处理一个链接）
venv\Scripts\python.exe scripts\pipeline.py --input "https://..." --deliver-to-feishu
```

**云服务器**：
```bash
# 部署
cd /opt/transcriber-agent
docker compose build
docker compose up -d
docker compose logs -f bot

# 日常
docker compose ps
docker compose restart bot
docker stats transcriber-bot
```

### 10.3 相关文档

| 文档 | 内容 |
|------|------|
| [installation.md](installation.md) | 详细的安装步骤 |
| [startup.md](startup.md) | 日常启动方法 |
| [usage.md](usage.md) | 使用说明 |
| [deploy.md](deploy.md) | 服务器部署详细指南 |
| [troubleshooting.md](troubleshooting.md) | 更多故障排查 |

### 10.4 项目依赖清单

```
yt-dlp          → 下载视频
funasr          → 语音转文字
torch           → AI 模型运行环境
openai          → 调用 AI 接口
trafilatura     → 提取网页正文
lark-oapi       → 连接飞书
requests        → 发送 HTTP 请求
imageio-ffmpeg  → 音频格式转换（备用）
```

### 10.5 项目仓库

GitHub：https://github.com/hj363049394/MyAgent/tree/main/Transformer/media-transcriber-agent

---

**文档结束**

有问题先看 [troubleshooting.md](troubleshooting.md)，找不到答案再提交 GitHub Issue。