"""
download.py — 音视频下载模块（yt-dlp 封装）

职责：
  1. 用 yt-dlp 下载视频/音频
  2. 优先下载字幕（如可获取）
  3. 返回下载结果（音频路径 + 字幕路径）

参考：小D 第 4 节工具栈 + config.yaml download 段
"""
import os
import sys
import subprocess
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlparse

import yt_dlp

logger = logging.getLogger(__name__)

# 支持的视频平台
VIDEO_PLATFORMS = {
    "youtube.com": "youtube",
    "youtu.be": "youtube",
    "bilibili.com": "bilibili",
    "b23.tv": "bilibili",
    "xiaoyuzhoufm.com": "xiaoyuzhou",
    "douyin.com": "douyin",
    "iesdouyin.com": "douyin",
    "xiaohongshu.com": "xiaohongshu",
    "xhslink.com": "xiaohongshu",
}


def detect_platform(url: str) -> str:
    """识别链接所属平台"""
    parsed = urlparse(url)
    netloc = parsed.netloc.lower()
    for domain, platform in VIDEO_PLATFORMS.items():
        if domain in netloc:
            return platform
    return "web"  # 普通网页


def download_media(
    url: str,
    output_dir: str = "./tmp/downloads",
    prefer_subtitle: bool = True,
    subtitle_lang: str = "zh,en",
    proxy: Optional[str] = None,
    audio_only: bool = True,
    cookies_file: Optional[str] = None,
    cookies_from_browser: Optional[str] = None,
) -> Dict[str, Any]:
    """
    下载音视频 + 字幕

    Args:
        url: 视频/音频链接
        output_dir: 下载目录
        prefer_subtitle: 是否优先下载字幕
        subtitle_lang: 字幕语言优先级
        proxy: 代理地址（可选）
        audio_only: 只下载音频（True，ASR 只需要音频）
        cookies_file: Netscape 格式 cookies 文件路径（B 站反爬必需）
        cookies_from_browser: 从浏览器读取 cookies（如 'chrome'/'edge'/'firefox'）
            注意：新版 Chrome 加密了 cookies，此方式可能失效，推荐用 cookies_file

    Returns:
        {
            "success": bool,
            "audio_path": str,      # 音频文件路径
            "subtitle_path": str,   # 字幕文件路径（无则为 None）
            "title": str,           # 视频标题
            "duration": int,        # 时长（秒）
            "platform": str,        # 平台
            "error": str,           # 错误信息（失败时）
        }
    """
    result = {
        "success": False,
        "audio_path": None,
        "subtitle_path": None,
        "title": None,
        "duration": None,
        "platform": detect_platform(url),
        "error": None,
    }

    os.makedirs(output_dir, exist_ok=True)

    # yt-dlp 配置
    ydl_opts = {
        "format": "bestaudio/best" if audio_only else "bestvideo+bestaudio/best",
        "outtmpl": os.path.join(output_dir, "%(title).80s.%(ext)s"),
        "noprogress": True,
        "quiet": False,
        "no_warnings": True,
    }

    # 代理
    if proxy:
        ydl_opts["proxy"] = proxy

    # cookies 配置（B 站反爬 412、抖音登录态必需）
    # 优先级：按平台自动选择 > cookies_file > cookies_from_browser
    platform = result["platform"]
    # 按平台查找专用 cookies：config/<platform>_cookies.txt
    # 平台映射：bilibili→bilibili_cookies.txt, douyin→douyin_cookies.txt
    platform_cookies_map = {
        "bilibili": "bilibili_cookies.txt",
        "douyin": "douyin_cookies.txt",
        "xiaohongshu": "xiaohongshu_cookies.txt",
        "youtube": "youtube_cookies.txt",
    }
    # config 目录（相对脚本目录的上级）
    config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
    platform_cookie_file = os.path.join(config_dir, platform_cookies_map.get(platform, ""))

    if platform in platform_cookies_map and os.path.exists(platform_cookie_file):
        ydl_opts["cookiefile"] = platform_cookie_file
        logger.info(f"使用 {platform} 专用 cookies: {platform_cookie_file}")
    elif cookies_file:
        if os.path.exists(cookies_file):
            ydl_opts["cookiefile"] = cookies_file
            logger.info(f"使用 cookies 文件: {cookies_file}")
        else:
            logger.warning(f"cookies 文件不存在: {cookies_file}")
    elif cookies_from_browser:
        ydl_opts["cookiesfrombrowser"] = (cookies_from_browser,)
        logger.info(f"从浏览器读取 cookies: {cookies_from_browser}")

    # 抖音专用提示：未配置 cookies 会立即失败
    if platform == "douyin" and "cookiefile" not in ydl_opts and "cookiesfrombrowser" not in ydl_opts:
        logger.error(
            "抖音要求登录态 cookies，未配置会失败。"
            "请在 config/douyin_cookies.txt 放置抖音登录后的 Netscape 格式 cookies。"
        )

    # 字幕下载
    if prefer_subtitle:
        ydl_opts["writesubtitles"] = True
        ydl_opts["writeautomaticsub"] = True  # 自动生成的字幕
        ydl_opts["subtitleslangs"] = subtitle_lang.split(",")
        ydl_opts["subtitlesformat"] = "srt/vtt/best"

    # B 站专用：携带 UA 和 Referer 绕过反爬
    if result["platform"] == "bilibili":
        ydl_opts["http_headers"] = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.bilibili.com",
        }
        if not cookies_file and not cookies_from_browser:
            logger.warning(
                "B 站近期升级反爬，未配置 cookies 可能遇到 412 错误。"
                "请在 .env 中配置 COOKIES_FILE 或在 config.yaml 中设置 download.cookies_file。"
                "教程见 docs/troubleshooting.md 坑 31。"
            )

    try:
        logger.info(f"开始下载: {url} (平台: {result['platform']})")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 先提取信息
            info = ydl.extract_info(url, download=False)
            result["title"] = info.get("title", "untitled")
            result["duration"] = info.get("duration", 0)

            # 检查字幕是否可用
            subtitles = info.get("subtitles", {})
            auto_subtitles = info.get("automatic_caption", {})

            # 下载前记录目录已有文件（用于下载后精确识别新文件）
            existing_files = set(Path(output_dir).glob("*"))

            # 下载
            ydl.download([url])

            # 精确识别本次下载的文件：用 info 中的标题匹配，避免误用旧文件
            # yt-dlp 默认文件名模板是 %(title).80s.%(ext)s
            expected_basename = ydl.prepare_filename(info)
            expected_stem = Path(expected_basename).stem

            # 音频扩展名 + 视频扩展名（部分平台如抖音只返回视频，pipeline 后续会用 ffmpeg 提取音频）
            media_exts = [".m4a", ".mp3", ".wav", ".webm", ".opus", ".mp4", ".mkv", ".mov", ".avi"]
            subtitle_exts = [".srt", ".vtt", ".ass"]

            # 1. 优先：在"新文件"中按预期标题前缀匹配（下载产生了新文件的场景）
            new_audio = None
            new_subtitle = None
            for f in Path(output_dir).glob("*"):
                # 跳过下载前已存在的旧文件
                if f in existing_files:
                    continue
                # 文件名必须以预期标题开头（处理 ext 不同的情况）
                if not f.stem.startswith(expected_stem[:30]):
                    continue
                if f.suffix.lower() in media_exts:
                    new_audio = str(f)
                elif f.suffix.lower() in subtitle_exts:
                    new_subtitle = str(f)

            # 2. 兜底 1：yt-dlp 跳过下载场景（同名文件已存在，yt-dlp 不重新下载）
            #    此时新文件集为空，但旧文件就是目标文件，需要按标题在所有文件中查找
            if not new_audio:
                for f in Path(output_dir).glob("*"):
                    if not f.stem.startswith(expected_stem[:30]):
                        continue
                    if f.suffix.lower() in media_exts:
                        new_audio = str(f)
                        logger.info(f"yt-dlp 跳过下载，复用已存在文件: {new_audio}")
                        break

            if not new_subtitle:
                for f in Path(output_dir).glob("*"):
                    if not f.stem.startswith(expected_stem[:30]):
                        continue
                    if f.suffix.lower() in subtitle_exts:
                        new_subtitle = str(f)
                        break

            # 3. 兜底 2：按标题匹配失败，用最新修改时间的文件（仅在新文件中找）
            if not new_audio:
                audio_candidates = [
                    f for f in Path(output_dir).glob("*")
                    if f not in existing_files
                    and f.suffix.lower() in media_exts
                ]
                if audio_candidates:
                    new_audio = str(max(audio_candidates, key=lambda f: f.stat().st_mtime))
                    logger.warning(f"按标题未匹配到音频，用最新文件兜底: {new_audio}")

            if not new_subtitle:
                subtitle_candidates = [
                    f for f in Path(output_dir).glob("*")
                    if f not in existing_files
                    and f.suffix.lower() in [".srt", ".vtt", ".ass"]
                ]
                if subtitle_candidates:
                    new_subtitle = str(max(subtitle_candidates, key=lambda f: f.stat().st_mtime))

            result["audio_path"] = new_audio
            result["subtitle_path"] = new_subtitle

            if not new_audio:
                result["error"] = "下载完成但未找到音频文件"
                logger.error(result["error"])
                return result

            result["success"] = True
            logger.info(
                f"下载完成: {result['title']} "
                f"(音频: {result['audio_path']}, 字幕: {result['subtitle_path']})"
            )

    except yt_dlp.utils.DownloadError as e:
        result["error"] = f"下载失败: {str(e)}"
        logger.error(result["error"])
    except Exception as e:
        result["error"] = f"未知错误: {str(e)}"
        logger.error(result["error"])

    return result


def get_ffmpeg_path() -> str:
    """获取 ffmpeg 路径，优先用系统 ffmpeg，没有则用 imageio-ffmpeg"""
    # 检查系统 ffmpeg
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return "ffmpeg"
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # 降级到 imageio-ffmpeg
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        logger.warning(
            "系统未安装 ffmpeg，且 imageio-ffmpeg 未安装。"
            "请运行: pip install imageio-ffmpeg"
        )
        return ""


if __name__ == "__main__":
    # 命令行测试
    import argparse

    parser = argparse.ArgumentParser(description="音视频下载工具")
    parser.add_argument("--url", required=True, help="视频/音频链接")
    parser.add_argument("--output", default="./tmp/downloads", help="输出目录")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    result = download_media(args.url, output_dir=args.output)
    print(f"\n下载结果: {result}")
