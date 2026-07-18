# Hermes Agent 安装部署与企业微信 AI Bot 对接教程

> 资料来源：Hermes Agent 安装教程：对接企业微信 AI Bot（CSDN，2026-04-23 原创 / 2026-07-12 推荐）
> 原文链接：https://blog.csdn.net/u013084266/article/details/160452040
>
> 本教程聚焦于 **企业微信 AI Bot** 对接方式，使用 WebSocket 长连接，**无需公网 IP**。

---

## 一、Hermes Agent 是什么

[Hermes Agent](https://github.com/NousResearch/hermes-agent) 是 Nous Research 开发的开源 AI Agent，具有以下特点：

- **自学习闭环**：从经验中自动创建技能，使用中持续改进，跨会话记忆搜索
- **多平台对接**：Telegram、Discord、Slack、WhatsApp、Signal、企业微信、飞书、钉钉等
- **多模型支持**：OpenRouter（200+ 模型）、Anthropic Claude、OpenAI、智谱 GLM、Kimi、MiniMax 等，一条命令切换
- **可运行在任何地方**：本地机器、$5 VPS、Docker、云服务

---

## 二、环境要求

| 项目 | 要求 |
|---|---|
| 操作系统 | Linux（推荐 Ubuntu 20.04+）、macOS、WSL2 |
| Python | 3.11 或更高版本 |
| 网络 | 需要访问 PyPI 和 GitHub（国内建议配好镜像） |
| 企业微信 | 企业微信管理后台管理员权限，需创建 AI Bot |

### 环境检查

```bash
python3 --version   # 确认 Python >= 3.11
which uv            # 检查 uv 是否安装（推荐的包管理器）
```

如果 `uv` 未安装：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
```

---

## 三、第一步：克隆代码

### 方式 A：浅克隆（推荐，下载快）

仓库比较大（含文档和资源文件），浅克隆只下载最新代码，节省时间和空间：

```bash
cd ~
git clone --depth 1 https://github.com/NousResearch/hermes-agent.git
cd hermes-agent
```

### 方式 B：官方一键安装脚本

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
```

> **坑 #1**：完整克隆（`git clone` 不加 `--depth 1`）在国内网络环境下可能非常慢，仓库超过 80MB。**建议使用浅克隆**。

---

## 四、第二步：创建 Python 虚拟环境并安装依赖

```bash
cd ~/hermes-agent

# 创建虚拟环境
uv venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖（包含消息平台、cron 定时任务、开发工具等）
uv pip install -e ".[messaging,cron,cli,pty,mcp,dev]"
```

> **坑 #2**：PyPI 在国内经常超时（`operation timed out`）。**解决方案**：使用清华镜像源。
>
> **坑 #3**：阿里云镜像源版本不全，会报 `No solution found` 错误。**不要用阿里云镜像**，用清华源。

```bash
uv pip install -e ".[messaging,cron,cli,pty,mcp,dev]" \
  -i https://pypi.tuna.tsinghua.edu.cn/simple/ \
  --trusted-host pypi.tuna.tsinghua.edu.cn
```

### 验证安装成功

```bash
python -c "from gateway.platforms.wecom import check_wecom_requirements; print('OK:', check_wecom_requirements())"
# 输出：OK: True
```

---

## 五、第三步：配置 LLM 模型

Hermes 需要一个 LLM 提供商来驱动对话。支持多种方式：

### 方式 A：使用智谱 GLM（国内推荐）

编辑项目根目录下的 `.env` 文件：

```bash
# .env
GLM_API_KEY=你的智谱API密钥
```

获取密钥：访问 [open.bigmodel.cn](https://open.bigmodel.cn/) 注册并创建 API Key。

然后编辑 `~/.hermes/config.yaml`，设置模型和提供商：

```yaml
model:
  default: glm-5-turbo      # 或 glm-4-plus、glm-4-flash 等
  provider: zai             # 智谱 GLM 的 provider 名
```

### 方式 B：使用 OpenRouter（国际推荐，200+ 模型）

```bash
# .env
OPENROUTER_API_KEY=sk-or-你的密钥
```

```yaml
# ~/.hermes/config.yaml
model:
  default: anthropic/claude-sonnet-4-6
  provider: auto
  base_url: https://openrouter.ai/api/v1
```

获取密钥：访问 [openrouter.ai/keys](https://openrouter.ai/keys)。

### 方式 C：使用 Anthropic Claude 直连

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-你的密钥
```

### 其他支持的提供商

| 提供商 | 环境变量 | 获取地址 |
|---|---|---|
| OpenAI | `OPENAI_API_KEY` | [platform.openai.com](https://platform.openai.com/) |
| Kimi/Moonshot | `KIMI_API_KEY` | [platform.kimi.ai](https://platform.kimi.ai/) |
| MiniMax | `MINIMAX_API_KEY` | [minimax.io](https://www.minimax.io/) |
| 小米 MiMo | `XIAOMI_API_KEY` | [platform.xiaomimimo.com](https://platform.xiaomimimo.com/) |

运行 `hermes model` 可以交互式选择模型。

---

## 六、第四步：配置企业微信 AI Bot

### 6.1 在企业微信管理后台创建 AI Bot

1. 登录 [企业微信管理后台](https://work.weixin.qq.com/wework_admin/frame)
2. 进入 **应用管理** → **AI 助手**（或搜索「AI Bot」）
3. 创建一个新的 AI Bot
4. 记录下 **Bot ID** 和 **Secret**

### 6.2 配置连接参数

在项目根目录的 `.env` 文件中添加：

```bash
# .env
WECOM_BOT_ID=你的Bot_ID
WECOM_SECRET=你的Secret
WECOM_HOME_CHANNEL=你的用户ID    # 可选，cron 定时任务的默认发送目标
```

WebSocket URL 默认是 `wss://openws.work.weixin.qq.com`，国内直连，无需修改。

> **注意**：也可以选择在 `~/.hermes/config.yaml` 中配置，效果相同。`.env` 中的值会覆盖 `config.yaml`，所以只需配置一处。

```yaml
platforms:
  wecom:
    enabled: true
    extra:
      bot_id: "你的Bot_ID"
      secret: "你的Secret"
      websocket_url: "wss://openws.work.weixin.qq.com"
      dm_policy: "open"        # 私聊策略：open（所有人可用）
      group_policy: "open"     # 群聊策略
```

### 6.3 验证配置

```bash
hermes doctor
```

检查输出中 WeCom 部分是否显示配置正确。

---

## 七、第五步：启动网关

```bash
# 确保在项目目录且虚拟环境已激活
source venv/bin/activate

# 启动网关
hermes gateway
```

`hermes gateway` 会以交互式菜单启动，你可以选择前台运行或安装为后台服务。

> **注意**：`hermes gateway start` 尝试通过 systemd 启动后台服务，在没有安装 systemd 服务单元的系统上会报错 `Unit hermes-gateway.service not found`。首次使用直接运行 `hermes gateway` 即可。

启动成功后，日志中应看到类似：

```
[WeCom] Connected via WebSocket to wss://openws.work.weixin.qq.com
[WeCom] Authentication successful
```

然后在企业微信中找到你的 AI Bot，发送消息即可对话。

### 快捷启动脚本

创建 `start.sh`：

```bash
#!/bin/bash
cd ~/hermes-agent
source venv/bin/activate
hermes gateway
```

```bash
chmod +x start.sh
./start.sh
```

---

## 八、遇到的问题与解决方案

### 问题 1：Git 克隆速度极慢

**现象**：`git clone` 下载到 70-80MB 后几乎停滞，等待超过 10 分钟未完成。

**原因**：仓库较大（含文档资源），GitHub 在国内直连不稳定。

**解决**：使用浅克隆 `git clone --depth 1`，只下载最新版本，速度提升数倍。

### 问题 2：PyPI 超时

**现象**：
```
error: Request failed after 3 retries
Caused by: Failed to fetch: `https://pypi.org/simple/yarl/`
Caused by: operation timed out
```

**解决**：使用清华镜像源：

```bash
uv pip install -e ".[messaging,...]" \
  -i https://pypi.tuna.tsinghua.edu.cn/simple/ \
  --trusted-host pypi.tuna.tsinghua.edu.cn
```

### 问题 3：阿里云镜像版本不全

**现象**：
```
No solution found when resolving dependencies:
  Because there are no versions of openai...
```

**原因**：阿里云 PyPI 镜像同步不完整，缺少 `openai>=2.21.0` 等新版本包。

**解决**：改用清华源，同步更及时。

### 问题 4：`hermes gateway start` 报错找不到 systemd 服务

**现象**：
```
Failed to start hermes-gateway.service: Unit hermes-gateway.service not found.
subprocess.CalledProcessError: Command '['systemctl', '--user', 'start', 'hermes-gateway']' returned non-zero exit status 5.
```

**原因**：`hermes gateway start` 会尝试通过 systemd 管理后台服务，但首次使用时服务单元尚未安装。

**解决**：直接使用 `hermes gateway` 启动即可。如果确实需要 systemd 后台服务，先运行 `hermes gateway install` 安装服务单元，再使用 `hermes gateway start`。

---

## 九、常用命令速查

| 命令 | 用途 |
|---|---|
| `hermes` | 启动 CLI 交互对话 |
| `hermes model` | 选择/切换 LLM 模型 |
| `hermes gateway` | 启动消息网关（推荐） |
| `hermes gateway run` | 前台运行网关（等效 `hermes gateway`） |
| `hermes gateway start` | 后台启动网关（需先 install，依赖 systemd） |
| `hermes gateway install` | 安装为 systemd 后台服务 |
| `hermes gateway setup` | 交互式配置消息平台 |
| `hermes gateway status` | 查看网关状态 |
| `hermes setup` | 完整设置向导 |
| `hermes doctor` | 诊断安装问题 |
| `hermes tools` | 管理工具集 |
| `hermes config set` | 设置单项配置 |
| `hermes skills` | 管理技能 |

---

## 十、附录：两种企业微信模式对比

Hermes 内置了 **两种** 企业微信对接模式：

|  | AI Bot 模式（本教程） | 自建应用回调模式 |
|---|---|---|
| 适配器 | `WeComAdapter` (wecom.py) | `WecomCallbackAdapter` (wecom_callback.py) |
| 连接方式 | WebSocket 长连接 | HTTP 回调（企业微信 POST 到你的服务器） |
| 公网 IP | **不需要** | **需要** |
| 配置参数 | `WECOM_BOT_ID` + `WECOM_SECRET` | `WECOM_CALLBACK_CORP_ID` + `WECOM_CALLBACK_CORP_SECRET` + `AGENT_ID` + `TOKEN` + `ENCODING_AES_KEY` |
| 适用场景 | 快速上手，个人或小团队 | 企业级，需要更多自定义控制 |
| 创建位置 | 管理后台 → AI 助手 | 管理后台 → 自建应用 |

如果需要使用自建应用回调模式，在 `.env` 中配置：

```bash
WECOM_CALLBACK_CORP_ID=你的企业ID
WECOM_CALLBACK_CORP_SECRET=你的应用Secret
WECOM_CALLBACK_AGENT_ID=应用AgentId
WECOM_CALLBACK_TOKEN=接收消息的Token
WECOM_CALLBACK_ENCODING_AES_KEY=消息加解密密钥
WECOM_CALLBACK_HOST=0.0.0.0
WECOM_CALLBACK_PORT=8645
```

---

## 参考链接

- 官方文档：[hermes-agent.nousresearch.com](https://hermes-agent.nousresearch.com/docs/)
- GitHub 仓库：[github.com/NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)
- Discord 社区：[discord.gg/NousResearch](https://discord.gg/NousResearch)
- 智谱 GLM API：[open.bigmodel.cn](https://open.bigmodel.cn/)
- OpenRouter：[openrouter.ai](https://openrouter.ai/)
- 企业微信管理后台：[work.weixin.qq.com](https://work.weixin.qq.com/wework_admin/frame)
