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

# 切换 Debian apt 源到阿里云镜像（国内服务器加速）
# python:3.11-slim 基于 Debian Trixie，默认源 deb.debian.org 国内访问慢
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null \
    || sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list 2>/dev/null \
    || true

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

# 配置 pip 国内镜像源（清华 TUNA），加速 Python 依赖安装
RUN mkdir -p /etc/pip \
    && cat > /etc/pip/pip.conf <<'EOF'
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
trusted-host = pypi.tuna.tsinghua.edu.cn
timeout = 120
retries = 5
EOF

# 先复制 requirements.txt，利用 Docker 层缓存
COPY requirements.txt .

# 安装 Python 依赖
# torch 单独从清华 PyTorch 镜像安装 CPU 版本（服务器无 GPU）
# 其他依赖从清华 PyPI 镜像安装
RUN pip install --index-url https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/pytorch/whl/cpu torch torchaudio \
    || pip install --index-url https://download.pytorch.org/whl/cpu torch torchaudio \
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
