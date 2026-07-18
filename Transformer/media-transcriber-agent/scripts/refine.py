"""
refine.py — 文本提纯模块（LLM 调用）

职责：
  1. 接收原始转录稿/字幕/网页正文
  2. 用 LLM（智谱 GLM-4.7）做提纯整理
  3. 输出"分享式提纯版原文"（不是摘要）

提纯标准（参考小D 第 2 节）：
  - 去掉时间戳、说话人标签、寒暄、口水话、重复、残句和 ASR 噪音
  - 修正常见 ASR 错词（人名/公司名/产品名/技术术语）
  - 忠实保留原意、关键判断、案例、数字、类比、论证链和重要原话
  - 不新增事实，不外推，不替原文做过度解释
  - 不写成"一句话总结 / 核心要点 / 启发 / 结论"
  - 按少量大主题 + 二级小标题组织
  - 禁止"其他有效观点"这类垃圾桶标题
  - 重要判断/金句/用户强相关内容适度加粗

参考：prompts/system-prompt.md + config.yaml refine 段
"""
import os
import sys
import logging
from typing import Optional, Dict, Any, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from openai import OpenAI

logger = logging.getLogger(__name__)

# 提纯系统提示词（基于小D 第 8 节 + system-prompt.md）
REFINE_SYSTEM_PROMPT = """你是一个专门负责音视频转录整理的助手。你的任务是把原始转录稿整理成"分享式提纯版原文"。

整理稿要求（必须严格遵守）：
1. 去掉时间戳、说话人标签、寒暄、口水话、重复、残句和明显 ASR 噪音；
2. 修正常见 ASR 错词，尤其是人名、公司名、产品名、技术术语；
3. 忠实保留原意、语气、关键判断、案例、数字、类比、论证链和重要原话；
4. 不新增事实，不外推，不替原文做过度解释；
5. 不写成"一句话总结 / 核心要点 / 启发 / 结论"；
6. 按少量大主题和二级小标题组织，标题要来自真实内容，避免"其他有效观点"这类垃圾桶标题；
7. 重要判断、金句、用户强相关内容适度加粗；
8. 输出格式为 Markdown。

请将原始转录稿整理为可读的中文分享式文稿。"""


def _refine_chunk(
    chunk: str,
    idx: int,
    total: int,
    client,
    model: str,
    fallback_model: str,
) -> Tuple[int, str]:
    """提纯单个分段（主模型 → 降级模型 → 兜底原始文本）

    任何异常都被捕获，不会抛出，避免影响其他并行段。
    返回 (idx, refined_text)。
    """
    logger.info(f"提纯第 {idx}/{total} 段 (模型: {model})...")

    # 单段最多尝试 2 次：主模型 → 降级模型
    for attempt_model in [model, fallback_model]:
        try:
            response = client.chat.completions.create(
                model=attempt_model,
                messages=[
                    {"role": "system", "content": REFINE_SYSTEM_PROMPT},
                    {"role": "user", "content": chunk},
                ],
                temperature=0.3,  # 低温度，保持忠实原意
                max_tokens=4096,
            )
            refined = response.choices[0].message.content.strip()
            if attempt_model != model:
                logger.info(f"第 {idx}/{total} 段用降级模型 {attempt_model} 成功")
            else:
                logger.info(f"第 {idx}/{total} 段完成")
            return idx, refined
        except Exception as e:
            logger.warning(
                f"第 {idx}/{total} 段提纯失败 (模型: {attempt_model}): {e}"
            )
            if attempt_model == model:
                logger.info(f"第 {idx} 段降级到 {fallback_model} 重试...")
                continue
            else:
                # 降级也失败：用原始 chunk 兜底，标记为未提纯
                logger.error(f"第 {idx} 段降级也失败，保留原始文本兜底")
                return idx, f"<!-- 第 {idx} 段提纯失败，以下为原始文本 -->\n\n{chunk}"

    # 理论上不会到达
    return idx, chunk


