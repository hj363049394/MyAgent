# 使用说明

> 本文档介绍 media-transcriber Agent 的使用方法。
> Phase 1（MVP）使用命令行方式，Phase 3+ 通过飞书 Bot 触发。

---

## 一、Phase 1：命令行使用（MVP）

### 1.1 环境准备

```bash
# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 设置环境变量（或用 .env 文件）
# Windows PowerShell:
$env:GLM_API_KEY="你的Key"
# Linux/macOS:
export GLM_API_KEY="你的Key"
```

### 1.2 处理视频链接

#### YouTube 视频

```bash
python scripts/pipeline.py --input "https://www.youtube.com/watch?v=xxxxx"
```

#### B站视频

```bash
python scripts/pipeline.py --input "https://www.bilibili.com/video/BVxxxxx"
```

#### 小宇宙播客

```bash
python scripts/pipeline.py --input "https://www.xiaoyuzhoufm.com/episode/xxxxx"
```

#### 抖音视频

```bash
python scripts/pipeline.py --input "https://www.douyin.com/video/xxxxx"
```

#### 小红书视频

```bash
python scripts/pipeline.py --input "https://www.xiaohongshu.com/explore/xxxxx"
```

### 1.3 处理网页文章

```bash
python scripts/pipeline.py --input "https://mp.weixin.qq.com/s/xxxxx"
```

网页文章会直接用 trafilatura 抽取正文，跳过 ASR，速度很快。

### 1.4 处理本地文件

```bash
python scripts/pipeline.py --input "D:\videos\meeting.mp4"
python scripts/pipeline.py --input "/home/user/audio/podcast.mp3"
```

### 1.5 指定标题

```bash
python scripts/pipeline.py \
  --input "https://www.youtube.com/watch?v=xxxxx" \
  --title "AI Agent 架构深度解析"
```

### 1.6 查看输出

提纯稿默认保存到 `./output/` 目录，文件名为标题或视频标题：

```bash
ls output/
# AI Agent 架构深度解析.md
```

### 1.7 完整参数

```bash
python scripts/pipeline.py --help

# 参数说明：
# --input          输入源（URL 或本地文件路径）【必填】
# --title          素材标题（可选）
# --output-dir     输出目录（默认 ./output）
# --temp-dir       临时文件目录（默认 ./tmp）
# --asr-engine     ASR 引擎（默认 funasr，可选 faster-whisper）
# --asr-model      ASR 模型（默认 medium）
# --asr-device     ASR 设备（默认 cpu）
# --asr-compute-type  ASR 计算类型（默认 int8）
# --llm-model      LLM 模型（默认 glm-4.7）
# --llm-fallback   LLM 降级模型（默认 glm-4.5-air）
# --deliver-to-feishu  交付到飞书文档（Phase 2）
# --feishu-user-id     飞书用户 ID（默认读 FEISHU_USER_ID）
# --feishu-folder-token  飞书文件夹 token（可选）
# --verbose        详细日志
```

---

## 二、Phase 2：飞书文档交付

### 2.1 前置条件

1. 在飞书开放平台创建企业自建应用（参考 [installation.md](installation.md) 第三章）
2. 在 `.env` 中配置飞书凭据：
   ```bash
   FEISHU_APP_ID=cli_xxxxx
   FEISHU_APP_SECRET=xxxxxx
   FEISHU_USER_ID=your_openid   # 协作者授权目标
   # FEISHU_FOLDER_TOKEN=xxxxxx # 可选，指定文档创建文件夹
   ```
3. 应用权限开通：
   - `docx:document`（文档读写）
   - `drive:drive`（云空间读写）
   - `drive:permission`（权限管理）

### 2.2 触发飞书交付

在原有命令后加 `--deliver-to-feishu`：

```bash
# 网页文章
python scripts/pipeline.py \
  --input "https://mp.weixin.qq.com/s/xxxxx" \
  --deliver-to-feishu

# 视频链接
python scripts/pipeline.py \
  --input "https://www.bilibili.com/video/BVxxxxx" \
  --title "Hermes vs CodeX" \
  --deliver-to-feishu

# 本地文件
python scripts/pipeline.py \
  --input "D:\meetings\weekly.mp4" \
  --deliver-to-feishu \
  --feishu-user-id "ou_xxxxxxxxxxxx"
```

### 2.3 输出说明

