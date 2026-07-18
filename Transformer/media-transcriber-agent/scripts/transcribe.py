"""
transcribe.py — 音频转录模块（faster-whisper 封装）

职责：
  1. 将音视频文件转码为 16kHz 单声道 wav（ffmpeg）
  2. 用 faster-whisper 转录为文字
  3. 输出带时间戳的原始转录稿（SRT + JSON）

参考：小D 第 4 节工具栈 + config.yaml asr/transcode 段
"""
import os
import sys
import json
import subprocess
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

from download import get_ffmpeg_path

logger = logging.getLogger(__name__)

# 支持的输入格式
SUPPORTED_FORMATS = {
    ".mp4", ".mkv", ".mov", ".webm", ".avi",  # 视频
    ".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg", ".opus",  # 音频
}


def validate_file(file_path: str) -> Dict[str, Any]:
    """
    验证文件是否可处理

    Returns:
        {
            "valid": bool,
            "exists": bool,
            "format": str,
            "size_mb": float,
            "error": str,
        }
    """
    path = Path(file_path)
    result = {
        "valid": False,
        "exists": path.exists(),
        "format": path.suffix.lower(),
        "size_mb": 0.0,
        "error": None,
    }

    if not result["exists"]:
        result["error"] = f"文件不存在: {file_path}"
        return result

    result["size_mb"] = round(path.stat().st_size / (1024 * 1024), 2)

    if result["format"] not in SUPPORTED_FORMATS:
        result["error"] = (
            f"不支持的格式: {result['format']}，"
            f"支持: {', '.join(sorted(SUPPORTED_FORMATS))}"
        )
        return result

    result["valid"] = True
    return result


def transcode_to_wav(
    input_path: str,
    output_dir: str = "./tmp/wav",
    sample_rate: int = 16000,
    channels: int = 1,
    codec: str = "pcm_s16le",
) -> Dict[str, Any]:
    """
    将音视频文件转码为 ASR 标准输入格式（16kHz 单声道 wav）

    Returns:
        {
            "success": bool,
            "wav_path": str,
            "error": str,
        }
    """
    os.makedirs(output_dir, exist_ok=True)

    input_file = Path(input_path)
    output_path = os.path.join(output_dir, f"{input_file.stem}.wav")

    ffmpeg = get_ffmpeg_path()
    if not ffmpeg:
        return {"success": False, "wav_path": None, "error": "ffmpeg 不可用"}

    cmd = [
        ffmpeg,
        "-y",  # 覆盖输出
        "-i", input_path,
        "-vn",  # 去掉视频（如有）
        "-ar", str(sample_rate),  # 采样率
        "-ac", str(channels),  # 声道数
        "-c:a", codec,  # 编码
        output_path,
    ]

    try:
        logger.info(f"转码中: {input_path} → {output_path}")
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        logger.info(f"转码完成: {output_path}")
        return {"success": True, "wav_path": output_path, "error": None}
    except subprocess.CalledProcessError as e:
        error_msg = f"转码失败: {e.stderr.decode('utf-8', errors='ignore')}"
        logger.error(error_msg)
        return {"success": False, "wav_path": None, "error": error_msg}


def transcribe_audio(
    wav_path: str,
    model_name: str = "medium",
    device: str = "cpu",
    compute_type: str = "int8",
    language: str = "zh",
    beam_size: int = 5,
    output_dir: str = "./tmp/transcripts",
) -> Dict[str, Any]:
    """
    用 faster-whisper 转录音频

    Returns:
        {
            "success": bool,
            "text": str,              # 全文文本
            "segments": List[Dict],   # 分段（含时间戳）
            "srt_path": str,          # SRT 文件路径
            "json_path": str,         # JSON 文件路径
            "error": str,
        }
    """
    from faster_whisper import WhisperModel

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
        logger.info(
            f"加载 ASR 模型: {model_name} (device={device}, compute_type={compute_type})"
        )
        model = WhisperModel(model_name, device=device, compute_type=compute_type)

        logger.info(f"转录中: {wav_path}")
        segments, info = model.transcribe(
            wav_path,
            language=language,
            beam_size=beam_size,
        )

        # 收集分段
        segments_list = []
        full_text = []
        for i, seg in enumerate(segments, 1):
            segment_data = {
                "id": i,
                "start": round(seg.start, 2),
                "end": round(seg.end, 2),
                "text": seg.text.strip(),
            }
            segments_list.append(segment_data)
            full_text.append(seg.text.strip())

        result["text"] = "\n".join(full_text)
        result["segments"] = segments_list

        # 保存 SRT
        wav_stem = Path(wav_path).stem
        srt_path = os.path.join(output_dir, f"{wav_stem}.srt")
        with open(srt_path, "w", encoding="utf-8") as f:
            for seg in segments_list:
                # 时间戳格式: HH:MM:SS,mmm
                start = _format_timestamp(seg["start"])
                end = _format_timestamp(seg["end"])
                f.write(f"{seg['id']}\n{start} --> {end}\n{seg['text']}\n\n")
        result["srt_path"] = srt_path

        # 保存 JSON
        json_path = os.path.join(output_dir, f"{wav_stem}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "text": result["text"],
                    "segments": segments_list,
                    "language": info.language,
                    "duration": round(info.duration, 2),
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
        result["json_path"] = json_path

        result["success"] = True
        logger.info(
            f"转录完成: {len(segments_list)} 段, "
            f"SRT: {srt_path}, JSON: {json_path}"
        )

    except Exception as e:
        result["error"] = f"转录失败: {str(e)}"
        logger.error(result["error"])

    return result


def _format_timestamp(seconds: float) -> str:
    """将秒数格式化为 SRT 时间戳: HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="音频转录工具")
    parser.add_argument("--input", required=True, help="输入音视频文件路径")
    parser.add_argument("--check-only", action="store_true", help="仅验证文件")
    parser.add_argument("--transcode-only", action="store_true", help="仅转码")
    parser.add_argument("--model", default="medium", help="ASR 模型")
    parser.add_argument("--device", default="cpu", help="设备 cpu/cuda")
    parser.add_argument("--compute-type", default="int8", help="计算类型")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    # 验证文件
    validation = validate_file(args.input)
    print(f"文件验证: {validation}")

    if not validation["valid"]:
        sys.exit(1)

    if args.check_only:
        sys.exit(0)

    # 转码
    tc_result = transcode_to_wav(args.input)
    print(f"转码结果: {tc_result}")

    if not tc_result["success"] or args.transcode_only:
        sys.exit(0 if tc_result["success"] else 1)

    # 转录
    tr_result = transcribe_audio(
        tc_result["wav_path"],
        model_name=args.model,
        device=args.device,
        compute_type=args.compute_type,
    )
    print(f"转录结果: {tr_result}")