def refine_text(
    raw_text: str,
    title: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None,
    base_url: str = "https://open.bigmodel.cn/api/paas/v4",
    model: str = "glm-4.7",
    max_chunk_size: int = 5000,
    fallback_model: str = "glm-4.5-air",
) -> Dict[str, Any]:
    """
    用 LLM 提纯原始文本

    Args:
        raw_text: 原始转录稿/字幕/网页正文
        title: 素材标题（可选）
        metadata: 元信息（作者/时间/shownotes 等）
        api_key: LLM API Key（默认从环境变量读取）
        base_url: LLM API 地址
        model: 主模型
        max_chunk_size: 分段最大字符数（避免 token 超限）
        fallback_model: 限流时的降级模型

    Returns:
        {
            "success": bool,
            "refined_text": str,     # 提纯后的 Markdown
            "output_path": str,      # 保存的文件路径
            "error": str,
        }
    """
    # 从环境变量获取 API Key（方式 B 优先：OPENAI_API_KEY；降级方式 A：GLM_API_KEY）
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("GLM_API_KEY")
    if not api_key:
        return {
            "success": False,
            "refined_text": None,
            "output_path": None,
            "error": "未配置 OPENAI_API_KEY 或 GLM_API_KEY 环境变量",
        }

    # 超时与重试配置（避免 GLM-4.7 长尾无响应导致整个 pipeline 卡死）
    #   - timeout: 单次请求 180 秒（GLM-4.7 提纯 5000 字符通常 30-90 秒）
    #   - max_retries: 最多重试 2 次（OpenAI SDK 默认会无限重试）
    import httpx
    _http_client = httpx.Client(timeout=httpx.Timeout(180.0, connect=10.0))
    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
        http_client=_http_client,
        max_retries=2,
    )

    # 组装用户消息
    user_msg_parts = []
    if title:
        user_msg_parts.append(f"标题：{title}")
    if metadata:
        meta_lines = []
        for k, v in metadata.items():
            if v:
                meta_lines.append(f"{k}: {v}")
        if meta_lines:
            user_msg_parts.append("元信息：\n" + "\n".join(meta_lines))
    user_msg_parts.append(f"原始转录稿：\n{raw_text}")
    user_msg = "\n\n".join(user_msg_parts)

    # 分段处理（如果文本过长）
    chunks = _split_text(user_msg, max_chunk_size)
    logger.info(f"文本分段: {len(chunks)} 段, 每段 ≤ {max_chunk_size} 字符")

    current_model = model

    # 方案 A：并行提纯（ThreadPoolExecutor）
    #   - 把 6 段串行调用改为并发，避开"等前一段返回才发下一段"
    #   - max_workers 控制并发数，避免触发 GLM API QPS/并发限制
    #   - 单段异常隔离，不影响其他段
    if len(chunks) == 1:
        # 单段直接同步调用，省去线程池开销
        refined_results = [_refine_chunk(chunks[0], 1, 1, client, current_model, fallback_model)]
    else:
        # max_workers=3：避开 GLM API 4 并发触发的 429 限流（max_workers=4 会触发降级）
        max_workers = min(len(chunks), 3)
        logger.info(f"并行提纯: {len(chunks)} 段, max_workers={max_workers}")
        refined_results = [None] * len(chunks)
        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="refine") as executor:
            futures = {
                executor.submit(
                    _refine_chunk,
                    chunk,
                    idx,
                    len(chunks),
                    client,
                    current_model,
                    fallback_model,
                ): idx
                for idx, chunk in enumerate(chunks, 1)
            }
            for future in as_completed(futures):
                idx, refined = future.result()
                # 按原始顺序保存（idx 从 1 开始）
                refined_results[idx - 1] = (idx, refined)

    refined_chunks = [r[1] for r in refined_results if r]

    # 方案 B：合并分段（跳过 LLM 二次"统一格式"调用，节省 2 分钟左右）
    #   - 分段提纯稿本身已可读，用分隔符拼接即可
    #   - 如需更连贯，可在 system prompt 里要求每段标题层级一致
    if len(refined_chunks) == 1:
        final_text = refined_chunks[0]
    else:
        final_text = "\n\n---\n\n".join(refined_chunks)
        logger.info(f"已合并 {len(refined_chunks)} 段提纯稿（跳过 LLM 统一格式）")

    return {
        "success": True,
        "refined_text": final_text,
        "output_path": None,  # 由调用方决定保存路径
        "error": None,
    }


