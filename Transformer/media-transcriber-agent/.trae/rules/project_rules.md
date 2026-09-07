# 音视频转录 Agent 项目记忆

## 项目位置
- 项目目录：`D:\My Project\trae_projects\Agent\Transformer\media-transcriber-agent`
- 父级 Agent 合集：`D:\My Project\trae_projects\Agent`
  - 子项目：knowledge_base / SelectionAssistant / Transformer（本转录 Agent）

## 线上仓库
- 仓库：`https://github.com/hj363049394/MyAgent`
- 项目路径：`Transformer/media-transcriber-agent`
- 默认分支：main

## 功能概述
飞书 Bot 触发音视频/网页内容转录为文稿：
- 发送链接：微信公众号、B站、YouTube、小红书、抖音、小宇宙、西瓜视频
- 发送本地文件路径
- 直接发送录音文件 / 语音消息（file/audio 消息类型，自动下载并转录）
- 命令：/help、/status、/progress
- 交付：生成 Markdown 文稿 + 推送飞书文档（含 AI 总结高亮块）

## 本地运行
- 启动：`python scripts/bot.py`（需在 venv 环境）
- 安装依赖：`pip install -r requirements.txt`
- 配置：`.env`（FEISHU_APP_ID / FEISHU_APP_SECRET / FEISHU_USER_ID / FEISHU_FOLDER_TOKEN）
- 说明：当前本机 Python 通过 `C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe` 运行，venv 重建后使用