成功后会同时输出本地 Markdown 和飞书文档链接：

```
============================================================
处理成功！
  标题: Hermes vs CodeX
  平台: bilibili
  提纯稿: ./output/Hermes vs CodeX.md
  飞书文档: https://feishu.cn/docx/xxxxxxxxxxxx
  协作者权限: 已授权
============================================================
```

### 2.4 权限降级策略

- 优先授权 `FEISHU_USER_ID` 为协作者（`full_access` 权限）
- 协作者授权失败时，自动降级为设置公开访问（本企业可阅读）
- 若均未配置 `FEISHU_USER_ID`，直接设置为公开访问

### 2.5 单独使用交付模块

如果已有 Markdown 文件，可单独调用交付：

```bash
python scripts/deliver_feishu.py \
  --input "./output/文章标题.md" \
  --title "文章标题" \
  --user-id "ou_xxxxxxxxxxxx"
```

---

## 三、单独使用各模块

### 3.1 仅下载视频

```bash
python scripts/download.py --url "https://www.youtube.com/watch?v=xxxxx"
```

### 3.2 仅转录本地音频

```bash
# 验证文件
python scripts/transcribe.py --input "audio.mp3" --check-only

# 仅转码
python scripts/transcribe.py --input "audio.mp3" --transcode-only

# 完整转录
python scripts/transcribe.py --input "audio.mp3" --model medium
```

### 3.3 仅抽取网页正文

```bash
python scripts/extract_web.py --url "https://example.com/article"
```

### 3.4 仅提纯文本

```bash
python scripts/refine.py \
  --input "raw_transcript.txt" \
  --title "视频标题" \
  --model glm-4.7
```

---

## 四、典型使用场景

### 场景 1：看到好的 YouTube 技术演讲，想快速阅读

```bash
python scripts/pipeline.py \
  --input "https://www.youtube.com/watch?v=xxxxx" \
  --title "Hermes Agent 深度解析"
```

输出：`output/Hermes Agent 深度解析.md`

### 场景 2：会议录制转文稿

```bash
python scripts/pipeline.py \
  --input "D:\meetings\weekly_standup.mp4" \
  --title "周会纪要-2026-07-16"
```

### 场景 3：微信公众号长文阅读

```bash
python scripts/pipeline.py \
  --input "https://mp.weixin.qq.com/s/xxxxx"
```

### 场景 4：抖音短视频内容提取

```bash
python scripts/pipeline.py \
  --input "https://www.douyin.com/video/xxxxx" \
  --title "抖音产品评测"
```

---

## 五、Phase 3：飞书 Bot 触发

### 5.1 前置条件

1. 完成飞书应用配置（参考 [installation.md](installation.md) 第四章）
2. **飞书应用添加机器人能力**：开放平台 → 应用能力 → 添加"机器人"
3. **订阅事件**：事件订阅 → 添加 `im.message.receive_v1`（接收消息）
4. **开通权限**：
   - `im:message`（消息读写）
   - `im:message.group_at_msg`（群聊 @ 消息）
   - `im:message.p2p_msg`（私聊消息）
   - `im:message:send_as_bot`（以机器人身份发消息）
5. **创建版本并发布**：版本管理 → 创建版本 → 管理员审核通过
6. 在 `.env` 中配置 Bot 权限策略（参考 `.env.example`）

### 5.2 启动 Bot

```bash
python scripts/bot.py
```

启动成功会看到：
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
[INFO] connected to wss://msg-frontier.feishu.cn/ws/v2?...
```

> Bot 进程会阻塞，保持 WebSocket 长连接。Ctrl+C 退出。

### 5.3 在飞书中使用

1. 在飞书中找到你的 Bot（搜索应用名）
2. 直接发送以下内容触发转录：

| 输入 | 类型 | 示例 |
|---|---|---|
| 网页链接 | URL | `https://mp.weixin.qq.com/s/xxxxx` |
| 视频链接 | URL | `https://www.bilibili.com/video/BVxxxxx` |
| YouTube | URL | `https://youtube.com/watch?v=xxxxx` |
| 小宇宙 | URL | `https://xiaoyuzhou.com/xxxxx` |
| 本地文件 | 路径 | `D:\\meetings\\weekly.mp4` |

3. Bot 会立即回复"⏳ 开始处理"消息
4. 处理完成后回复"✅ 处理成功"+飞书文档链接