def generate_ai_summary(
    refined_text: str,
    title: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: str = "https://open.bigmodel.cn/api/paas/v4",
    model: str = "glm-4.7",
    fallback_model: str = "glm-4.5-air",
) -> Dict[str, Any]:
    """基于提纯稿生成 AI 核心总结

    与 refine_text（提纯）不同，本函数做"提炼"：
    1-2 句话概括 + 3-5 个核心要点（要点为简短陈述句，不超过 30 字）

    Args:
        refined_text: 提纯后的完整 Markdown 文本
        title: 素材标题（可选）
        api_key: LLM API Key
        base_url: LLM API 地址
        model: 主模型
        fallback_model: 限流时的降级模型

    Returns:
        {
            "success": bool,
            "summary": str,   # 总结内容（Markdown 格式）
            "error": str,
        }
    """
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("GLM_API_KEY")
    if not api_key:
        return {
            "success": False,
            "summary": None,
            "error": "未配置 OPENAI_API_KEY 或 GLM_API_KEY 环境变量",
        }

    summary_system_prompt = """你是一个内容提炼助手。你的任务是基于给定的整理稿，生成一份精炼的"AI 总结"。

输出要求（必须严格遵守）：
1. 第一部分：1-2 句话概括全文核心（不超过 80 字）；
2. 第二部分：3-5 个核心要点，每个要点为简短陈述句（不超过 30 字），用 Markdown 无序列表（- ）格式；
3. 要点必须来自原文真实内容，不外推、不新增事实；
4. 聚焦"关键判断 / 核心结论 / 重要数据 / 主要建议"，避免细节复述；
5. 不要标题、不要寒暄、不要"以下是总结"等过渡语，直接输出内容；
6. 输出为纯 Markdown，总长度控制在 200-500 字。

示例输出格式：
本文讨论了 XXX 的核心原理，指出 YYY 是关键因素。

- 要点1：简短陈述
- 要点2：简短陈述
- 要点3：简短陈述"""

    # 复用 refine_text 的超时与重试配置
    import httpx
    _http_client = httpx.Client(timeout=httpx.Timeout(180.0, connect=10.0))
    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
        http_client=_http_client,
        max_retries=2,
    )

    # 组装用户消息
    user_msg_parts = []
    if title:
        user_msg_parts.append(f"标题：{title}")
    user_msg_parts.append(f"整理稿内容：\n{refined_text}")
    user_msg = "\n\n".join(user_msg_parts)

    # 主模型 → 降级模型
    for attempt_model in [model, fallback_model]:
        try:
            logger.info(f"生成 AI 总结 (模型: {attempt_model})...")
            response = client.chat.completions.create(
                model=attempt_model,
                messages=[
                    {"role": "system", "content": summary_system_prompt},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.3,
                max_tokens=1024,
            )
            summary = response.choices[0].message.content.strip()
            if attempt_model != model:
                logger.info(f"AI 总结用降级模型 {attempt_model} 成功")
            else:
                logger.info(f"AI 总结生成完成，长度 {len(summary)} 字符")
            return {
                "success": True,
                "summary": summary,
                "error": None,
            }
        except Exception as e:
            logger.warning(f"AI 总结生成失败 (模型: {attempt_model}): {e}")
            if attempt_model == model:
                logger.info(f"降级到 {fallback_model} 重试...")
                continue
            else:
                return {
                    "success": False,
                    "summary": None,
                    "error": f"AI 总结生成失败: {e}",
                }

    return {
        "success": False,
        "summary": None,
        "error": "AI 总结生成失败（未知原因）",
    }


def _split_text(text: str, max_size: int) -> List[str]:
    """将长文本按段落边界分段，每段不超过 max_size 字符"""
    if len(text) <= max_size:
        return [text]

    chunks = []
    current_chunk = ""
    # 按双换行（段落）分割
    paragraphs = text.split("\n\n")

    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 <= max_size:
            current_chunk += ("\n\n" if current_chunk else "") + para
        else:
            if current_chunk:
                chunks.append(current_chunk)
            # 单段超长，按句号硬切
            if len(para) > max_size:
                sentences = para.replace("。", "。\n").split("\n")
                current_chunk = ""
                for sent in sentences:
                    if len(current_chunk) + len(sent) + 1 <= max_size:
                        current_chunk += ("\n" if current_chunk else "") + sent
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = sent
            else:
                current_chunk = para

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def save_refined(refined_text: str, output_dir: str, filename: str) -> str:
    """保存提纯稿到本地 Markdown 文件"""
    os.makedirs(output_dir, exist_ok=True)
    if not filename.endswith(".md"):
        filename += ".md"
    output_path = os.path.join(output_dir, filename)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(refined_text)
    logger.info(f"提纯稿已保存: {output_path}")
    return output_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="文本提纯工具")
    parser.add_argument("--input", required=True, help="原始稿文件路径")
    parser.add_argument("--output-dir", default="./output", help="输出目录")
    parser.add_argument("--title", default=None, help="素材标题")
    parser.add_argument("--model", default="glm-4.7", help="LLM 模型")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    with open(args.input, "r", encoding="utf-8") as f:
        raw_text = f.read()

    result = refine_text(raw_text, title=args.title, model=args.model)

    if result["success"]:
        output_path = save_refined(
            result["refined_text"],
            output_dir=args.output_dir,
            filename=args.title or "refined_output",
        )
        print(f"\n提纯完成！保存到: {output_path}")
    else:
        print(f"提纯失败: {result['error']}")
        sys.exit(1)
