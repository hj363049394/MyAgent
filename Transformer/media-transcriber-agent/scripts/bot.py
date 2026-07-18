"""
飞书 Bot 触发器（Phase 3）

通过 lark-oapi WebSocket 长连接接收飞书消息，解析链接/命令，
异步调用 media-transcriber pipeline 处理，完成后回复飞书文档链接。

依赖：
    pip install lark-oapi

启动：
    python scripts/bot.py

环境变量（在 .env 中配置）：
    FEISHU_APP_ID         飞书应用 App ID
    FEISHU_APP_SECRET     飞书应用 App Secret
    FEISHU_USER_ID        协作者授权目标（ou_xxx）
    FEISHU_ALLOW_ALL_USERS  是否允许所有用户（true/false，默认 true）
    FEISHU_GROUP_POLICY   群聊策略（open/restrict，默认 open）
    FEISHU_DM_POLICY     私聊策略（open/restrict，默认 open）

使用：
    在飞书中找到 Bot，直接发送：
    - 链接：https://mp.weixin.qq.com/s/xxxxx
    - 视频链接：https://www.bilibili.com/video/BVxxxxx
    - 本地文件路径：D:\\meetings\\weekly.mp4
    - 命令 /help 查看帮助
    - 命令 /status 查看处理队列状态
"""
import os
import sys
import json
import re
import logging
import threading
import queue
import time
import base64
from typing import Optional, Dict, Any, List

# 将 scripts 目录加入 path（便于 import pipeline 模块）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import lark_oapi as lark
from lark_oapi.api.im.v1 import (
    CreateMessageRequest,
    CreateMessageRequestBody,
    PatchMessageRequest,
    PatchMessageRequestBody,
)

# 加载 .env
from pipeline import load_env_file

logger = logging.getLogger("bot")


# ============================================================
# 配置
# ============================================================
class BotConfig:
    """Bot 配置（从环境变量读取）"""

    APP_ID: str = os.environ.get("FEISHU_APP_ID", "")
    APP_SECRET: str = os.environ.get("FEISHU_APP_SECRET", "")
    USER_ID: str = os.environ.get("FEISHU_USER_ID", "")
    FOLDER_TOKEN: str = os.environ.get("FEISHU_FOLDER_TOKEN", "")
    ALLOW_ALL_USERS: bool = os.environ.get("FEISHU_ALLOW_ALL_USERS", "true").lower() == "true"
    GROUP_POLICY: str = os.environ.get("FEISHU_GROUP_POLICY", "open")
    DM_POLICY: str = os.environ.get("FEISHU_DM_POLICY", "open")
    # 管理员用户白名单（FEISHU_ADMIN_IDS 环境变量，逗号分隔）
    ADMIN_IDS: List[str] = [
        x.strip() for x in os.environ.get("FEISHU_ADMIN_IDS", "").split(",") if x.strip()
    ]

    @classmethod
    def reload(cls):
        """从环境变量重新加载"""
        cls.APP_ID = os.environ.get("FEISHU_APP_ID", "")
        cls.APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")
        cls.USER_ID = os.environ.get("FEISHU_USER_ID", "")
        cls.FOLDER_TOKEN = os.environ.get("FEISHU_FOLDER_TOKEN", "")
        cls.ALLOW_ALL_USERS = (
            os.environ.get("FEISHU_ALLOW_ALL_USERS", "true").lower() == "true"
        )
        cls.GROUP_POLICY = os.environ.get("FEISHU_GROUP_POLICY", "open")
        cls.DM_POLICY = os.environ.get("FEISHU_DM_POLICY", "open")
        cls.ADMIN_IDS = [
            x.strip()
            for x in os.environ.get("FEISHU_ADMIN_IDS", "").split(",")
            if x.strip()
        ]