### 5.4 支持的命令

| 命令 | 作用 |
|---|---|
| `/help` | 显示使用帮助 |
| `/status` | 查看任务队列状态 |

### 5.5 群聊使用

在群聊中需要 **@机器人** 后发送链接：
```
@转录Bot https://www.bilibili.com/video/BVxxxxx
```

群聊策略需设为 `open`（`FEISHU_GROUP_POLICY=open`）。

### 5.6 权限控制

默认 `FEISHU_ALLOW_ALL_USERS=true`（所有飞书用户可用）。收紧访问：

```bash
# .env
FEISHU_ALLOW_ALL_USERS=false
FEISHU_ADMIN_IDS=ou_用户1,ou_用户2  # 白名单 open_id
```

### 5.7 架构说明

```
飞书消息 ──→ lark-oapi WebSocket 长连接（出站，无需公网 IP）
              ↓
        bot.py 接收消息事件（3 秒内返回 ack）
              ↓
        解析 URL/路径/命令
              ↓
        TaskProcessor 异步队列（独立线程）
              ↓
        MediaTranscriberPipeline.process()
              ↓
        回复飞书消息（REST API）
```

**关键设计**：
- **WebSocket 长连接**：lark-oapi 内置，无需公网 IP，本地直接跑
- **异步处理**：飞书要求 3 秒内响应，pipeline 用独立线程处理，不阻塞消息接收
- **任务队列**：多任务串行执行，避免并发导致 ASR/LLM 资源争抢
- **失败降级**：pipeline 失败不影响 Bot 主进程，错误消息回传飞书

---

## 六、输出示例

### 提纯稿格式

```markdown
# Hermes Agent 深度解析

> 来源: YouTube  时长: 1800 秒

## 一、Hermes Agent 的核心定位

Hermes Agent 是 Nous Research 开源的**自进化 AI Agent 框架**，核心口号是"与你一起成长的 Agent"。

与传统 Agent"被动接收指令、机械执行"不同，它内置完整的学习闭环——**不仅能完成任务，更能从经验中沉淀能力**。

### 1.1 自进化学习闭环

完成复杂任务后，Hermes 会自动执行四个动作：

- **自动抽象方法论**：将成功工作流封装为可复用 Skill
- **持续迭代优化**：基于反馈改进已有 Skill
- ...

## 二、技术架构

...
```

---

## 六、性能参考

### ASR 转录速度（CPU，medium 模型，int8 量化）

| 音频时长 | 转录耗时 | 备注 |
|---|---|---|
| 5 分钟 | ~4 分钟 | 短视频 |
| 30 分钟 | ~25 分钟 | 播客单集 |
| 1 小时 | ~50 分钟 | 长播客 |
| 2 小时 | ~100 分钟 | 长会议 |

### LLM 提纯速度

| 文本长度 | 耗时 | 备注 |
|---|---|---|
| 5000 字 | ~10 秒 | 单段 |
| 20000 字 | ~40 秒 | 4 段 + 合并 |
| 50000 字 | ~2 分钟 | 10 段 + 合并 |

### 网页文章抽取速度

| 页面类型 | 耗时 |
|---|---|
| 普通博客 | ~2 秒 |
| 微信公众号 | ~3 秒 |
| 知乎长文 | ~3 秒 |

---

## 八、进阶用法

### 8.1 升级 ASR 模型提升准确率

```bash
# 用 large-v3 模型（需要更多内存和时间）
python scripts/pipeline.py \
  --input "audio.mp3" \
  --asr-model large-v3 \
  --asr-compute-type int8
```

### 8.2 切换 LLM 后端

```bash
# 用 OpenRouter
export OPENROUTER_API_KEY="sk-or-xxx"
python scripts/pipeline.py \
  --input "video.mp4" \
  --llm-model "anthropic/claude-sonnet-4-6"
```

### 8.3 自定义提纯 Prompt

编辑 `scripts/refine.py` 中的 `REFINE_SYSTEM_PROMPT` 常量，调整提纯规则。

### 8.4 批量处理

```bash
# Windows PowerShell
Get-ChildItem D:\videos\*.mp4 | ForEach-Object {
    python scripts/pipeline.py --input $_.FullName
}

# Linux/macOS
for f in /home/user/videos/*.mp4; do
    python scripts/pipeline.py --input "$f"
done
```
