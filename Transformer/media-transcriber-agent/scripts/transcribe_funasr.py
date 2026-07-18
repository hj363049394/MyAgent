"""
transcribe_funasr.py — 音频转录模块（funasr + SenseVoice 封装）

职责：
  1. 将音视频文件转码为 16kHz 单声道 wav（ffmpeg）
  2. 用 funasr + SenseVoiceSmall 转录为文字
  3. 清理 SenseVoice 特殊标记（<|zh|><|NEUTRAL|><|Speech|><|withitn|>）
  4. 输出带时间戳的原始转录稿（SRT + JSON）

为什么用 funasr 而不是 faster-whisper：
  - faster-whisper 模型托管在 HuggingFace，国内网络无法直接下载
  - funasr + SenseVoiceSmall 是阿里达摩院方案，modelscope.cn 国内直连
  - SenseVoiceSmall 中文识别效果优于 whisper-medium，速度更快（rtf ~0.2 vs ~0.8）

性能对比（18 分钟音频，CPU）：
  - faster-whisper medium int8: 约 50 分钟
  - funasr + SenseVoiceSmall: 约 3 分 44 秒（快 13 倍）

参考：小D 第 4 节工具栈 + config.yaml asr/transcode 段
"""
import os
import sys
import re
import json
import logging
import glob
from pathlib import Path
from typing import Optional, Dict, Any, List

# 复用 transcribe.py 的验证和转码逻辑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from transcribe import validate_file, transcode_to_wav, _format_timestamp

logger = logging.getLogger(__name__)

# SenseVoice 特殊标记正则（需要清理）
SENSEVOICE_TAGS_RE = re.compile(
    r"<\|[^|]+\|>"  # 匹配 <|zh|> <|NEUTRAL|> <|Speech|> <|withitn|> 等
)


def _clean_sensevoice_text(text: str) -> str:
    """清理 SenseVoice 输出的特殊标记和多余空白"""
    # 移除 <|zh|><|NEUTRAL|><|Speech|><|withitn|> 等标记
    text = SENSEVOICE_TAGS_RE.sub("", text)
    # 折叠多余空白
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _find_local_model(model_name: str = "iic/SenseVoiceSmall") -> Optional[str]:
    """查找已下载到本地的模型路径"""
    # modelscope 下载路径格式: .cache/models/models/{org}--{name}/snapshots/{rev}
    org, _, name = model_name.partition("/")
    dir_name = f"{org}--{name}"
    cache_dir = os.environ.get(
        "MODELSCOPE_CACHE", os.path.join(os.getcwd(), ".cache", "models")
    )
    pattern = os.path.join(cache_dir, "models", dir_name, "snapshots", "*")
    matches = glob.glob(pattern)
    return matches[0] if matches else None


