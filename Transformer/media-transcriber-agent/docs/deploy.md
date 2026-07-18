# 服务器部署指南

> 在阿里云服务器（4C8G / Alibaba Cloud Linux 4 / 上海）上以 Docker 方式部署媒体转录 Agent。
> 与寺庙应用独立共存，互不影响。
>
> 本地 Windows 开发仍用 venv 模式，参考 [startup.md](startup.md)。

---

## 一、前置条件

### 1.1 服务器要求

- **规格**：4 核 CPU / 8 GB 内存（已与寺庙应用共存验证）
- **系统**：Alibaba Cloud Linux 4 LTS 64 位（兼容 CentOS 8 / RHEL 8）
- **网络**：出站访问飞书 API、GLM API、视频网站
- **磁盘**：剩余空间 ≥ 10 GB（模型 + 依赖 + 缓存）

### 1.2 已安装组件

- Docker Engine（≥ 20.10）
- Docker Compose v2（`docker compose` 命令）
- Git

> 寺庙应用已用 Docker 部署，Docker Engine 应已安装。如未安装：
> ```bash
> # Alibaba Cloud Linux 4
> dnf install -y docker
> systemctl enable --now docker
> # docker compose v2 已包含在 docker-compose-plugin
> dnf install -y docker-compose-plugin
> ```

### 1.3 准备好的文件

- [ ] GitHub 仓库访问权限：`https://github.com/hj363049394/MyAgent`
- [ ] `.env` 配置文件内容（从本地复制）
- [ ] `config/*_cookies.txt`（bilibili、douyin、xiaohongshu、youtube，按需）
- [ ] `FEISHU_FOLDER_TOKEN`（云上建议重新创建一个文件夹，或沿用本地的 `M0qrfYBjelR9PgdrQdhc4mWEn9c`）

---

## 二、部署步骤

### 2.1 拉取代码

```bash
# 创建工作目录
sudo mkdir -p /opt/transcriber-agent
sudo chown $USER:$USER /opt/transcriber-agent
cd /opt/transcriber-agent

# 拉取代码（仓库是 public 直接 clone，private 则需配置 SSH key 或 token）
git clone https://github.com/hj363049394/MyAgent.git tmp-repo
# 仅取需要的子目录
cp -r tmp-repo/Transformer/media-transcriber-agent/* .
cp -r tmp-repo/Transformer/media-transcriber-agent/.dockerignore .
rm -rf tmp-repo

# 确认目录结构
ls -la
# 应看到：Dockerfile、docker-compose.yml、scripts/、prompts/、requirements.txt 等
```

### 2.2 配置环境变量

```bash
cd /opt/transcriber-agent

# 创建 .env（从本地复制内容，或重新填写）
cat > .env <<'EOF'
# 飞书应用凭据（必填）
FEISHU_APP_ID=cli_xxxxx
FEISHU_APP_SECRET=xxxxxx

# 你的飞书 open_id（必填，用于文档协作者授权）
FEISHU_USER_ID=ou_xxxxx

# 飞书文档保存目录的 folder_token（云上建议重新创建）
FEISHU_FOLDER_TOKEN=M0qrfYBjelR9PgdrQdhc4mWEn9c

# GLM API Key
OPENAI_API_KEY=xxxxxx

# Bot 权限策略
FEISHU_ALLOW_ALL_USERS=true
FEISHU_DM_POLICY=open
FEISHU_GROUP_POLICY=open
EOF

chmod 600 .env  # 仅 root 可读
```

### 2.3 上传 cookies 文件

在**本地 Windows** 执行：

```powershell
# 从本地上传到服务器
scp -r d:\trae_projects\Agent\Transformer\media-transcriber-agent\config\* root@<服务器IP>:/opt/transcriber-agent/config/
```

在**服务器**上设置权限：

```bash
cd /opt/transcriber-agent
chmod 600 config/*_cookies.txt
ls -la config/
```

### 2.4 构建并启动

```bash
cd /opt/transcriber-agent

# 构建镜像（首次约 5-10 分钟，主要耗时在下载 torch）
docker compose build

# 后台启动
docker compose up -d

# 查看启动日志（确认 WebSocket 连接成功）
docker compose logs -f bot
```

预期日志：

```
============================================================
音视频转录整理 Bot 启动
  App ID: cli_xxxxx
  User ID: ou_xxxxx
  Folder Token: M0qrfYBjelR9PgdrQdhc4mWEn9c
  允许所有用户: True
  群聊策略: open
  私聊策略: open
============================================================
正在连接飞书 WebSocket...
[INFO] Lark: connected to wss://msg-frontier.feishu.cn/ws/v2?...
```

看到 `connected to wss://` 即启动成功。按 Ctrl+C 退出日志查看（不会停止容器）。

### 2.5 验证

```bash
# 1. 容器状态
docker compose ps
# 应看到 transcriber-bot 状态为 Up

# 2. 资源占用
docker stats transcriber-bot --no-stream
# 应看到 CPU < 5%，内存 1-2 GB（模型未加载时）

# 3. 健康检查
docker inspect --format='{{.State.Health.Status}}' transcriber-bot
# 应为 healthy

# 4. 飞书发链接测试
#    在飞书中给 Bot 发一个视频链接，确认能正常处理
```

---

## 三、日常运维

### 3.1 查看日志

```bash
# 实时日志
docker compose logs -f bot

# 最近 100 行
docker compose logs --tail 100 bot

# 容器内文件日志
docker compose exec bot cat /app/tmp/bot.log | tail -50
```

