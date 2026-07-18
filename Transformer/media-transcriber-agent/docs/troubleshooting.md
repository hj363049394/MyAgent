# 常见坑与排查

> 本文档汇总 media-transcriber Agent 开发和使用过程中的常见问题与解决方案。
> 参考小D 第 10 节 + 知识库踩坑经验。

---

## 一、小D 总结的 6 大坑（必须规避）

### 坑 1：只复制提示词，不复制工具链

**现象**：Agent 说话像转录助手，但实际不能下载、转录、创建文档。

**根因**：只复制了 system-prompt.md，没有安装 yt-dlp、faster-whisper、lark-cli 等工具。

**解决**：必须完整安装工具栈，参考 [installation.md](installation.md)。提示词只是大脑，工具才是手脚。

---

### 坑 2：把提纯做成摘要

**现象**：输出变成"核心要点 1、要点 2、要点 3..."，丢失了原意和论证链。

**根因**：LLM 默认行为是"总结"，没有强约束"不要摘要"。

**解决**：
- `refine.py` 的 `REFINE_SYSTEM_PROMPT` 已明确"不是摘要"
- 如果仍出现，在 Prompt 中增加正反示例
- 降低 temperature 到 0.3（减少"创造性"压缩）

---

### 坑 3：不做术语校正

**现象**：长音频里的公司名、人名、产品名被 ASR 识别错（如"字节跳动"→"字节挑动"）。

**根因**：ASR 模型对专有名词识别准确率有限。

**解决**：
- 在 Prompt 中强调"修正常见 ASR 错词"
- 如果有 shownotes/简介，作为 metadata 传给 LLM 参考
- 升级到 large-v3 模型提升准确率
- 后续可维护一个"术语词典"做预处理替换

---

### 坑 4：飞书权限没闭环

**现象**：Bot 创建了文档，但用户打不开，提示无权限。

**根因**：Bot 创建的文档默认只有 Bot 自己有权限，用户不在协作者列表。

**解决**：
- 用 lark-drive skill 自动添加本人为协作者（可管理权限）
- 配置 `config.yaml` 的 `auto_permission: true` + `default_owner`
- 如果自动授权失败，回复"文档已创建，但协作者权限未完成，请手动添加"
- **交付成功的标准是用户能打开，不是文档创建完**

---

### 坑 5：Markdown 导入格式乱

**现象**：飞书文档目录断裂、层级混乱、加粗不生效。

**根因**：Markdown 格式不规范（未闭合的 `**`、标题层级跳跃等）。

**解决**：
- 创建后用 `lark-cli fetch outline` 验证目录结构
- 必要时重建格式
- `refine.py` 输出前做格式校验

---

### 坑 6：泄露凭据

**现象**：app secret、token、cookie 出现在聊天或文档中。

**根因**：配置不当或 Agent 误输出。

**解决**：
- **绝对不要**在聊天中粘贴凭据
- **绝对不要**把 token、secret 写入文档
- `.env` 文件不提交 git（已在 .gitignore）
- Agent 的 SOUL.md 明确"不泄露凭据"为禁止行为

---

## 二、LLM 相关坑（参考知识库飞书文档）

### 坑 7：`provider: "custom"` 导致 401

**现象**：调用智谱 GLM 报 HTTP 401 Unauthorized。

**根因**：`config.yaml` 中 `provider: "custom"` 会强制走本地推理服务器路径，用 `no-key-required` placeholder，**忽略所有 API key**。

**解决**：必须用 `provider: "zai"`：

```yaml
model:
  default: "glm-4.7"
  provider: "zai"            # ← 不是 "custom"
  base_url: "https://open.bigmodel.cn/api/paas/v4"
```

---

### 坑 8：智谱模型名带 `-Flash` 后缀报错

**现象**：bigmodel 报"模型不存在 (1211)"。

**根因**：模型名拼写错误，如 `glm-4.7-Flash`，端点上不存在。

**解决**：用正确的模型名，不带 `-Flash` 后缀：

| 用途 | 正确模型名 |
|---|---|
| 文本主模型 | `glm-4.7` |
| 视觉模型 | `glm-4.6v` |
| 轻量兜底 | `glm-4.5-air` |

用 `curl /v1/models` 探测真实模型列表。

---

### 坑 9：智谱限流（1305/1302 错误）

**现象**：bigmodel 报"限速 (1305)"或"账号 RPM 限速 (1302)"。

**根因**：触发了模型级或账号级限流。

