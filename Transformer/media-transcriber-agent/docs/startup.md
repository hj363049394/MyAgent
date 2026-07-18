# 启动与使用指南

> 日常使用 media-transcriber Agent 的完整流程。
> 首次部署请先阅读 [installation.md](installation.md) 完成安装和飞书应用配置。

---

## 一、日常启动流程（3 步）

### 1. 打开终端，进入项目目录

```powershell
cd d:\trae_projects\Agent\Transformer\media-transcriber-agent
```

### 2. 启动 Bot（用 venv 的 Python）

**必须用 venv 的 Python**，不要直接用系统 `python`，否则会缺少 `imageio-ffmpeg`（ASR 转录需要）等依赖。

```powershell
# 方式 A：直接用 venv 的 python（推荐，最省事）
venv\Scripts\python.exe scripts\bot.py

# 方式 B：先激活 venv 再启动
venv\Scripts\activate
python scripts/bot.py
```

> **坑点**：如果直接 `python scripts\bot.py` 而不激活 venv，可能用到系统 Python，导致：
> - B 站链接可以处理（走字幕路径，不需要 ffmpeg）
> - 抖音链接失败（走 ASR 路径，需要 ffmpeg，而系统 Python 没装 imageio-ffmpeg）
>
> 所以**务必用 venv 的 Python**。

看到以下日志说明启动成功（飞书 WebSocket 已连接）：

```
============================================================
音视频转录整理 Bot 启动
  App ID: cli_xxxxx
  User ID: ou_xxxxx
  Folder Token: (未配置，文档保存到根目录)
  允许所有用户: True
  群聊策略: open
  私聊策略: open
============================================================
正在连接飞书 WebSocket...
[INFO] connected to wss://msg-frontier.feishu.cn/ws/v2?...
```

> **注意**：Bot 进程会阻塞保持长连接，**不要关闭终端**。Ctrl+C 退出。

---

## 二、在飞书中使用

### 2.1 触发转录

直接在飞书里找到你的 Bot（私聊或在群里 @它），发送链接：

| 输入类型 | 示例 |
|---------|------|
| B站视频 | `https://www.bilibili.com/video/BVxxxxx` |
| YouTube | `https://youtube.com/watch?v=xxxxx` |
| 微信公众号 | `https://mp.weixin.qq.com/s/xxxxx` |
| 小宇宙播客 | `https://xiaoyuzhou.com/xxxxx` |
| 本地文件路径 | `D:\videos\meeting.mp4` |

### 2.2 支持的命令

| 命令 | 作用 |
|------|------|
| `/help` | 显示使用帮助 |
| `/status` | 查看任务队列状态 |
| `/progress` | 查看正在处理任务的实时进度 + 最近 20 行日志 |

### 2.3 处理流程

1. 发送链接 → Bot 立即回复"⏳ 开始处理"
2. 后台执行：下载 → 字幕/ASR → LLM 提纯 → 飞书文档交付
3. 完成后回复"✅ 处理成功"+ 飞书文档链接

### 2.4 群聊使用

在群聊中需要 **@机器人** 后发送链接：

```
@转录Bot https://www.bilibili.com/video/BVxxxxx
```

群聊策略需设为 `open`（`.env` 中 `FEISHU_GROUP_POLICY=open`）。

---

## 三、输出位置

| 输出 | 路径 |
|------|------|
| 飞书文档 | Bot 应用根目录（默认）或指定文件夹（需配置 `FEISHU_FOLDER_TOKEN`） |
| 本地 Markdown 稿 | `output\<标题>.md` |
| Bot 运行日志 | `tmp\bot.log`（可用 `/progress` 命令实时查看末尾 20 行） |

---

## 四、停止 Bot

在终端按 `Ctrl+C`，Bot 会断开 WebSocket 并退出。

---

## 五、配置改动后需重启

以下情况**必须重启 Bot 才能生效**（配置只在启动时加载一次）：

- 修改了 `.env` 文件（如调整 `FEISHU_USER_ID`、`FEISHU_FOLDER_TOKEN`、权限策略）
- 修改了 `scripts/bot.py`、`scripts/refine.py` 等代码文件

**重启步骤**：

```powershell
# 终端中按 Ctrl+C 停止当前 Bot
# 然后重新执行（务必用 venv 的 python）
venv\Scripts\python.exe scripts\bot.py
```

---

## 六、`.env` 关键配置说明

```bash
# 飞书应用凭据（必填）
FEISHU_APP_ID=cli_xxxxx
FEISHU_APP_SECRET=xxxxxx

# 你的飞书 open_id（必填，用于文档协作者授权）
FEISHU_USER_ID=ou_xxxxxxxxxxxxxxxx

# 飞书文档保存目录的 folder_token（可选）
# FEISHU_FOLDER_TOKEN=xxxxxx

# Bot 权限策略
FEISHU_ALLOW_ALL_USERS=true
FEISHU_DM_POLICY=open
FEISHU_GROUP_POLICY=open

# 管理员白名单（可选，逗号分隔的 open_id）
# FEISHU_ADMIN_IDS=ou_user1,ou_user2
```

### 6.1 关于 FEISHU_USER_ID（重要澄清）

**填你自己的飞书 open_id**（`ou_` 开头），**不是**机器人 ID。

| ID 类型 | 用途 | 是否填到 FEISHU_USER_ID |
|---------|------|------------------------|
| 用户的 open_id（`ou_xxx`） | 授权你为文档协作者（full_access） | ✅ 填这个 |
| 机器人的 app_id（`cli_xxx`） | Bot 身份标识 | ❌ 不填这里 |
| 用户的 user_id / union_id | 企业维度/开发者维度的标识 | ❌ 不填这里 |

