# 媒体转录 Agent Dockerfile
# 双兼容设计：Linux 服务器 Docker 部署用；本地 Windows 仍用 venv 模式
#
# 构建命令（在项目根目录）：
#   docker build -t transcriber-bot .
#
# 运行命令（用 docker-compose，见 docker-compose.yml）：
#   docker compose up -d

FROM python:3.11-slim

# 时区设置为上海（避免日志时间错乱）
ENV TZ=Asia/Shanghai \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装系统依赖：
# - ffmpeg: ASR 转码必需
# - curl: 健康检查
# - ca-certificates: HTTPS 证书
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        curl \
        ca-certificates \
        tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先复制 requirements.txt，利用 Docker 层缓存
COPY requirements.txt .

# 安装 Python 依赖
# torch 用 CPU 版本（服务器无 GPU）
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch torchaudio \
    && pip install -r requirements.txt

# 复制项目代码
COPY scripts/ ./scripts/
COPY prompts/ ./prompts/

# 创建必要的运行时目录（运行时挂载 volume 覆盖）
RUN mkdir -p /app/config /app/output /app/tmp /root/.cache/modelscope

# 健康检查：Bot 是长连接进程，用 python 进程存活判断
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD pgrep -f "python.*bot.py" > /dev/null || exit 1

# 启动 Bot
CMD ["python", "scripts/bot.py"]