**解决**：
- `refine.py` 已实现自动降级：限流时切换到 `glm-4.5-air`
- 等待几分钟重试
- 免费档限速更宽松，付费档 RPM 更高

---

## 三、ASR 相关坑

### 坑 10：faster-whisper 安装失败

**现象**：`pip install faster-whisper` 报 CTranslate2 编译错误。

**解决**：
```bash
pip install --upgrade pip setuptools wheel
pip install faster-whisper
```

---

### 坑 11：ASR 模型下载慢

**现象**：首次运行 ASR 卡在模型下载（HuggingFace 国内访问慢）。

**解决**：
```bash
# 设置 HF 镜像
export HF_ENDPOINT=https://hf-mirror.com
# Windows PowerShell:
$env:HF_ENDPOINT="https://hf-mirror.com"
```

---

### 坑 12：ffmpeg 找不到

**现象**：`FileNotFoundError: ffmpeg` 或转码失败。

**解决**：
- 检查 ffmpeg 是否在 PATH：`where ffmpeg` / `which ffmpeg`
- 没装则安装：`winget install ffmpeg` 或 `pip install imageio-ffmpeg`
- `download.py` 的 `get_ffmpeg_path()` 会自动降级到 imageio-ffmpeg

---

### 坑 13：音频过长导致转录超时

**现象**：2 小时以上的音频，CPU 转录要 3-4 小时。

**解决**：
- 后台异步执行
- 提示用户"音频较长，预计 X 分钟"
- 考虑分段处理（按静音段切分）
- 升级到 GPU + large-v3（Phase 2 服务器部署）

---

## 四、下载相关坑

### 坑 14：yt-dlp 下载 YouTube 失败

**现象**：下载 YouTube 视频报错。

**解决**：
- YouTube 需要代理，配置 `HTTPS_PROXY`
- 更新 yt-dlp：`pip install -U yt-dlp`（YouTube 经常更新反爬）

---

### 坑 15：抖音/小红书链接无法下载

**现象**：yt-dlp 报"无法提取视频"。

**解决**：
- 用完整的分享链接（不要用短链的预览）
- 抖音：从 App 分享 → 复制链接 → 粘贴
- 小红书：从 App 分享 → 复制链接 → 粘贴
- 更新 yt-dlp 到最新版

---

### 坑 16：B站视频需要登录

**现象**：部分 B站视频（如会员专享）下载失败。

**解决**：
- 用 yt-dlp 的 `--cookies` 参数传入浏览器 cookie
- 或下载后发本地文件处理

---

## 五、网页抽取相关坑

### 坑 17：trafilatura 抽取为空

**现象**：网页文章抽取返回空内容。

**根因**：页面是 JS 渲染（SPA），trafilatura 拿不到动态内容。

**解决**：
- 尝试用浏览器截图 + 视觉模型 `glm-4.6v` 识别
- 或提示用户复制正文文本直接发给我
- 微信公众号文章一般可以直接抽取

---

### 坑 18：抽取内容过短

**现象**：抽取内容 < 100 字，视为失败。

**根因**：可能是登录墙、付费墙、或反爬。

**解决**：
- 提示用户"该内容需要登录，请提供 cookie 或复制正文"

---

## 六、飞书 Bot 相关坑（Phase 3+）

### 坑 19：飞书 Bot 收不到消息

**现象**：发消息给 Bot 没有响应。

**根因**：缺少事件订阅权限。

**解决**：
- 飞书开发者后台 → 事件订阅 → 添加 `im.message.receive_v1`
- 权限管理 → 开通 `im:message`、`im:message.p2p_msg` 等

---

### 坑 20：飞书 Bot 拒收所有消息

**现象**：Bot 回复"未授权"或直接不响应。

**根因**：默认 pairing/allowlist policy。

**解决**：
```bash
FEISHU_ALLOW_ALL_USERS=true
GATEWAY_ALLOW_ALL_USERS=true
FEISHU_DM_POLICY=open
FEISHU_GROUP_POLICY=open
```

---

### 坑 21：lark_oapi ModuleNotFoundError

**现象**：Hermes Gateway 启动报 `ModuleNotFoundError: lark_oapi`。

**根因**：hermes 默认 deps 不包含飞书 SDK。

**解决**：
```bash
pip install lark_oapi aiohttp websockets
```

---

### 坑 22：SSH 远程后台启动 Gateway 失败

**现象**：`setsid + &` 启动的 Gateway 随 SSH 会话退出而死。