# ============================================================
# URL/输入识别
# ============================================================
URL_PATTERN = re.compile(
    r"https?://[^\s<>\"]+", re.IGNORECASE
)
# 支持的平台关键词（用于提示用户）
SUPPORTED_PLATFORMS = {
    "mp.weixin.qq.com": "微信公众号",
    "bilibili.com": "B站",
    "youtube.com": "YouTube",
    "youtu.be": "YouTube",
    "xiaohongshu.com": "小红书",
    "douyin.com": "抖音",
    "ixigua.com": "西瓜视频",
    "xiaoyuzhou.com": "小宇宙",
}


def extract_urls(text: str) -> List[str]:
    """从文本中提取 URL"""
    return URL_PATTERN.findall(text)


def is_local_path(text: str) -> bool:
    """判断是否为本地文件路径"""
    text = text.strip()
    if not text:
        return False
    # Windows 路径（D:\... 或 D:/...）
    if re.match(r"^[A-Za-z]:[\\/]", text):
        return os.path.exists(text)
    # Unix 路径
    if text.startswith("/") or text.startswith("~/"):
        return os.path.exists(os.path.expanduser(text))
    return False


def detect_platform(url: str) -> str:
    """检测 URL 所属平台"""
    for domain, name in SUPPORTED_PLATFORMS.items():
        if domain in url:
            return name
    return "web"