### 3.2 重启服务

```bash
# 重启（更新代码后）
docker compose restart bot

# 完全重建（更新依赖后）
docker compose down
docker compose build
docker compose up -d
```

### 3.3 更新代码

```bash
cd /opt/transcriber-agent

# 拉取最新代码
git pull origin main  # 如果是直接 clone 的
# 或重新 scp 上传 scripts/ 目录

# 重建并重启
docker compose up -d --build
```

### 3.4 资源监控

```bash
# 实时监控容器资源
docker stats transcriber-bot

# 查看寺庙应用 + Agent 总体占用
docker stats

# 系统整体资源
top
free -h
df -h
```

### 3.5 查看下载/输出文件

```bash
# 下载的临时视频/音频
ls -lh /opt/transcriber-agent/tmp/downloads/

# 提纯稿
ls -lh /opt/transcriber-agent/output/

# 清理临时文件（磁盘紧张时）
rm -rf /opt/transcriber-agent/tmp/downloads/*
```

---

## 四、开机自启

Docker 容器配置了 `restart: always`，服务器重启后会自动启动。但需确保 Docker 服务自启：

```bash
sudo systemctl enable docker
sudo systemctl enable containerd
```

---

## 五、配置变更流程

修改 `.env` 或 cookies 后，**必须重启容器**才生效：

```bash
cd /opt/transcriber-agent
docker compose restart bot
```

修改代码（`scripts/` 下）后，**需要重建镜像**：

```bash
cd /opt/transcriber-agent
docker compose up -d --build
```

---

## 六、常见问题

### Q1：构建镜像时下载 torch 很慢？

**原因**：PyPI 在国外，torch 包大（~200 MB）。

**解决**：使用国内镜像源。修改 Dockerfile 中的 pip install：

```dockerfile
# 替换为
RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple \
    --index-url https://download.pytorch.org/whl/cpu torch torchaudio \
    && pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
```

### Q2：首次启动时 ASR 模型下载很慢？

**原因**：FunASR 的 SenseVoiceSmall 模型从 modelscope 下载（~500 MB）。

**解决**：模型下载后会缓存在 `modelscope_cache` volume 中，下次启动秒加载。首次耐心等 5-10 分钟即可。

### Q3：容器启动后立即退出？

**排查步骤**：

```bash
# 查看退出日志
docker compose logs bot

# 常见原因：
# 1. .env 缺失或字段错误 → 检查 .env 文件
# 2. cookies 文件缺失 → 检查 config/ 目录
# 3. 飞书凭据错误 → 检查 FEISHU_APP_ID/SECRET
```

### Q4：与寺庙应用资源冲突？

**症状**：Agent 处理任务时寺庙应用响应慢。

**排查**：

```bash
# 实时查看各容器 CPU 占用
docker stats

# 如果 Agent 超出 2.5 核限制，调整 docker-compose.yml:
# deploy.resources.limits.cpus: '2.0'  # 降到 2 核
```

### Q5：cookies 过期？

**症状**：抖音/B 站下载失败，提示需要登录。

**解决**：

1. 在本地 Windows 用浏览器登录平台
2. 用 "Get cookies.txt" 扩展导出 Netscape 格式 cookies
3. scp 上传到服务器：

```powershell
scp douyin_cookies.txt root@<IP>:/opt/transcriber-agent/config/
```

4. 重启容器：

```bash
docker compose restart bot
```

### Q6：飞书文档创建失败 403？

**原因**：`FEISHU_FOLDER_TOKEN` 指向的文件夹 Bot 没有权限。

**解决**：在服务器上用 Bot 凭据创建自己的文件夹：

```bash
# 进容器执行
docker compose exec bot python /app/tmp/create_folder.py
# 输出的 folder_token 填到 .env，重启容器
```

---

## 七、与本地 Windows 版本的差异

| 维度 | 本地 Windows | 服务器 Linux |
|------|-------------|--------------|
| 运行方式 | venv + `python scripts/bot.py` | Docker 容器 |
| 启动命令 | `venv\Scripts\python.exe scripts\bot.py` | `docker compose up -d` |
| 日志查看 | 终端 stdout + `tmp\bot.log` | `docker compose logs -f bot` |
| 配置变更 | 改 `.env` 后重启 Python 进程 | 改 `.env` 后 `docker compose restart bot` |
| 代码更新 | 直接改文件，重启进程 | 改文件后 `docker compose up -d --build` |
| ffmpeg | imageio-ffmpeg 兜底 | 系统装 ffmpeg（Dockerfile 内） |
| 模型缓存 | `C:\Users\xxx\.cache\modelscope` | Docker volume `modelscope_cache` |

**代码完全一致**，无需维护两套分支。

---

## 八、回滚方案

如服务器部署出问题，可立即切回本地 Windows 运行：

1. 本地 Windows `venv\Scripts\python.exe scripts\bot.py` 启动
2. 飞书 Bot 同一应用，本地启动会自动顶替云上的 WebSocket 连接
3. 服务器上 `docker compose down` 停止容器

---

## 九、快速参考

```bash
# 部署（首次）
cd /opt/transcriber-agent
docker compose build
docker compose up -d
docker compose logs -f bot

# 日常运维
docker compose ps                          # 状态
docker compose logs -f bot                 # 日志
docker compose restart bot                 # 重启
docker stats transcriber-bot               # 资源

# 更新代码
git pull
docker compose up -d --build

# 完全卸载
docker compose down -v                     # 停止并删除 volume
rm -rf /opt/transcriber-agent
```
