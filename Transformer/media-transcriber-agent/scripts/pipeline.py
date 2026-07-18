"""
pipeline.py — 主流水线脚本

职责：
  串联 download → transcode → transcribe → refine → deliver 完整流程
  根据素材类型自动选择处理路径：
    - 网页文章 → extract_web → refine → deliver
    - 视频/音频链接 → download → (字幕 or ASR) → refine → deliver
    - 本地文件 → transcode → transcribe → refine → deliver

使用方法：
  python pipeline.py --input "<URL或文件路径>" [--title "标题"]

参考：prompts/system-prompt.md 标准工作流
"""
import os
import sys
import logging
import argparse
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlparse


def load_env_file(env_path: str) -> None:
    """从 .env 文件加载环境变量（不覆盖已存在的）"""
    if not os.path.isfile(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


# 加载 .env 文件（从项目根目录和当前目录）
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_env_file(str(_PROJECT_ROOT / ".env"))
load_env_file(".env")

# 确保能导入同目录下的模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from download import download_media, detect_platform
from transcribe import validate_file, transcode_to_wav, transcribe_audio
from transcribe_funasr import transcribe_audio_funasr
from extract_web import extract_content
from refine import refine_text, save_refined, generate_ai_summary
from deliver_feishu import deliver_to_feishu

logger = logging.getLogger(__name__)


class MediaTranscriberPipeline:
    """音视频转录整理主流水线"""

    def __init__(
        self,
        glm_api_key: Optional[str] = None,
        llm_model: str = "glm-4.7",
        llm_fallback: str = "glm-4.5-air",
        asr_engine: str = "funasr",
        asr_model: str = "medium",
        asr_device: str = "cpu",
        asr_compute_type: str = "int8",
        output_dir: str = "./output",
        temp_dir: str = "./tmp",
        deliver_to_feishu_enabled: bool = False,
        feishu_user_id: Optional[str] = None,
        feishu_folder_token: Optional[str] = None,
    ):
        self.glm_api_key = glm_api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get("GLM_API_KEY")
        self.llm_model = llm_model
        self.llm_fallback = llm_fallback
        self.asr_engine = asr_engine  # "funasr"（默认，国内可用）或 "faster-whisper"
        self.asr_model = asr_model
        self.asr_device = asr_device
        self.asr_compute_type = asr_compute_type
        self.output_dir = output_dir
        self.temp_dir = temp_dir
        # 飞书交付（Phase 2）
        self.deliver_to_feishu_enabled = deliver_to_feishu_enabled
        self.feishu_user_id = feishu_user_id or os.environ.get("FEISHU_USER_ID")
        self.feishu_folder_token = feishu_folder_token or os.environ.get("FEISHU_FOLDER_TOKEN")

        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(temp_dir, exist_ok=True)

    def process(self, input_source: str, title: Optional[str] = None) -> Dict[str, Any]:
        """
        处理输入源（URL 或本地文件）

        Returns:
            {
                "success": bool,
                "output_path": str,     # 提纯稿 Markdown 路径
                "platform": str,        # 来源平台
                "title": str,           # 标题
                "feishu_url": str,      # 飞书文档链接（Phase 2，未启用时为 None）
                "feishu_permission": bool,
                "error": str,
            }
        """
        logger.info(f"开始处理: {input_source}")

        # 判断输入类型
        if self._is_url(input_source):
            result = self._process_url(input_source, title)
        elif self._is_local_file(input_source):
            result = self._process_local_file(input_source, title)
        else:
            return {
                "success": False,
                "output_path": None,
                "platform": None,
                "title": title,
                "feishu_url": None,
                "feishu_permission": False,
                "error": f"无法识别的输入: {input_source}",
            }

        # 成功后执行飞书交付（Phase 2）
        if result["success"] and self.deliver_to_feishu_enabled:
            feishu_result = self._deliver_to_feishu(
                title=result["title"],
                markdown_path=result["output_path"],
                source_url=input_source if self._is_url(input_source) else None,
            )
            result["feishu_url"] = feishu_result.get("url")
            result["feishu_permission"] = feishu_result.get("permission_granted", False)
            if not feishu_result["success"]:
                # 飞书交付失败不阻塞主流程，只记录错误
                logger.warning(
                    f"飞书交付失败（主流程不受影响）: {feishu_result.get('error')}"
                )
                if not result.get("error"):
                    result["error"] = f"飞书交付失败: {feishu_result.get('error')}"
        else:
            result.setdefault("feishu_url", None)
            result.setdefault("feishu_permission", False)

        return result

    def _deliver_to_feishu(
        self,
        title: str,
        markdown_path: str,
        source_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """读取 Markdown 文件并交付到飞书文档

        飞书文档标题优先用正文的第一个 Markdown 标题（# 或 ##），
        提取不到则用传入的 title（通常是视频/文章原标题）兜底。
        本地文件名不受影响，仍用原 title。

        如果传入 source_url（URL 链接），会在正文最前面插入一个引用块，
        标注原文来源，便于后续追溯。引用块只加到飞书文档，不影响本地 .md 文件。

        在原文链接引用块之后，还会生成一个"AI 总结"高亮块（callout），
        对全文核心内容做 1-2 句概括 + 3-5 个要点提炼。
        AI 总结基于提纯后的正文生成，失败时不阻塞主流程，仅跳过该块。
        """
        try:
            with open(markdown_path, "r", encoding="utf-8") as f:
                markdown_content = f.read()
        except Exception as e:
            return {
                "success": False,
                "url": None,
                "permission_granted": False,
                "error": f"读取 Markdown 文件失败: {e}",
            }

        # 保留原始正文（不含 source_block），用于生成 AI 总结
        original_body = markdown_content

        # 在正文最前面插入原文来源引用块（仅飞书文档，不影响本地 .md）
        source_block = ""
        if source_url:
            source_block = f"> 原文链接：{source_url}\n\n"
            logger.info(f"已在飞书文档开头插入原文来源引用: {source_url}")

        # 生成 AI 总结（基于原始提纯正文，避免 source_url 干扰 LLM）
        # 总结任务对推理深度要求低于提纯，使用 air 模型提速（30-60s vs 2-4min）
        summary_model = self.llm_fallback  # glm-4.5-air
        summary_fallback = "glm-4.5-flash"  # 再降级到 flash
        logger.info(f"AI 总结使用快速模型: {summary_model} (fallback: {summary_fallback})")
        summary_block = ""
        summary_result = generate_ai_summary(
            refined_text=original_body,
            title=title,
            api_key=self.glm_api_key,
            model=summary_model,
            fallback_model=summary_fallback,
        )
        if summary_result["success"]:
            # 用 HTML 注释标记包裹，deliver_feishu._markdown_to_blocks 识别后转为 callout block
            summary_block = (
                "<!--AI_SUMMARY_START-->\n"
                f"{summary_result['summary']}\n"
                "<!--AI_SUMMARY_END-->\n\n"
            )
            logger.info("已生成 AI 总结，将作为高亮块插入飞书文档")
        else:
            # 总结失败不阻塞主流程，仅记录警告
            logger.warning(
                f"AI 总结生成失败，跳过该高亮块: {summary_result.get('error')}"
            )

        # 拼装最终的飞书文档内容：原文链接引用 → AI 总结高亮块 → 正文
        markdown_content = source_block + summary_block + original_body

        # 从正文提取第一个 Markdown 标题作为飞书文档标题
        feishu_title = self._extract_first_heading(markdown_content) or title
        # 飞书文档标题长度限制 100 字符，超出截断
        if len(feishu_title) > 100:
            feishu_title = feishu_title[:100]
            logger.info(f"飞书文档标题过长，已截断为: {feishu_title}")

        if feishu_title != title:
            logger.info(f"飞书文档标题用正文首个标题: {feishu_title} (原视频标题: {title})")

        logger.info(f"开始飞书文档交付: {feishu_title}")
        return deliver_to_feishu(
            title=feishu_title,
            markdown_content=markdown_content,
            user_id=self.feishu_user_id,
            folder_token=self.feishu_folder_token,
        )

    @staticmethod
    def _extract_first_heading(markdown_content: str) -> Optional[str]:
        """从 Markdown 内容提取第一个标题（# ~ ######）的文本

        跳过代码块内的 # 行（代码块以 ``` 包裹）。
        返回纯文本标题（去除 # 前缀和前后空白），无标题返回 None。
        """
        in_code_block = False
        for line in markdown_content.splitlines():
            stripped = line.strip()
            # 代码块边界切换
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue
            # 匹配 ATX 标题：# ~ ######
            if stripped.startswith("#"):
                # 去掉 # 前缀和可能的 # 后缀（如 ## 标题 ##）
                text = stripped.lstrip("#").strip()
                # 去除尾部 # （闭合式标题）
                text = text.rstrip("#").strip()
                if text:
                    return text
        return None

    def _is_url(self, source: str) -> bool:
        """判断是否为 URL"""
        try:
            parsed = urlparse(source)
            return parsed.scheme in ("http", "https") and bool(parsed.netloc)
        except Exception:
            return False

    def _is_local_file(self, source: str) -> bool:
        """判断是否为本地文件"""
        return os.path.isfile(source)

    def _process_url(
        self, url: str, title: Optional[str] = None
    ) -> Dict[str, Any]:
        """处理 URL（网页文章或视频链接）"""
        platform = detect_platform(url)
        logger.info(f"平台识别: {platform}")

        if platform == "web":
            # 网页文章路径：直接抽正文
            return self._process_web_article(url, title)
        else:
            # 视频平台路径：下载 → 字幕/ASR → 提纯
            return self._process_video_url(url, title, platform)

    def _process_web_article(
        self, url: str, title: Optional[str] = None
    ) -> Dict[str, Any]:
        """处理网页文章"""
        logger.info("路径：网页文章抽取")

        web_output = os.path.join(self.temp_dir, "web_content.md")
        result = extract_content(url, output_path=web_output)

        if not result["success"]:
            return {
                "success": False,
                "output_path": None,
                "platform": "web",
                "title": title or result.get("title"),
                "error": result["error"],
            }

        # 提纯
        final_title = title or result["title"] or "web_article"
        metadata = {
            "作者": result.get("author"),
            "发布时间": result.get("date"),
            "来源": url,
        }

        refine_result = refine_text(
            raw_text=result["content"],
            title=final_title,
            metadata=metadata,
            api_key=self.glm_api_key,
            model=self.llm_model,
            fallback_model=self.llm_fallback,
        )

        if not refine_result["success"]:
            return {
                "success": False,
                "output_path": None,
                "platform": "web",
                "title": final_title,
                "error": refine_result["error"],
            }

        # 保存
        output_path = save_refined(
            refine_result["refined_text"],
            output_dir=self.output_dir,
            filename=self._sanitize_filename(final_title),
        )

        return {
            "success": True,
            "output_path": output_path,
            "platform": "web",
            "title": final_title,
            "error": None,
        }

    def _process_video_url(
        self, url: str, title: Optional[str], platform: str
    ) -> Dict[str, Any]:
        """处理视频链接"""
        logger.info(f"路径：视频下载 → 字幕/ASR")

        # cookies 配置（B 站反爬 412 必需）
        cookies_file = os.environ.get("COOKIES_FILE")
        cookies_from_browser = os.environ.get("COOKIES_FROM_BROWSER")

        # Step 1: 下载
        download_result = download_media(
            url=url,
            output_dir=os.path.join(self.temp_dir, "downloads"),
            cookies_file=cookies_file,
            cookies_from_browser=cookies_from_browser,
        )

        if not download_result["success"]:
            return {
                "success": False,
                "output_path": None,
                "platform": platform,
                "title": title,
                "error": download_result["error"],
            }

        final_title = title or download_result.get("title") or "video_transcript"

        # Step 2: 判断路径（字幕 or ASR）
        if download_result.get("subtitle_path"):
            # 有字幕路径：直接读字幕
            logger.info("使用字幕路径（跳过 ASR）")
            with open(
                download_result["subtitle_path"], "r", encoding="utf-8"
            ) as f:
                raw_text = f.read()
        else:
            # 无字幕路径：转码 + ASR
            logger.info("使用 ASR 路径")
            asr_result = self._run_asr(download_result["audio_path"])
            if not asr_result["success"]:
                return {
                    "success": False,
                    "output_path": None,
                    "platform": platform,
                    "title": final_title,
                    "error": asr_result["error"],
                }
            raw_text = asr_result["text"]

        # Step 3: 提纯
        metadata = {
            "平台": platform,
            "时长": f"{download_result.get('duration', 0)} 秒",
            "来源": url,
        }

        refine_result = refine_text(
            raw_text=raw_text,
            title=final_title,
            metadata=metadata,
            api_key=self.glm_api_key,
            model=self.llm_model,
            fallback_model=self.llm_fallback,
        )

        if not refine_result["success"]:
            return {
                "success": False,
                "output_path": None,
                "platform": platform,
                "title": final_title,
                "error": refine_result["error"],
            }

        # Step 4: 保存
        output_path = save_refined(
            refine_result["refined_text"],
            output_dir=self.output_dir,
            filename=self._sanitize_filename(final_title),
        )

        return {
            "success": True,
            "output_path": output_path,
            "platform": platform,
            "title": final_title,
            "error": None,
        }

    def _process_local_file(
        self, file_path: str, title: Optional[str] = None
    ) -> Dict[str, Any]:
        """处理本地音视频文件"""
        logger.info("路径：本地文件 → 转码 → ASR")

        # 验证文件
        validation = validate_file(file_path)
        if not validation["valid"]:
            return {
                "success": False,
                "output_path": None,
                "platform": "local",
                "title": title,
                "error": validation["error"],
            }

        final_title = title or Path(file_path).stem

        # 转码 + ASR
        asr_result = self._run_asr(file_path)
        if not asr_result["success"]:
            return {
                "success": False,
                "output_path": None,
                "platform": "local",
                "title": final_title,
                "error": asr_result["error"],
            }

        # 提纯
        metadata = {
            "文件": file_path,
            "格式": validation["format"],
            "大小": f"{validation['size_mb']} MB",
        }

        refine_result = refine_text(
            raw_text=asr_result["text"],
            title=final_title,
            metadata=metadata,
            api_key=self.glm_api_key,
            model=self.llm_model,
            fallback_model=self.llm_fallback,
        )

        if not refine_result["success"]:
            return {
                "success": False,
                "output_path": None,
                "platform": "local",
                "title": final_title,
                "error": refine_result["error"],
            }

        # 保存
        output_path = save_refined(
            refine_result["refined_text"],
            output_dir=self.output_dir,
            filename=self._sanitize_filename(final_title),
        )

        return {
            "success": True,
            "output_path": output_path,
            "platform": "local",
            "title": final_title,
            "error": None,
        }

    def _run_asr(self, audio_path: str) -> Dict[str, Any]:
        """转码 + ASR 转录（根据 asr_engine 选择后端）"""
        # 转码
        tc_result = transcode_to_wav(
            audio_path,
            output_dir=os.path.join(self.temp_dir, "wav"),
        )
        if not tc_result["success"]:
            return tc_result

        # 根据引擎选择 ASR 后端
        if self.asr_engine == "funasr":
            # funasr + SenseVoiceSmall（默认，国内可用，速度快）
            return transcribe_audio_funasr(
                tc_result["wav_path"],
                model_name="iic/SenseVoiceSmall",
                output_dir=os.path.join(self.temp_dir, "transcripts"),
            )
        else:
            # faster-whisper（需要能访问 HuggingFace）
            return transcribe_audio(
                tc_result["wav_path"],
                model_name=self.asr_model,
                device=self.asr_device,
                compute_type=self.asr_compute_type,
                output_dir=os.path.join(self.temp_dir, "transcripts"),
            )

    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名中的非法字符"""
        illegal_chars = '<>:"/\\|?*'
        for ch in illegal_chars:
            filename = filename.replace(ch, "_")
        return filename.strip()[:80]  # 限制长度


def main():
    parser = argparse.ArgumentParser(description="音视频转录整理主流水线")
    parser.add_argument(
        "--input", required=True, help="输入源（URL 或本地文件路径）"
    )
    parser.add_argument("--title", default=None, help="素材标题（可选）")
    parser.add_argument("--output-dir", default="./output", help="输出目录")
    parser.add_argument("--temp-dir", default="./tmp", help="临时文件目录")
    parser.add_argument(
        "--asr-engine",
        default="funasr",
        choices=["funasr", "faster-whisper"],
        help="ASR 引擎 (funasr 默认国内可用 / faster-whisper 需访问 HuggingFace)",
    )
    parser.add_argument(
        "--asr-model", default="medium", help="ASR 模型 (tiny/base/small/medium/large-v3)"
    )
    parser.add_argument("--asr-device", default="cpu", help="ASR 设备 (cpu/cuda)")
    parser.add_argument(
        "--asr-compute-type", default="int8", help="ASR 计算类型 (int8/float16)"
    )
    parser.add_argument("--llm-model", default="glm-4.7", help="LLM 模型")
    parser.add_argument(
        "--llm-fallback", default="glm-4.5-air", help="LLM 降级模型（限流时）"
    )
    parser.add_argument(
        "--verbose", action="store_true", help="详细日志"
    )
    # Phase 2：飞书文档交付
    parser.add_argument(
        "--deliver-to-feishu",
        action="store_true",
        help="交付到飞书文档（Phase 2，需配置 FEISHU_APP_ID/SECRET）",
    )
    parser.add_argument(
        "--feishu-user-id",
        default=None,
        help="飞书用户 ID（openid，用于授权协作者；默认读 FEISHU_USER_ID）",
    )
    parser.add_argument(
        "--feishu-folder-token",
        default=None,
        help="飞书文件夹 token（可选，文档创建位置；默认读 FEISHU_FOLDER_TOKEN）",
    )

    args = parser.parse_args()

    # 日志配置
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # 检查 API Key（方式 B 优先：OPENAI_API_KEY；降级方式 A：GLM_API_KEY）
    if not (os.environ.get("OPENAI_API_KEY") or os.environ.get("GLM_API_KEY")):
        logger.error("未配置 OPENAI_API_KEY 或 GLM_API_KEY 环境变量")
        logger.error("请在 .env 中配置（方式 B 用 OPENAI_API_KEY，方式 A 用 GLM_API_KEY）")
        sys.exit(1)

    # Phase 2：开启飞书交付时校验凭据
    if args.deliver_to_feishu:
        if not (os.environ.get("FEISHU_APP_ID") and os.environ.get("FEISHU_APP_SECRET")):
            logger.error("开启 --deliver-to-feishu 但未配置 FEISHU_APP_ID / FEISHU_APP_SECRET")
            logger.error("请在 .env 中配置飞书应用凭据，参考 profile/.env.example")
            sys.exit(1)

    # 运行流水线
    pipeline = MediaTranscriberPipeline(
        llm_model=args.llm_model,
        llm_fallback=args.llm_fallback,
        asr_engine=args.asr_engine,
        asr_model=args.asr_model,
        asr_device=args.asr_device,
        asr_compute_type=args.asr_compute_type,
        output_dir=args.output_dir,
        temp_dir=args.temp_dir,
        deliver_to_feishu_enabled=args.deliver_to_feishu,
        feishu_user_id=args.feishu_user_id,
        feishu_folder_token=args.feishu_folder_token,
    )

    result = pipeline.process(args.input, title=args.title)

    print("\n" + "=" * 60)
    if result["success"]:
        print(f"处理成功！")
        print(f"  标题: {result['title']}")
        print(f"  平台: {result['platform']}")
        print(f"  提纯稿: {result['output_path']}")
        if result.get("feishu_url"):
            print(f"  飞书文档: {result['feishu_url']}")
            perm = "已授权" if result.get("feishu_permission") else "未完成"
            print(f"  协作者权限: {perm}")
    else:
        print(f"处理失败: {result['error']}")
        if result.get("output_path"):
            print(f"  （本地提纯稿已保存: {result['output_path']}）")
        sys.exit(1)
    print("=" * 60)


if __name__ == "__main__":
    main()