# ============================================================
# 飞书 API 客户端（REST）
# ============================================================
class FeishuClient:
    """飞书 REST API 封装"""

    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.client = lark.Client.builder().app_id(app_id).app_secret(app_secret).build()
        logger.info("飞书 REST 客户端初始化完成")

    def send_message(
        self,
        receive_id: str,
        receive_id_type: str,
        text: str,
        reply_to_message_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        发送消息到飞书

        Args:
            receive_id: 接收者 ID（open_id / user_id / chat_id）
            receive_id_type: receive_id 类型（open_id / user_id / chat_id）
            text: 消息文本（纯文本）
            reply_to_message_id: 回复的消息 ID（可选，用于在话题中回复）

        Returns:
            message_id 或 None
        """
        # 飞书消息体使用 post 格式支持换行
        # 这里用 text 格式 + \\n 换行
        body = CreateMessageRequestBody.builder() \
            .receive_id(receive_id) \
            .msg_type("text") \
            .content(json.dumps({"text": text}))

        if reply_to_message_id:
            builder = CreateMessageRequest.builder() \
                .receive_id_type(receive_id_type) \
                .request_body(body.build())
            # 回复消息需要单独设置 reply_in_thread
        else:
            builder = CreateMessageRequest.builder() \
                .receive_id_type(receive_id_type) \
                .request_body(body.build())

        try:
            resp = self.client.im.v1.message.create(builder.build())
            if not resp.success():
                logger.error(
                    f"发送消息失败: code={resp.code}, msg={resp.msg}, log_id={resp.get_log_id()}"
                )
                return None
            return resp.data.message_id
        except Exception as e:
            logger.error(f"发送消息异常: {e}")
            return None

    def send_card(
        self, receive_id: str, receive_id_type: str, card_content: Dict[str, Any]
    ) -> Optional[str]:
        """发送交互式卡片消息"""
        body = CreateMessageRequestBody.builder() \
            .receive_id(receive_id) \
            .msg_type("interactive") \
            .content(json.dumps(card_content))

        request = CreateMessageRequest.builder() \
            .receive_id_type(receive_id_type) \
            .request_body(body.build())

        try:
            resp = self.client.im.v1.message.create(request.build())
            if not resp.success():
                logger.error(
                    f"发送卡片失败: code={resp.code}, msg={resp.msg}"
                )
                return None
            return resp.data.message_id
        except Exception as e:
            logger.error(f"发送卡片异常: {e}")
            return None

    def update_message(self, message_id: str, text: str) -> bool:
        """更新已发送的消息（用于进度更新）"""
        body = PatchMessageRequestBody.builder().content(
            json.dumps({"text": text})
        ).build()
        request = PatchMessageRequest.builder() \
            .message_id(message_id) \
            .request_body(body) \
            .build()

        try:
            resp = self.client.im.v1.message.patch(request)
            if not resp.success():
                logger.error(f"更新消息失败: code={resp.code}, msg={resp.msg}")
                return False
            return True
        except Exception as e:
            logger.error(f"更新消息异常: {e}")
            return False


# ============================================================
# 任务处理器（异步线程）
# ============================================================
class TaskProcessor:
    """
    异步任务处理器

    飞书 WebSocket 要求 3 秒内响应，所以 pipeline 必须异步执行。
    用队列+工作线程实现，避免阻塞 WebSocket 回调。
    """

    def __init__(self, feishu_client: FeishuClient):
        self.feishu_client = feishu_client
        self.task_queue: queue.Queue = queue.Queue()
        self.worker_thread: Optional[threading.Thread] = None
        self.running = False
        self.current_tasks: Dict[str, Dict[str, Any]] = {}  # task_id -> task info
        self._lock = threading.Lock()

    def start(self):
        """启动工作线程"""
        if self.running:
            return
        self.running = True
        self.worker_thread = threading.Thread(
            target=self._worker_loop, name="task-worker", daemon=True
        )
        self.worker_thread.start()
        logger.info("任务处理工作线程已启动")

    def stop(self):
        """停止工作线程"""
        self.running = False
        self.task_queue.put(None)  # 哨兵唤醒
        if self.worker_thread:
            self.worker_thread.join(timeout=5)

    def submit(
        self,
        task_id: str,
        input_source: str,
        receive_id: str,
        receive_id_type: str,
        reply_message_id: Optional[str] = None,
        title: Optional[str] = None,
        sender_open_id: Optional[str] = None,
    ):
        """提交任务到队列"""
        task = {
            "task_id": task_id,
            "input": input_source,
            "receive_id": receive_id,
            "receive_id_type": receive_id_type,
            "reply_message_id": reply_message_id,
            "title": title,
            "status": "queued",
            "submitted_at": time.time(),
            "sender_open_id": sender_open_id,
        }
        with self._lock:
            self.current_tasks[task_id] = task
        self.task_queue.put(task)
        logger.info(f"任务已入队: {task_id} (input={input_source[:60]})")

    def get_status(self) -> Dict[str, Any]:
        """获取任务队列状态"""
        with self._lock:
            return {
                "queue_size": self.task_queue.qsize(),
                "current_tasks": dict(self.current_tasks),
            }

    def _worker_loop(self):
        """工作线程主循环"""
        logger.info("工作线程循环启动")
        while self.running:
            try:
                task = self.task_queue.get(timeout=1)
                if task is None:
                    break
                self._process_task(task)
                self.task_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"工作线程异常: {e}", exc_info=True)
        logger.info("工作线程循环结束")

    def _process_task(self, task: Dict[str, Any]):
        """处理单个任务（调用 pipeline）"""
        task_id = task["task_id"]
        receive_id = task["receive_id"]
        receive_id_type = task["receive_id_type"]
        input_source = task["input"]

        logger.info(f"开始处理任务 {task_id}: {input_source}")

        # 更新状态
        with self._lock:
            task["status"] = "processing"
            task["started_at"] = time.time()

        # 发送"开始处理"消息
        self.feishu_client.send_message(
            receive_id,
            receive_id_type,
            f"⏳ 开始处理：{input_source[:80]}\n处理时间约 1-20 分钟，请耐心等待...",
        )

        try:
            # 延迟 import，避免循环依赖和启动慢
            from pipeline import MediaTranscriberPipeline

            # 优先使用消息发送者的 openid 作为协作者授权目标，
            # 这样多用户场景下每人都能拿到自己文档的权限
            collaborator_id = task.get("sender_open_id") or BotConfig.USER_ID
            logger.info(
                f"任务 {task_id} 协作者授权目标: {collaborator_id} "
                f"(sender={task.get('sender_open_id')}, fallback USER_ID={BotConfig.USER_ID})"
            )
            pipeline = MediaTranscriberPipeline(
                deliver_to_feishu_enabled=True,
                feishu_user_id=collaborator_id,
                feishu_folder_token=BotConfig.FOLDER_TOKEN or None,
            )

            result = pipeline.process(input_source, title=task.get("title"))

            if result["success"]:
                # 成功：回复飞书文档链接
                lines = [
                    f"✅ 处理成功！",
                    f"",
                    f"📌 标题：{result['title']}",
                    f"🔖 来源：{result['platform']}",
                ]
                if result.get("feishu_url"):
                    lines.append(f"📄 飞书文档：{result['feishu_url']}")
                    perm = (
                        "已授权"
                        if result.get("feishu_permission")
                        else "未完成（请打开文档链接手动申请权限）"
                    )
                    lines.append(f"🔑 协作者权限：{perm}")
                lines.append(f"💾 本地稿：{result['output_path']}")

                self.feishu_client.send_message(
                    receive_id, receive_id_type, "\n".join(lines)
                )
            else:
                # 失败
                err = result.get("error", "未知错误")
                self.feishu_client.send_message(
                    receive_id,
                    receive_id_type,
                    f"❌ 处理失败：{err}\n\n输入：{input_source[:80]}",
                )
                if result.get("output_path"):
                    self.feishu_client.send_message(
                        receive_id,
                        receive_id_type,
                        f"（本地提纯稿已保存：{result['output_path']}）",
                    )

            # 更新任务状态
            with self._lock:
                task["status"] = "done" if result["success"] else "failed"
                task["finished_at"] = time.time()
                task["result"] = result

        except Exception as e:
            logger.error(f"任务 {task_id} 处理异常: {e}", exc_info=True)
            self.feishu_client.send_message(
                receive_id, receive_id_type, f"❌ 处理异常：{e}"
            )
            with self._lock:
                task["status"] = "error"
                task["error"] = str(e)
                task["finished_at"] = time.time()


# ============================================================
# 消息处理
# ============================================================
def handle_message(data: lark.im.v1.P2ImMessageReceiveV1, processor: TaskProcessor):
    """处理接收到的飞书消息"""
    try:
        event = data.event
        msg = event.message
        sender = event.sender

        # 提取关键字段
        message_id = msg.message_id
        chat_id = msg.chat_id
        chat_type = msg.chat_type  # p2p / group
        msg_type = msg.message_type
        sender_id_obj = sender.sender_id
        sender_open_id = sender_id_obj.open_id
        sender_user_id = sender_id_obj.user_id
        sender_union_id = sender_id_obj.union_id

        # 只处理文本消息
        if msg_type != "text":
            logger.info(f"跳过非文本消息: type={msg_type}")
            return

        # 解析消息内容
        try:
            content = json.loads(msg.content)
            text = content.get("text", "").strip()
        except Exception:
            logger.warning(f"消息内容解析失败: {msg.content}")
            return

        logger.info(
            f"收到消息: chat_id={chat_id}, type={chat_type}, "
            f"sender={sender_open_id}, text={text[:100]}"
        )

        # 权限校验
        if not _check_permission(chat_type, sender_open_id):
            logger.warning(f"权限不足，拒绝消息: sender={sender_open_id}")
            return

        # 解析命令或链接
        receive_id = chat_id
        receive_id_type = "chat_id"

        # 处理命令
        if text.startswith("/"):
            _handle_command(
                text, receive_id, receive_id_type, processor, sender_open_id
            )
            return

        # 处理 URL
        urls = extract_urls(text)
        if urls:
            # 只处理第一个 URL
            url = urls[0]
            task_id = f"task_{int(time.time())}_{sender_open_id[-6:]}"
            processor.submit(
                task_id=task_id,
                input_source=url,
                receive_id=receive_id,
                receive_id_type=receive_id_type,
                reply_message_id=message_id,
                sender_open_id=sender_open_id,
            )
            return

        # 处理本地文件路径
        if is_local_path(text):
            task_id = f"task_{int(time.time())}_{sender_open_id[-6:]}"
            processor.submit(
                task_id=task_id,
                input_source=text,
                receive_id=receive_id,
                receive_id_type=receive_id_type,
                reply_message_id=message_id,
                sender_open_id=sender_open_id,
            )
            return

        # 无法识别
        _send_help(receive_id, receive_id_type, processor.feishu_client)

    except Exception as e:
        logger.error(f"处理消息异常: {e}", exc_info=True)


def _check_permission(chat_type: str, sender_open_id: str) -> bool:
    """权限校验"""
    # 群聊策略
    if chat_type == "group" and BotConfig.GROUP_POLICY != "open":
        return False
    # 私聊策略
    if chat_type == "p2p" and BotConfig.DM_POLICY != "open":
        return False
    # 允许所有用户
    if BotConfig.ALLOW_ALL_USERS:
        return True
    # 管理员白名单
    if sender_open_id in BotConfig.ADMIN_IDS:
        return True
    # 协作者自己
    if sender_open_id == BotConfig.USER_ID:
        return True
    return False


def _handle_command(
    text: str,
    receive_id: str,
    receive_id_type: str,
    processor: TaskProcessor,
    sender_open_id: str,
):
    """处理斜杠命令"""
    client = processor.feishu_client
    cmd = text.lower().split()[0] if text.split() else ""

    if cmd == "/help":
        help_text = (
            "📖 使用说明\n\n"
            "直接发送以下内容即可触发转录：\n"
            "• 网页链接：https://mp.weixin.qq.com/s/xxx\n"
            "• 视频链接：https://www.bilibili.com/video/BVxxx\n"
            "• YouTube：https://youtube.com/watch?v=xxx\n"
            "• 小宇宙：https://xiaoyuzhou.com/xxx\n"
            "• 本地文件：D:\\\\path\\\\to\\\\file.mp4\n\n"
            "支持的平台：微信公众号、B站、YouTube、小红书、抖音、小宇宙\n\n"
            "命令：\n"
            "• /help - 显示本帮助\n"
            "• /status - 查看任务队列状态\n"
            "• /progress - 查看当前处理中任务的实时进度日志\n"
        )
        client.send_message(receive_id, receive_id_type, help_text)

    elif cmd == "/status":
        status = processor.get_status()
        lines = [
            "📊 任务队列状态",
            f"",
            f"队列大小：{status['queue_size']}",
            f"当前任务数：{len(status['current_tasks'])}",
            "",
        ]
        if status["current_tasks"]:
            lines.append("任务列表：")
            for tid, task in status["current_tasks"].items():
                elapsed = int(time.time() - task.get("submitted_at", time.time()))
                lines.append(
                    f"  • {tid}: {task['status']} (已用 {elapsed}s) - {task['input'][:40]}"
                )
        else:
            lines.append("（无任务）")
        client.send_message(receive_id, receive_id_type, "\n".join(lines))

    elif cmd == "/progress":
        # 显示当前正在处理任务的实时进度（读取 bot.log 末尾日志）
        status = processor.get_status()
        running = [
            (tid, t) for tid, t in status["current_tasks"].items()
            if t.get("status") == "processing"
        ]
        if not running:
            client.send_message(
                receive_id, receive_id_type,
                "📭 当前没有正在处理的任务\n输入 /status 查看所有任务",
            )
        else:
            lines = [f"🔄 当前有 {len(running)} 个任务在处理中", ""]
            for tid, task in running:
                elapsed = int(time.time() - task.get("started_at", time.time()))
                lines.append(f"📌 任务：{tid}")
                lines.append(f"   输入：{task['input'][:60]}")
                lines.append(f"   已用：{elapsed}s（{elapsed // 60}分{elapsed % 60}秒）")
                lines.append("")
            # 附上最近 20 行日志
            recent_logs = _tail_bot_log(20)
            if recent_logs:
                lines.append("📝 最近日志（倒序）：")
                lines.append("```")
                for line in recent_logs:
                    lines.append(line)
                lines.append("```")
            client.send_message(receive_id, receive_id_type, "\n".join(lines))

    else:
        client.send_message(
            receive_id,
            receive_id_type,
            f"未知命令：{cmd}\n输入 /help 查看可用命令",
        )


def _send_help(receive_id: str, receive_id_type: str, client: FeishuClient):
    """发送帮助"""
    client.send_message(
        receive_id,
        receive_id_type,
        "🤖 我是音视频转录整理 Bot\n\n"
        "直接发送链接或文件路径即可触发转录：\n"
        "• 网页：https://mp.weixin.qq.com/s/xxx\n"
        "• 视频：https://www.bilibili.com/video/BVxxx\n"
        "• 本地文件：D:\\\\path\\\\to\\\\file.mp4\n\n"
        "输入 /help 查看完整帮助",
    )


def _tail_bot_log(n: int = 20) -> List[str]:
    """读取 tmp/bot.log 末尾 n 行（保持旧→新顺序）"""
    log_file = os.path.join(SCRIPT_DIR, "..", "tmp", "bot.log")
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        # 取末尾 n 行，去掉换行符和 CLIXML 噪音
        tail = lines[-n:] if len(lines) >= n else lines
        return [ln.rstrip("\r\n") for ln in tail if ln.strip()]
    except Exception as e:
        logger.warning(f"读取 bot.log 失败: {e}")
        return []


# ============================================================
# 主程序
# ============================================================
def main():
    # 日志配置（同时输出到 stdout 和文件，便于 Windows 后台运行排查）
    log_file = os.path.join(SCRIPT_DIR, "..", "tmp", "bot.log")
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    # 清空旧日志
    try:
        open(log_file, "w", encoding="utf-8").close()
    except Exception:
        pass

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )

    # 加载 .env
    env_file = os.path.join(SCRIPT_DIR, "..", ".env")
    load_env_file(env_file)
    BotConfig.reload()

    # 校验配置
    if not BotConfig.APP_ID or not BotConfig.APP_SECRET:
        logger.error("未配置 FEISHU_APP_ID 或 FEISHU_APP_SECRET")
        logger.error("请在 .env 中配置飞书应用凭据")
        sys.exit(1)

    if not BotConfig.USER_ID:
        logger.warning(
            "未配置 FEISHU_USER_ID，飞书文档将走公开访问降级策略"
        )

    logger.info("=" * 60)
    logger.info("音视频转录整理 Bot 启动")
    logger.info(f"  App ID: {BotConfig.APP_ID}")
    logger.info(f"  User ID: {BotConfig.USER_ID or '(未配置)'}")
    logger.info(f"  Folder Token: {BotConfig.FOLDER_TOKEN or '(未配置，文档保存到根目录)'}")
    logger.info(f"  允许所有用户: {BotConfig.ALLOW_ALL_USERS}")
    logger.info(f"  群聊策略: {BotConfig.GROUP_POLICY}")
    logger.info(f"  私聊策略: {BotConfig.DM_POLICY}")
    logger.info(f"  管理员白名单: {BotConfig.ADMIN_IDS or '(无)'}")
    logger.info("=" * 60)

    # 初始化飞书 REST 客户端
    feishu_client = FeishuClient(BotConfig.APP_ID, BotConfig.APP_SECRET)

    # 初始化任务处理器
    processor = TaskProcessor(feishu_client)
    processor.start()

    # 注册事件处理器
    def on_message_receive(data: lark.im.v1.P2ImMessageReceiveV1) -> None:
        handle_message(data, processor)

    event_handler = lark.EventDispatcherHandler.builder("", "") \
        .register_p2_im_message_receive_v1(on_message_receive) \
        .build()

    # 初始化 WebSocket 客户端
    ws_client = lark.ws.Client(
        BotConfig.APP_ID,
        BotConfig.APP_SECRET,
        event_handler=event_handler,
        log_level=lark.LogLevel.INFO,
    )

    logger.info("正在连接飞书 WebSocket...")
    try:
        ws_client.start()  # 阻塞调用
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在关闭...")
    finally:
        processor.stop()
        logger.info("Bot 已关闭")


if __name__ == "__main__":
    main()
