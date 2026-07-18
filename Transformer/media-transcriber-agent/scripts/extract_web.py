"""
extract_web.py — 网页正文抽取模块（trafilatura 封装）

职责：
  1. 用 trafilatura 抽取网页正文
  2. 自动去除导航、广告、侧边栏、评论等噪音
  3. 输出干净的 Markdown 文本
  4. 保留标题、作者、发布时间等元信息
  5. 微信公众号特殊处理（需带浏览器 UA 才能抓取）

参考：web-content-extractor SKILL.md
"""
import os
import sys
import re
import logging
from typing import Optional, Dict, Any

import requests
import trafilatura
from trafilatura.metadata import extract_metadata

logger = logging.getLogger(__name__)

# 浏览器 UA（微信公众号等平台会拦截非浏览器请求）
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# 微信公众号文章正则（从 HTML 中提取）
WECHAT_TITLE_RE = re.compile(r'<h1[^>]*class="rich_media_title"[^>]*>(.*?)</h1>', re.S)
WECHAT_OG_TITLE_RE = re.compile(
    r'<meta[^>]*property="og:title"[^>]*content="([^"]+)"', re.I
)
WECHAT_CONTENT_RE = re.compile(
    r'<div[^>]*id="js_content"[^>]*>(.*?)</div>\s*<div', re.S
)
WECHAT_AUTHOR_RE = re.compile(
    r'<a[^>]*id="js_name"[^>]*>(.*?)</a>', re.S
)
WECHAT_OG_DESC_RE = re.compile(
    r'<meta[^>]*property="og:description"[^>]*content="([^"]+)"', re.I
)
WECHAT_TIME_RE = re.compile(
    r'var\s+createTime\s*=\s*[\'"]([^\'\"]+)[\'"]', re.S
)
WECHAT_PUBLISH_TIME_RE = re.compile(
    r'var\s+ct\s*=\s*[\'"]?(\d+)[\'"]?', re.S
)


def _is_wechat(url: str) -> bool:
    """判断是否为微信公众号链接"""
    return "mp.weixin.qq.com" in url


def _fetch_with_headers(url: str) -> Optional[str]:
    """用浏览器 UA 下载网页 HTML（解决微信公众号反爬）"""
    try:
        logger.info(f"用浏览器 UA 下载网页: {url}")
        resp = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
        if resp.status_code != 200:
            logger.error(f"HTTP {resp.status_code}")
            return None
        # 微信公众号返回 GBK 或 UTF-8，按 apparent_encoding 解码
        if resp.encoding and resp.encoding.lower() == "iso-8859-1":
            resp.encoding = resp.apparent_encoding
        return resp.text
    except Exception as e:
        logger.error(f"下载失败: {e}")
        return None


def _clean_html(html: str) -> str:
    """粗清洗 HTML：移除 script/style/注释"""
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.S | re.I)
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.S | re.I)
    html = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    return html


def _html_to_text(html_fragment: str) -> str:
    """把 HTML 片段转为简单文本（保留换行）"""
    # <p> <br> 转换行
    text = re.sub(r"<br\s*/?>", "\n", html_fragment, flags=re.I)
    text = re.sub(r"</p\s*>", "\n\n", text, flags=re.I)
    text = re.sub(r"<p[^>]*>", "", text, flags=re.I)
    # 移除其余所有标签
    text = re.sub(r"<[^>]+>", "", text)
    # HTML 实体
    text = (
        text.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
    )
    # 折叠多余空行
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_wechat(html: str, url: str) -> Dict[str, Any]:
    """微信公众号文章专用抽取（trafilatura 抓不到时的降级方案）"""
    result = {
        "success": False,
        "title": None,
        "author": None,
        "date": None,
        "content": None,
        "word_count": 0,
        "error": None,
    }

    # 检测验证码重定向
    if "wappoc_appmsgcaptcha" in html or "环境异常" in html:
        result["error"] = "微信公众号触发验证码，请稍后重试或更换网络"
        return result

    html = _clean_html(html)

    # 标题：优先 h1.rich_media_title，其次 og:title
    m = WECHAT_TITLE_RE.search(html)
    if m:
        result["title"] = _html_to_text(m.group(1))
    if not result["title"]:
        m = WECHAT_OG_TITLE_RE.search(html)
        if m:
            result["title"] = m.group(1).strip()

    # 作者（公众号名）
    m = WECHAT_AUTHOR_RE.search(html)
    if m:
        result["author"] = _html_to_text(m.group(1))

    # 发布时间：优先 createTime 文本，其次 ct 时间戳
    m = WECHAT_TIME_RE.search(html)
    if m:
        result["date"] = m.group(1)
    if not result["date"]:
        m = WECHAT_PUBLISH_TIME_RE.search(html)
        if m:
            import datetime
            try:
                ts = int(m.group(1))
                result["date"] = datetime.datetime.fromtimestamp(
                    ts
                ).strftime("%Y-%m-%d %H:%M")
            except (ValueError, OSError):
                pass

    # 正文
    m = WECHAT_CONTENT_RE.search(html)
    if not m:
        result["error"] = "微信公众号正文区块未找到（页面结构可能变更）"
        return result

    content_text = _html_to_text(m.group(1))
    if len(content_text) < 100:
        result["error"] = f"微信公众号正文过短（{len(content_text)} 字），可能被截断"
        return result

    # 组装 Markdown
    md_parts = []
    if result["title"]:
        md_parts.append(f"# {result['title']}\n")
    meta = []
    if result["author"]:
        meta.append(f"公众号：{result['author']}")
    if result["date"]:
        meta.append(f"发布时间：{result['date']}")
    if meta:
        md_parts.append(f"> {'  '.join(meta)}  |  来源：{url}\n")
    md_parts.append(content_text)

    final_md = "\n".join(md_parts)
    result["content"] = final_md
    result["word_count"] = len(content_text)
    result["success"] = True
    return result