**解决**：用 Python Popen + `start_new_session=True`：

```python
import subprocess
subprocess.Popen(
    ["hermes", "gateway", "run"],
    start_new_session=True,
    stdin=subprocess.DEVNULL,
    stdout=open("/tmp/gateway.log", "wb"),
    stderr=subprocess.STDOUT,
)
```

---

### 坑 23：飞书交付报 401 Unauthorized（Phase 2）

**现象**：`--deliver-to-feishu` 时报 `获取 token 失败: app_id or app_secret invalid`。

**根因**：`FEISHU_APP_ID` 或 `FEISHU_APP_SECRET` 配置错误，或应用未发布。

**解决**：
1. 确认 `.env` 中 App ID 格式为 `cli_xxxxx`（不是数字 ID）
2. 确认 App Secret 完整无空格
3. 飞书开放平台 → 版本管理 → 确认应用已创建版本并审核通过

---

### 坑 24：飞书文档创建成功但内容为空（Phase 2）

**现象**：文档创建成功但打开看不到内容，日志显示 `文档内容写入失败`。

**根因**：应用缺少 `docx:document` 权限，或 Markdown 含特殊字符导致 blocks 转换失败。

**解决**：
1. 飞书开放平台 → 权限管理 → 确认已开通 `docx:document`
2. 确认应用版本已重新发布（权限变更需重新发版）
3. 查看 `deliver_feishu.py` 的 `_markdown_to_blocks()` 是否对特殊字符做了转义

---

### 坑 25：飞书协作者授权失败（Phase 2）

**现象**：文档创建成功但 `协作者权限: 未完成`。

**根因**：
- `FEISHU_USER_ID` 不是 openid 格式（`ou_xxxxx`）
- 或应用缺少 `drive:permission` 权限

**解决**：
1. 确认 `FEISHU_USER_ID` 是 openid（`ou_` 开头），不是 user_id 或 union_id
2. 权限管理开通 `drive:permission`
3. 若仍失败，系统会自动降级为设置公开访问（`tenant_readable`），文档仍可访问

---

### 坑 26：`provider: "custom"` 导致 401（方式 B 陷阱）

**现象**：切换到方式 B（OpenAI 兼容）后仍报 401。

**根因**：`config.yaml` 中 `provider` 误写为 `"custom"`，custom 会强制走本地推理服务器路径，用 `no-key-required` placeholder，**忽略所有 API key**。

**解决**：必须用 `provider: "auto"`：

```yaml
model:
  default: "glm-4.7"
  provider: "auto"              # ← 方式 B 用 auto（不是 custom）
  base_url: "https://open.bigmodel.cn/api/paas/v4"
```

环境变量用：
```bash
OPENAI_API_KEY=你的智谱Key
OPENAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4
```

---

### 坑 27：Bot 启动后看不到 `connected to wss://`（Phase 3）

**现象**：`python scripts/bot.py` 启动后卡住，没有 WebSocket 连接日志。

**根因**：
1. 飞书应用未添加"机器人"能力
2. 未订阅 `im.message.receive_v1` 事件
3. 应用未发布（版本管理未创建版本或未审核通过）
4. App ID / App Secret 配置错误

**解决**：
1. 飞书开放平台 → 应用能力 → 确认已添加"机器人"
2. 事件订阅 → 确认已添加 `im.message.receive_v1`
3. 版本管理 → 创建版本 → 确认已审核通过
4. 检查 `.env` 中 `FEISHU_APP_ID` / `FEISHU_APP_SECRET` 是否正确

---

### 坑 28：Bot 收不到消息（Phase 3）

**现象**：WebSocket 已连接，但在飞书发消息给 Bot 没反应。

**根因**：
1. 权限不足：缺 `im:message.p2p_msg`（私聊）或 `im:message.group_at_msg`（群聊）
2. 权限策略：`FEISHU_ALLOW_ALL_USERS=false` 但用户不在白名单
3. 群聊没 @ 机器人
4. 事件订阅被禁用

**解决**：
1. 飞书开放平台 → 权限管理 → 确认已开通 `im:message.p2p_msg` 等
2. `.env` 中设 `FEISHU_ALLOW_ALL_USERS=true`（测试阶段）
3. 群聊中必须 @ 机器人后再发链接
4. 事件订阅 → 确认 `im.message.receive_v1` 处于启用状态

---

### 坑 29：Bot 回复"⏳ 开始处理"后再无响应（Phase 3）

