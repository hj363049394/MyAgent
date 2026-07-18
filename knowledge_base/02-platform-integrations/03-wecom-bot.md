# 企业微信 AI Bot 对接（两种模式对比）

> 资料来源：Hermes Agent 安装教程：对接企业微信 AI Bot（CSDN，2026-04-23 / 2026-07-12）
> 原文链接：https://blog.csdn.net/u013084266/article/details/160452040
>
> 本文档聚焦企业微信对接的两种模式选型与配置细节。Hermes Agent 安装、LLM 配置等通用步骤请参考 `01-hermes-agent/03-hermes-agent-installation.md`。

---

## 一、两种企业微信模式对比

Hermes 内置了 **两种** 企业微信对接模式：

|  | AI Bot 模式（推荐入门） | 自建应用回调模式 |
|---|---|---|
| 适配器 | `WeComAdapter` (wecom.py) | `WecomCallbackAdapter` (wecom_callback.py) |
| 连接方式 | WebSocket 长连接 | HTTP 回调（企业微信 POST 到你的服务器） |
| 公网 IP | **不需要** | **需要** |
| 配置参数 | `WECOM_BOT_ID` + `WECOM_SECRET` | `WECOM_CALLBACK_CORP_ID` + `WECOM_CALLBACK_CORP_SECRET` + `AGENT_ID` + `TOKEN` + `ENCODING_AES_KEY` |
| 适用场景 | 快速上手，个人或小团队 | 企业级，需要更多自定义控制 |
| 创建位置 | 管理后台 → AI 助手 | 管理后台 → 自建应用 |

---

## 二、模式 A：AI Bot 模式（WebSocket，推荐）

### 2.1 在企业微信管理后台创建 AI Bot

1. 登录 [企业微信管理后台](https://work.weixin.qq.com/wework_admin/frame)
2. 进入 **应用管理** → **AI 助手**（或搜索「AI Bot」）
3. 创建一个新的 AI Bot
4. 记录下 **Bot ID** 和 **Secret**

### 2.2 配置连接参数

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
# ~/.hermes/config.yaml
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

### 2.3 验证配置

```bash
hermes doctor
```

检查输出中 WeCom 部分是否显示配置正确。

### 2.4 启动网关

```bash
# 确保在项目目录且虚拟环境已激活
source venv/bin/activate

# 启动网关
hermes gateway
```

`hermes gateway` 会以交互式菜单启动，你可以选择前台运行或安装为后台服务。

启动成功后，日志中应看到类似：

```
[WeCom] Connected via WebSocket to wss://openws.work.weixin.qq.com
[WeCom] Authentication successful
```

然后在企业微信中找到你的 AI Bot，发送消息即可对话。

---

## 三、模式 B：自建应用回调模式（HTTP，需公网 IP）

如果需要使用自建应用回调模式（适合企业级、需要更多自定义控制），在 `.env` 中配置：

```bash
WECOM_CALLBACK_CORP_ID=你的企业ID
WECOM_CALLBACK_CORP_SECRET=你的应用Secret
WECOM_CALLBACK_AGENT_ID=应用AgentId
WECOM_CALLBACK_TOKEN=接收消息的Token
WECOM_CALLBACK_ENCODING_AES_KEY=消息加解密密钥
WECOM_CALLBACK_HOST=0.0.0.0
WECOM_CALLBACK_PORT=8645
```

### 关键差异
- 企业微信会将消息以 HTTP POST 方式推送到你的服务器
- 需要公网 IP 和端口映射
- 消息使用 AES 加解密，需要 `ENCODING_AES_KEY`
- 适合需要自定义路由、鉴权、日志的企业级场景

---

## 四、启动相关坑与解决方案

### 坑 1：`hermes gateway start` 报错找不到 systemd 服务

**现象**：
```
Failed to start hermes-gateway.service: Unit hermes-gateway.service not found.
subprocess.CalledProcessError: Command '['systemctl', '--user', 'start', 'hermes-gateway']' returned non-zero exit status 5.
```

**原因**：`hermes gateway start` 会尝试通过 systemd 管理后台服务，但首次使用时服务单元尚未安装。

**解决**：直接使用 `hermes gateway` 启动即可。如果确实需要 systemd 后台服务，先运行 `hermes gateway install` 安装服务单元，再使用 `hermes gateway start`。

### 坑 2：SSH 远程后台启动 gateway 失败

**现象**：`hermes gateway run` 是阻塞进程；用 `setsid + &` 在 SSH exec_command 里会随父进程一起死。

**解决**：用 Python Popen + `start_new_session=True`：

```python
# /tmp/spawn_gw.py
import os, subprocess
env = os.environ.copy()
env["LANG"] = "C.UTF-8"
env["LC_ALL"] = "C.UTF-8"
env["PATH"] = f"/root/.local/bin:{env.get('PATH','')}"
log = open("/tmp/gateway.log", "wb")
subprocess.Popen(
    ["/root/.hermes/hermes-agent/venv/bin/hermes", "gateway", "run", "--accept-hooks"],
    cwd="/root", env=env,
    stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
    start_new_session=True,
)
```

```bash
python3 /tmp/spawn_gw.py
```

---

## 五、快捷启动脚本

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

## 六、运维命令速查

| 命令 | 用途 |
|---|---|
| `hermes gateway` | 启动消息网关（推荐） |
| `hermes gateway run` | 前台运行网关（等效 `hermes gateway`） |
| `hermes gateway start` | 后台启动网关（需先 install，依赖 systemd） |
| `hermes gateway install` | 安装为 systemd 后台服务 |
| `hermes gateway setup` | 交互式配置消息平台 |
| `hermes gateway status` | 查看网关状态 |
| `hermes doctor` | 诊断安装问题 |

---

## 七、选型建议

| 场景 | 推荐模式 | 理由 |
|---|---|---|
| 个人开发 / 小团队 / 快速验证 | **AI Bot 模式** | 无需公网 IP，配置简单，5 分钟跑通 |
| 企业级生产 / 需要自定义路由鉴权 | **自建应用回调模式** | 可控性强，但需公网 IP 和运维成本 |
| 已有公网服务器 / 需要多 Bot 实例 | 自建应用回调模式 | 适合规模化部署 |

> **关键经验**：WebSocket 模式 > Webhook 模式 —— 不需要公网 IP/端口映射，国内直连 `wss://openws.work.weixin.qq.com`，省心省运维成本。