**关键**：飞书里同一个人在不同应用下有不同的 `open_id`。你从飞书个人主页复制的 ID 可能是 `user_id`，而 Bot 看到你的 `open_id` 是另一串。这是正常的，不需要改。

**如何获取你在这个 Bot 应用下的 open_id**：
- 启动 Bot 后给它发任意消息，查看 `tmp\bot.log`，日志中 `sender=ou_xxxxx` 就是你的 open_id

### 6.2 关于 FEISHU_FOLDER_TOKEN（403 问题）

`FEISHU_FOLDER_TOKEN` 指定文档创建到哪个文件夹。如果配置后出现 `403 Forbidden`，**原因不是 FEISHU_USER_ID 错误**，而是 **Bot 应用没有该文件夹的写入权限**。

**飞书 API 校验逻辑**：
- 创建文档带 `folder_token` 时，校验 **Bot 应用本身**对该文件夹的权限
- 跟 `FEISHU_USER_ID` 无关（它只影响文档创建后的协作者授权）

**两种 ID 的作用对比**：

| 配置项 | 作用 | 影响范围 |
|--------|------|----------|
| `FEISHU_USER_ID` | 文档创建后，把**你**加为协作者 | 仅授权，不影响创建位置 |
| `FEISHU_FOLDER_TOKEN` | 指定文档**创建到哪个文件夹** | 需要 Bot 有该文件夹的写入权限 |

**让文档能放到指定目录的正确做法**：

飞书云空间共享面板默认搜索的是**用户**（通讯录中的人），搜不到 Bot 应用，所以推荐用方案 A。

**方案 A（推荐）：用 Bot API 自己创建文件夹**

Bot 用自己的身份创建文件夹，自动拥有完整权限，不需要在共享面板搜索添加。

```powershell
cd d:\trae_projects\Agent\Transformer\media-transcriber-agent
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

然后重启 Bot 即可。文档会自动创建到该文件夹下。

> 脚本默认文件夹名是 "Bot 转录文稿"，可编辑 `tmp/create_folder.py` 中的 `FOLDER_NAME` 修改。

**方案 B：在飞书云空间把 Bot 加为现有文件夹的协作者**

如果想用已有的文件夹（不是 Bot 创建的）：

1. 打开目标文件夹的飞书云空间链接（如 `https://my.feishu.cn/drive/folder/<token>`）
2. 右上角点击"共享"按钮
3. 在"添加协作者"搜索框中，**切换到"应用"tab**（默认是"用户"tab，搜不到 Bot）
4. 搜索 Bot 应用名称
5. 添加为协作者，权限选 **"可编辑"**
6. 把文件夹 token 填到 `.env` 的 `FEISHU_FOLDER_TOKEN`
7. 重启 Bot

> 注意：如果搜索不到 Bot 应用，说明应用未添加"机器人"能力或未发布版本，请先在飞书开放平台完成配置。

**方案 C（临时）：不指定文件夹**

注释掉 `.env` 中 `FEISHU_FOLDER_TOKEN`，文档创建到 Bot 根目录（已验证可用）。

---

## 七、命令行替代方式（无需常驻 Bot）

如果不想常驻 Bot 进程，也可以直接用命令行处理单个链接（同样会交付到飞书）：

```powershell
cd d:\trae_projects\Agent\Transformer\media-transcriber-agent
venv\Scripts\activate

# 网页文章 + 飞书交付
python scripts/pipeline.py --input "https://mp.weixin.qq.com/s/xxxxx" --deliver-to-feishu

# 视频链接 + 飞书交付
python scripts/pipeline.py --input "https://www.bilibili.com/video/BVxxxxx" --deliver-to-feishu

# 本地文件 + 飞书交付
python scripts/pipeline.py --input "D:\videos\meeting.mp4" --deliver-to-feishu
```

更多命令行参数见 [usage.md](usage.md)。

---

## 八、常见问题

### Q1：Bot 启动后日志不写入 `tmp/bot.log`？

**原因**：PowerShell 的 `Set-Content` 写入 BOM 头可能干扰 Python `FileHandler` 缓冲。

**解决**：直接查看终端 stdout 输出即可（Bot 同时输出到 stdout 和文件）。

### Q2：发送链接后没有响应？

**排查步骤**：
1. 检查终端是否还在运行 Bot 进程（未 Ctrl+C 退出）
2. 检查日志是否出现"收到消息"记录
3. 如果没收到消息，检查飞书开放平台事件订阅是否配置 `im.message.receive_v1`
4. 如果收到消息但没处理，发送 `/status` 查看队列状态

### Q3：处理失败提示 403？

- 如果是**创建文档**失败 → Bot 没有目标文件夹权限，参考第 6.2 节
- 如果是**添加协作者**失败 → `FEISHU_USER_ID` 配置错误，参考第 6.1 节

### Q4：处理速度慢？

正常耗时参考：
- 短视频（<10 分钟）：2-5 分钟
- 中等视频（10-30 分钟）：3-8 分钟
- 长视频（>30 分钟）：5-15 分钟

如果异常慢，检查：
- LLM 提纯是否触发 429 限流（日志出现"降级到 glm-4.5-air"）→ 等 1 分钟再发新任务
- 网络是否稳定（GLM API 长尾重试）

### Q5：如何让文档保存到指定文件夹？

参考第 6.2 节。核心是**把 Bot 加为该文件夹的协作者**，而不是改 `FEISHU_USER_ID`。

---

## 九、快速参考

```powershell
# 日常启动（3 行）
cd d:\trae_projects\Agent\Transformer\media-transcriber-agent
venv\Scripts\activate
python scripts/bot.py

# 在飞书中发送链接即可触发
# 命令：/help /status /progress
```