def transcribe_audio_funasr(
    wav_path: str,
    model_name: str = "iic/SenseVoiceSmall",
    language: str = "zh",
    output_dir: str = "./tmp/transcripts",
    local_model_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    用 funasr + SenseVoice 转录音频

    Args:
        wav_path: wav 音频路径
        model_name: modelscope 模型 ID
        language: 语言
        output_dir: 转录稿输出目录
        local_model_dir: 本地模型目录（可选，优先使用）

    Returns:
        {
            "success": bool,
            "text": str,
            "segments": List[Dict],
            "srt_path": str,
            "json_path": str,
            "error": str,
        }
    """
    os.makedirs(output_dir, exist_ok=True)

    result = {
        "success": False,
        "text": "",
        "segments": [],
        "srt_path": None,
        "json_path": None,
        "error": None,
    }

    try:
        from funasr import AutoModel

        # 查找本地模型
        model_path = local_model_dir or _find_local_model(model_name)
        if model_path:
            logger.info(f"使用本地模型: {model_path}")
        else:
            logger.info(f"本地未找到模型，将从 modelscope 下载: {model_name}")
            model_path = model_name

        # 加载 VAD 模型（也尝试本地查找）
        vad_model_name = "fsmn-vad"
        vad_path = _find_local_model(vad_model_name)

        logger.info(f"加载 funasr 模型: {model_path}")
        model_kwargs = {
            "model": model_path,
            "trust_remote_code": True,
            "device": "cpu",
            "disable_update": True,
            "vad_model": vad_path if vad_path else vad_model_name,
            "vad_kwargs": {"max_single_segment_time": 30000},
        }
        # 如果是本地路径，需要 remote_code 指向模型目录
        if model_path and model_path != model_name:
            model_kwargs["remote_code"] = model_path
        if vad_path:
            model_kwargs["vad_model"] = vad_path

        model = AutoModel(**model_kwargs)
        logger.info("模型加载成功")

        logger.info(f"转录中: {wav_path}")
        rec_result = model.generate(
            input=wav_path,
            language=language,
            use_itn=True,
            batch_size_s=60,
            merge_vad=True,
            merge_length_s=15,
        )

        # 解析结果
        segments_list = []
        full_text_parts = []

        if rec_result and len(rec_result) > 0:
            res = rec_result[0]
            raw_text = res.get("text", "")

            # SenseVoice 可能把多段拼在 text 里，每段带标记
            # 按 <|zh|> 标记分段
            if "<|" in raw_text:
                # 按语言标记分割
                parts = re.split(r"(<\|zh\|>|<\|en\|>|<\|ja\|>|<\|ko\|>|<\|yue\|>)", raw_text)
                current_segments = []
                for i in range(0, len(parts) - 1, 2):
                    lang_tag = parts[i + 1] if i + 1 < len(parts) else ""
                    seg_text = parts[i + 2] if i + 2 < len(parts) else ""
                    cleaned = _clean_sensevoice_text(seg_text)
                    if cleaned:
                        current_segments.append(cleaned)

                for idx, seg_text in enumerate(current_segments, 1):
                    segments_list.append(
                        {
                            "id": idx,
                            "start": 0.0,
                            "end": 0.0,
                            "text": seg_text,
                        }
                    )
                    full_text_parts.append(seg_text)
            else:
                cleaned = _clean_sensevoice_text(raw_text)
                full_text_parts.append(cleaned)
                segments_list.append(
                    {"id": 1, "start": 0.0, "end": 0.0, "text": cleaned}
                )

            # 也检查 sentence_info（如果有时间戳）
            sentence_info = res.get("sentence_info", [])
            if sentence_info:
                segments_list = []
                full_text_parts = []
                for i, sent in enumerate(sentence_info, 1):
                    text = _clean_sensevoice_text(sent.get("text", ""))
                    if text:
                        segments_list.append(
                            {
                                "id": i,
                                "start": round(sent.get("start", 0) / 1000, 2),
                                "end": round(sent.get("end", 0) / 1000, 2),
                                "text": text,
                            }
                        )
                        full_text_parts.append(text)

        result["text"] = "\n".join(full_text_parts)
        result["segments"] = segments_list

        # 保存 SRT
        wav_stem = Path(wav_path).stem
        srt_path = os.path.join(output_dir, f"{wav_stem}.srt")
        with open(srt_path, "w", encoding="utf-8") as f:
            if segments_list:
                for seg in segments_list:
                    start = _format_timestamp(seg["start"])
                    end = _format_timestamp(seg["end"])
                    f.write(f"{seg['id']}\n{start} --> {end}\n{seg['text']}\n\n")
            else:
                f.write(f"1\n00:00:00,000 --> 00:00:00,000\n{result['text']}\n")
        result["srt_path"] = srt_path

        # 保存 JSON
        json_path = os.path.join(output_dir, f"{wav_stem}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "text": result["text"],
                    "segments": segments_list,
                    "language": language,
                    "engine": "funasr-sensevoice",
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
        result["json_path"] = json_path

        result["success"] = True
        logger.info(
            f"转录完成: {len(segments_list)} 段, "
            f"{len(result['text'])} 字, "
            f"SRT: {srt_path}, JSON: {json_path}"
        )

    except Exception as e:
        result["error"] = f"转录失败: {str(e)}"
        logger.error(result["error"])

    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="音频转录工具（funasr 版）")
    parser.add_argument("--input", required=True, help="输入音视频文件路径")
    parser.add_argument(
        "--model", default="iic/SenseVoiceSmall", help="modelscope 模型 ID"
    )
    parser.add_argument(
        "--local-model", default=None, help="本地模型目录（可选）"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    validation = validate_file(args.input)
    print(f"文件验证: {validation}")

    if not validation["valid"]:
        sys.exit(1)

    tc_result = transcode_to_wav(args.input)
    if not tc_result["success"]:
        sys.exit(1)

    tr_result = transcribe_audio_funasr(
        tc_result["wav_path"],
        model_name=args.model,
        local_model_dir=args.local_model,
    )
    if tr_result["success"]:
        print(f"\n转录成功！{len(tr_result['text'])} 字")
        print(f"前 200 字: {tr_result['text'][:200]}")
        print(f"SRT: {tr_result['srt_path']}")
    else:
        print(f"转录失败: {tr_result['error']}")
