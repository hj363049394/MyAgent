# 安装部署指南

> 本文档指导你完成 media-transcriber Agent 的本地安装与配置。
> 参考：知识库 `01-hermes-agent/03-hermes-agent-installation.md` 的踩坑经验。

---

## 一、环境要求

| 项目 | 要求 | 备注 |
|---|---|---|
| 操作系统 | Windows 10/11（WSL2 推荐）/ macOS / Linux | Windows 原生也可，WSL2 体验更好 |
| Python | 3.11 或更高版本 | |
| 内存 | ≥ 8GB（ASR medium 模型需要 ~1GB） | |
| 磁盘 | ≥ 2GB（含模型缓存） | |
| 网络 | 需访问 PyPI、智谱 API、视频平台 | YouTube 需代理 |

---

## 二、安装 Python 依赖

### 2.1 安装核心 Python 库

```bash
# 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 安装核心依赖
pip install yt-dlp faster-whisper trafilatura openai
```

### 2.2 安装 ffmpeg

ffmpeg 是音频转码的核心依赖，必须安装。

#### 方式 A：系统安装（推荐）

**Windows（winget）**：
```bash
winget install ffmpeg
```

**Windows（choco）**：
```bash
choco install ffmpeg
```

**Linux（Ubuntu/Debian）**：
```bash
sudo apt install ffmpeg
```

**macOS（Homebrew）**：
```bash
brew install ffmpeg
```

#### 方式 B：用 imageio-ffmpeg 替代（无需系统安装）

如果系统安装 ffmpeg 失败，可以用 Python 包 `imageio-ffmpeg` 提供的本地版本：

```bash
pip install imageio-ffmpeg
```

`download.py` 中的 `get_ffmpeg_path()` 会自动检测：优先用系统 ffmpeg，没有则降级到 imageio-ffmpeg。

### 2.3 安装飞书 SDK（Phase 2+）

```bash
pip install lark-oapi requests
```

> Phase 2（飞书文档交付）：`deliver_feishu.py` 直接走 REST API，只用 `requests`
> Phase 3（飞书 Bot 触发）：`bot.py` 用 `lark-oapi` 的 WebSocket 长连接接收消息

### 2.4 验证安装

```bash
python -c "import yt_dlp; print('yt-dlp:', yt_dlp.version.__version__)"
python -c "import faster_whisper; print('faster-whisper: OK')"
python -c "import trafilatura; print('trafilatura: OK')"
python -c "from openai import OpenAI; print('openai: OK')"
ffmpeg -version | head -n 1
```

---

## 三、配置 LLM 后端（智谱 GLM）

### 3.1 获取智谱 API Key