def extract_content(
    url: str,
    output_path: Optional[str] = None,
    include_links: bool = False,
    include_images: bool = False,
) -> Dict[str, Any]:
    """
    抽取网页正文

    Args:
        url: 网页链接
        output_path: 输出文件路径（可选，默认返回文本）
        include_links: 是否保留链接
        include_images: 是否保留图片

    Returns:
        {
            "success": bool,
            "title": str,
            "author": str,
            "date": str,
            "content": str,        # Markdown 正文
            "word_count": int,
            "error": str,
        }
    """
    result = {
        "success": False,
        "title": None,
        "author": None,
        "date": None,
        "content": None,
        "word_count": 0,
        "error": None,
    }

    try:
        # 微信公众号走专用路径
        if _is_wechat(url):
            logger.info("检测到微信公众号链接，走专用抽取路径")
            html = _fetch_with_headers(url)
            if not html:
                result["error"] = "微信公众号网页下载失败"
                return result
            wc_result = _extract_wechat(html, url)
            if wc_result["success"]:
                result = wc_result
                if output_path:
                    os.makedirs(
                        os.path.dirname(output_path) or ".", exist_ok=True
                    )
                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write(result["content"])
                    logger.info(f"正文已保存: {output_path}")
                logger.info(
                    f"微信公众号抽取完成: {result['word_count']} 字, "
                    f"标题: {result['title']}"
                )
                return result
            # 微信专用失败，降级到 trafilatura 再试
            logger.warning(
                f"微信专用抽取失败（{wc_result['error']}），降级到 trafilatura"
            )
            downloaded = html
        else:
            # 普通网页：先用带 UA 的 requests 下载，再传给 trafilatura
            logger.info(f"下载网页: {url}")
            downloaded = _fetch_with_headers(url)
            if not downloaded:
                # 降级到 trafilatura 自带的下载
                downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                result["error"] = "网页无法访问（可能 404 或超时）"
                logger.error(result["error"])
                return result

        # 抽取元信息
        logger.info("抽取元信息...")
        metadata = extract_metadata(downloaded)
        if metadata:
            result["title"] = metadata.title or result["title"]
            result["author"] = metadata.author or result["author"]
            result["date"] = metadata.date or result["date"]

        # 抽取正文（Markdown 格式）
        logger.info("抽取正文...")
        content = trafilatura.extract(
            downloaded,
            output_format="markdown",
            include_links=include_links,
            include_images=include_images,
            include_tables=True,
            favor_precision=True,  # 精度优先，减少噪音
        )

        if not content:
            result["error"] = (
                result.get("error")
                or "正文抽取为空（可能是 JS 渲染页面或登录墙）"
            )
            logger.error(result["error"])
            return result

        # 检查抽取质量
        word_count = len(content)
        if word_count < 100:
            result["error"] = (
                f"抽取内容过短（{word_count} 字），可能是登录墙或付费内容"
            )
            logger.error(result["error"])
            return result

        # 组装最终 Markdown
        markdown_parts = []
        if result["title"]:
            markdown_parts.append(f"# {result['title']}\n")
        meta_line = []
        if result["author"]:
            meta_line.append(f"作者：{result['author']}")
        if result["date"]:
            meta_line.append(f"发布时间：{result['date']}")
        if meta_line:
            markdown_parts.append(f"> {'  '.join(meta_line)}\n")
        markdown_parts.append(content)

        final_markdown = "\n".join(markdown_parts)

        result["content"] = final_markdown
        result["word_count"] = word_count
        result["success"] = True
        result["error"] = None

        # 保存到文件
        if output_path:
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(final_markdown)
            logger.info(f"正文已保存: {output_path}")

        logger.info(f"抽取完成: {word_count} 字, 标题: {result['title']}")

    except Exception as e:
        result["error"] = f"抽取失败: {str(e)}"
        logger.error(result["error"])

    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="网页正文抽取工具")
    parser.add_argument("--url", required=True, help="网页链接")
    parser.add_argument("--output", default=None, help="输出文件路径")
    parser.add_argument("--include-links", action="store_true", help="保留链接")
    parser.add_argument("--include-images", action="store_true", help="保留图片")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    result = extract_content(
        args.url,
        output_path=args.output,
        include_links=args.include_links,
        include_images=args.include_images,
    )

    if result["success"]:
        if not args.output:
            print(result["content"])
        print(f"\n抽取结果: {result['word_count']} 字, 标题: {result['title']}")
    else:
        print(f"抽取失败: {result['error']}")
        sys.exit(1)