**现象**：Bot 收到消息并回复了"开始处理"，但长时间没有最终结果。

**根因**：
1. pipeline 处理耗时较长（视频 ASR + LLM 提纯可能 15-30 分钟）
2. 工作线程崩溃（看 bot.py 日志）
3. GLM API 限流（1302/1305 错误码）

**解决**：
1. 查看终端日志确认工作线程在运行
2. 发送 `/status` 命令查看任务队列状态
3. 确认 GLM API Key 未触发限流（看 refine.py 日志）
4. 视频处理建议先用短视频（< 5 分钟）测试

---

### 坑 30：Bot 处理消息报 3 秒超时（Phase 3）

**现象**：飞书消息被重复处理，日志看到同一消息多次触发。

**根因**：飞书 WebSocket 要求 3 秒内响应，否则触发重推机制。如果 `handle_message` 同步执行耗时操作（如直接调 pipeline），会超时。

**解决**：bot.py 已用 `TaskProcessor` 异步队列解决此问题。如仍超时：
1. 检查 `handle_message` 是否有阻塞操作
2. 确认 `processor.submit()` 是非阻塞的（只是入队）
3. 网络延迟也可能导致 3 秒超时，检查网络连接

---

### 坑 31：B 站下载报 412 Precondition Failed

**现象**：
```
ERROR: [BiliBili] xxx: Unable to download JSON metadata:
HTTP Error 412: Precondition Failed
```

**根因**：B 站近期升级了反爬机制，对未登录的 API 请求返回 412。即使 yt-dlp 版本最新（2026.03.17），未携带登录 cookies 的请求仍会被拦截。

**解决方案**：配置 B 站登录 cookies，让 yt-dlp 伪装为已登录浏览器。

#### 方式 1：导出 Netscape 格式 cookies 文件（推荐，最稳定）

**步骤 1：安装浏览器扩展**

- Chrome/Edge：安装 [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/)
- Firefox：安装 [cookies.txt](https://addons.mozilla.org/firefox/addon/cookies-txt/)

**步骤 2：登录 B 站**

在浏览器中访问 https://www.bilibili.com 并登录你的账号。

**步骤 3：导出 cookies**

点击扩展图标 → 选择"Export" → 保存为 `cookies.txt`。

**步骤 4：放置 cookies 文件**

将 `cookies.txt` 放到项目目录下，建议路径：`config/cookies.txt`

**步骤 5：配置 .env**

```bash
# .env
COOKIES_FILE=./config/cookies.txt
```

**步骤 6：重启 Bot**

```bash
python scripts/bot.py
```

#### 方式 2：从浏览器直接读取（备选，可能失效）

```bash
# .env
COOKIES_FROM_BROWSER=chrome  # 或 edge / firefox
```

> 注意：新版 Chrome（80+）对 cookies 做了加密，yt-dlp 可能无法读取。如果报错 "unable to extract cookies"，请用方式 1。

#### 验证

```bash
# 直接用 download.py 测试
python scripts/download.py --url "https://www.bilibili.com/video/BVxxxxx"
```

成功输出应包含 "下载完成"，失败会显示 412 错误。

#### 注意事项

- cookies 有时效性，过期需重新导出（通常 30 天有效）
- 不要把 cookies.txt 提交到 git（已在 .gitignore 中排除）
- cookies 包含登录凭据，注意保密
- 如仍失败，尝试更新 yt-dlp：`pip install -U yt-dlp`

---

## 七、排查流程速查

遇到问题时，按以下顺序排查：

```
1. 检查环境变量
   - OPENAI_API_KEY / GLM_API_KEY 是否设置？
   - FEISHU_APP_ID / FEISHU_APP_SECRET（Phase 2）是否设置？
   - HTTPS_PROXY 是否需要（YouTube）？

2. 检查依赖
   - python -c "import yt_dlp, faster_whisper, trafilatura, openai, requests"
   - ffmpeg -version

3. 检查网络
   - 能否访问 open.bigmodel.cn？
   - 能否访问 open.feishu.cn？（Phase 2）
   - 能否访问视频平台？

4. 单独测试各模块
   - python scripts/download.py --url "..."
   - python scripts/transcribe.py --input "..." --check-only
   - python scripts/extract_web.py --url "..."
   - python scripts/refine.py --input "..." --title "..."

5. 查看日志
   - 加 --verbose 参数看详细日志
   - 检查 ./logs/ 目录

6. 验证 LLM 连通
   - python -c "from openai import OpenAI; ..."
```