1. 访问 [open.bigmodel.cn](https://open.bigmodel.cn/)
2. 注册账号并实名认证
3. 进入「API Keys」页面创建 Key
4. 复制 Key（格式：`xxxxxxxx.xxxxxxxx`）

### 3.2 配置环境变量

在项目根目录创建 `.env` 文件（参考 `profile/.env.example`）：

```bash
# 复制模板
cp profile/.env.example .env
```

编辑 `.env`，填入你的 API Key：

```bash
GLM_API_KEY=你的真实API Key
GLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4
```

### 3.3 验证 LLM 连通性

```bash
# 设置环境变量（Windows PowerShell）
$env:GLM_API_KEY="你的Key"

# 测试
python -c "
from openai import OpenAI
import os
client = OpenAI(
    api_key=os.environ['GLM_API_KEY'],
    base_url='https://open.bigmodel.cn/api/paas/v4'
)
r = client.chat.completions.create(
    model='glm-4.7',
    messages=[{'role':'user','content':'回复 PONG'}]
)
print(r.choices[0].message.content)
"
# 预期输出: PONG
```

> **方式 B（推荐）**：用通用 OpenAI 兼容方式接入，在 `.env` 中配 `OPENAI_API_KEY` + `OPENAI_BASE_URL`，`config.yaml` 中 `provider: "auto"`。优势：切换 LLM 后端时只需改 `base_url` 和 `model`。详见 [profile/.env.example](../profile/.env.example)。

---

## 四、配置飞书应用（Phase 2：文档交付）

### 4.1 创建飞书自建应用

1. 访问 [飞书开放平台](https://open.feishu.cn/app) → 创建企业自建应用
2. 记录 **App ID**（`cli_xxxxx`）和 **App Secret**
3. 添加能力：**机器人**（Phase 3 需要，Phase 2 可先不加）
4. 权限管理 → 开通以下权限：
   - `docx:document`（文档读写）
   - `drive:drive`（云空间读写）
   - `drive:permission`（权限管理）
   - `wiki:wiki`（知识库读写，可选）
5. 版本管理 → 创建版本 → 申请发布 → 管理员审核通过

### 4.2 获取飞书用户 ID

用于文档创建后授权你本人为协作者：

1. 打开飞书个人主页
2. 右上角更多 → 获取 ID（`ou_xxxxxxxxxxxxxxxx`）
3. 或调用人事 API 获取

### 4.3 配置 .env

在项目根目录的 `.env` 中追加：

```bash
FEISHU_APP_ID=cli_xxxxx
FEISHU_APP_SECRET=xxxxxx
FEISHU_USER_ID=ou_xxxxxxxxxxxxxxxx
# FEISHU_FOLDER_TOKEN=xxxxxx   # 可选，指定文档创建文件夹
```

### 4.4 验证飞书连通性

```bash
python -c "
import sys; sys.path.insert(0, 'scripts')
from deliver_feishu import _get_tenant_access_token
import os
# 从 .env 读取（需先 load_env_file 或手动 export）
token = _get_tenant_access_token(
    os.environ['FEISHU_APP_ID'],
    os.environ['FEISHU_APP_SECRET']
)
print('Token:', token[:20] + '...' if token else 'FAILED')
"
# 预期输出: Token: t-xxxxxxx...
```

### 4.5 Phase 2 完整测试

```bash
# 测试网页文章 + 飞书交付
python scripts/pipeline.py \
  --input "https://mp.weixin.qq.com/s/xxxxx" \
  --deliver-to-feishu
```

成功输出会包含飞书文档链接。详见 [usage.md](usage.md) 第二章。

---

## 五、配置飞书 Bot（Phase 3：Bot 触发）

本节从零开始，详细说明如何在飞书开放平台创建应用并配置为 Bot，最终通过 WebSocket 长连接接收消息。Phase 2 已完成此过程的用户可直接跳到 5.4 验证。

### 5.1 创建飞书自建应用

1. 访问飞书开放平台：https://open.feishu.cn/app
2. 登录飞书账号 → 点击"**创建企业自建应用**"
3. 填写应用信息：
   - **应用名称**：音视频转录整理 Bot（自定义）
   - **应用描述**：将视频/音频/网页链接转为可读文稿
   - **应用图标**：上传任意图标（可选）
4. 创建完成 → 进入应用详情页 → 记录 **App ID** 和 **App Secret**（凭证与基础信息 → 应用凭证）

> 这两个值就是 `.env` 中的 `FEISHU_APP_ID` 和 `FEISHU_APP_SECRET`。

### 5.2 添加机器人能力

1. 应用详情页 → **应用能力** → **添加应用能力**
2. 勾选"**机器人**" → 保存
3. 配置机器人信息：
   - **机器人名称**：显示在飞书消息中（可与应用名不同）
   - **机器人描述**：可选
   - **机器人头像**：可选

### 5.3 配置权限与事件订阅

#### 5.3.1 开通权限

应用详情页 → **权限管理** → 开通以下权限：

| 权限 | 权限标识 | 用途 |
|---|---|---|
| 获取与发送单聊、群组消息 | `im:message` | 消息读写基础权限 |
| 读取用户发给机器人的单聊消息 | `im:message.p2p_msg:readonly` | 私聊接收消息 |
| 读取群聊中用户@机器人的消息 | `im:message.group_at_msg:readonly` | 群聊@接收消息 |
| 以应用的身份发消息 | `im:message:send_as_bot` | Bot 发送回复消息 |
| 获取与更新文档信息 | `docx:document` | Phase 2 创建/写入飞书文档 |
| 添加协作者 | `drive:drive:permission` | Phase 2 文档授权 |

> Phase 2 已开通文档相关权限的话，这里只需补充消息相关权限。

#### 5.3.2 订阅事件

应用详情页 → **事件订阅** → 选择"**使用长连接接收事件**"（重要！）

> 长连接模式无需公网 IP，本地直接跑。**不要选 Webhook 模式**，那需要公网域名。

添加事件：**接收消息 v2.0**（`im.message.receive_v1`）

#### 5.3.3 创建版本并发布

应用详情页 → **版本管理与发布** → **创建版本**

- **应用版本号**：1.0.0
- **可用范围**：选"所有员工"或指定成员（自己）
- **提交审核**：自建应用通常立即通过

> 权限变更后必须重新创建版本并发布，否则新权限不生效。

### 5.4 配置 .env

在 `.env` 中配置 Bot 权限策略（Phase 3 专属）：

```bash
# Phase 3：飞书 Bot 触发配置
FEISHU_ALLOW_ALL_USERS=true        # 允许所有用户触发（true/false）
FEISHU_DM_POLICY=open              # 私聊策略：open / restrict
FEISHU_GROUP_POLICY=open           # 群聊策略：open / restrict
# FEISHU_ADMIN_IDS=ou_xxxxxxxx     # 白名单（ALLOW_ALL_USERS=false 时生效）
```

### 5.5 启动 Bot

```bash
python scripts/bot.py
```

预期输出：
```
============================================================
音视频转录整理 Bot 启动
  App ID: cli_xxxxx
  User ID: ou_xxxxx
  允许所有用户: True
  群聊策略: open
  私聊策略: open
============================================================
正在连接飞书 WebSocket...
[INFO] Lark: connected to wss://msg-frontier.feishu.cn/ws/v2?...
```

看到 `connected to wss://` 即代表 WebSocket 长连接已建立。

### 5.6 验证消息接收

1. 打开飞书客户端 → 搜索你的应用名 → 找到 Bot
2. 私聊 Bot 发送 `/help` → 应立即收到帮助消息
3. 发送一个 URL（如 `https://mp.weixin.qq.com/s/xxxxx`）测试完整流程

### 5.7 常见配置问题

| 问题 | 根因 | 解决 |
|---|---|---|
| 启动后看不到 `connected to wss://` | App ID/Secret 错误 | 检查 .env 中凭据 |
| Bot 搜不到 | 未发布或可用范围不含自己 | 版本管理→创建版本→发布 |
| 发消息无响应 | 未订阅 `im.message.receive_v1` | 事件订阅→添加事件 |
| 私聊无响应 | 缺 `im:message.p2p_msg` 权限 | 权限管理→开通权限→重新发版 |
| 群聊@无响应 | 缺 `im:message.group_at_msg` 权限 | 权限管理→开通权限→重新发版 |
| 权限变更不生效 | 未重新发版 | 版本管理→创建新版本→发布 |

详见 [troubleshooting.md](troubleshooting.md) 坑 27-30。

---

## 六、下载 ASR 模型

faster-whisper 首次运行时会自动下载模型，但国内下载慢，建议预先下载。

### 6.1 自动下载（首次运行时）

模型会缓存到 `~/.cache/huggingface/`，首次运行 `transcribe.py` 时自动下载。

### 6.2 手动指定模型目录（可选）

在 `.env` 中配置：

```bash
WHISPER_CACHE_DIR=./.cache/whisper
```

### 6.3 模型大小参考

| 模型 | 大小 | CPU 速度（1小时音频） | 推荐场景 |
|---|---|---|---|
| tiny | 75MB | ~5 分钟 | 快速测试 |
| base | 145MB | ~10 分钟 | 快速预览 |
| small | 480MB | ~25 分钟 | 一般质量 |
| **medium** | 1.5GB | ~50 分钟 | **推荐（Phase 1）** |
| large-v3 | 3GB | ~2-3 小时 | 服务器+GPU（Phase 2） |

---

## 七、安装 Hermes Agent（Phase 3+ 备选方案）

> Phase 1-3 均不需要安装 Hermes Agent，本项目用独立轻量 Bot（`bot.py`）即可。
> 仅当需要 Hermes 的记忆体系/多平台/自进化能力时，才参考本节迁移到 Hermes 框架。

### 7.1 克隆 Hermes Agent

```bash
git clone --depth 1 https://github.com/NousResearch/hermes-agent.git
cd hermes-agent
```

### 7.2 创建虚拟环境并安装

```bash
uv venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

uv pip install -e ".[messaging,cron,cli,pty,mcp,dev]" \
  -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

### 7.3 安装飞书 SDK

```bash
pip install lark_oapi aiohttp websockets
```

### 7.4 创建 media-transcriber Profile

```bash
hermes profile create media-transcriber
```

将本项目的 `profile/` 目录下的配置文件复制到 Hermes 的 profile 目录：

```bash
cp profile/SOUL.md ~/.hermes/profiles/media-transcriber/
cp profile/config.yaml ~/.hermes/profiles/media-transcriber/
cp .env ~/.hermes/.env
cp prompts/system-prompt.md ~/.hermes/profiles/media-transcriber/
cp -r skills/* ~/.hermes/profiles/media-transcriber/skills/
```

### 7.5 验证

```bash
hermes --version
hermes -p media-transcriber chat
```

---

## 八、常见安装问题

### 问题 1：pip install faster-whisper 失败

**现象**：安装 faster-whisper 时报 CTranslate2 编译错误。

**解决**：
```bash
# 升级 pip 和 setuptools
pip install --upgrade pip setuptools wheel
# 重新安装
pip install faster-whisper
```

### 问题 2：ffmpeg 命令找不到

**现象**：运行时报 `FileNotFoundError: ffmpeg`。

**解决**：
- 方式 1：确认 ffmpeg 在 PATH 中（`where ffmpeg` / `which ffmpeg`）
- 方式 2：安装 imageio-ffmpeg 作为替代（`pip install imageio-ffmpeg`）

### 问题 3：智谱 API 401 错误

**现象**：调用 LLM 报 `HTTP 401 Unauthorized`。

**解决**：
- 检查 `GLM_API_KEY` 是否正确
- 检查 `config.yaml` 中 `provider` 是否为 `"zai"`（**不能用 `"custom"`**）
- 检查 Key 是否过期或额度用尽

### 问题 4：yt-dlp 下载失败

**现象**：下载 YouTube 视频报错。

**解决**：
- YouTube 需要代理，在 `.env` 中配置 `HTTPS_PROXY`
- 更新 yt-dlp：`pip install -U yt-dlp`
- 抖音/小红书链接需要完整分享链接

### 问题 5：faster-whisper 模型下载慢

**现象**：首次运行 ASR 卡在模型下载。

**解决**：
- 设置 HF 镜像：`export HF_ENDPOINT=https://hf-mirror.com`
- 或手动下载模型放到 `WHISPER_CACHE_DIR`

---

## 九、下一步

安装完成后，请阅读 [usage.md](usage.md) 了解如何使用。

如遇问题，参考 [troubleshooting.md](troubleshooting.md)。
