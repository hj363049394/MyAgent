"""
deliver_feishu.py — 飞书文档交付模块（lark-oapi 封装）

职责：
  1. 创建飞书文档（Wiki 或云文档）
  2. 写入 Markdown 内容
  3. 授权本人为协作者（可管理权限）
  4. 验证文档目录和权限
  5. 返回飞书文档链接

参考：
  - 小D 第 6 节飞书 Bot/App 配置
  - 知识库 02-platform-integrations/01-feishu-bot.md（WebSocket 模式 + 踩坑清单）
  - 飞书开放平台文档：https://open.feishu.cn/document/server-docs/docs/docs-overview

前置条件：
  1. 在飞书开放平台创建企业自建应用
  2. 添加"机器人"能力
  3. 权限管理开通：
     - wiki:wiki（知识库读写）
     - docx:document（文档读写）
     - drive:drive（云空间读写）
     - drive:permission（权限管理）
  4. 复制 App ID 和 App Secret
"""
import os
import sys
import json
import logging
import requests
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# 飞书 API 基础地址
FEISHU_BASE_URL = "https://open.feishu.cn/open-apis"


def _get_tenant_access_token(app_id: str, app_secret: str) -> Optional[str]:
    """获取飞书 tenant_access_token"""
    url = f"{FEISHU_BASE_URL}/auth/v3/tenant_access_token/internal"
    payload = {"app_id": app_id, "app_secret": app_secret}
    try:
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            logger.error(f"获取 token 失败: {data.get('msg')}")
            return None
        token = data.get("tenant_access_token")
        logger.info("获取 tenant_access_token 成功")
        return token
    except Exception as e:
        logger.error(f"获取 token 异常: {e}")
        return None


def create_docx_document(
    token: str,
    title: str,
    folder_token: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    创建飞书文档（docx 类型）

    Args:
        token: tenant_access_token
        title: 文档标题
        folder_token: 文件夹 token（可选，不传则创建在根目录）

    Returns:
        {
            "document_id": str,
            "url": str,
        }
    """
    url = f"{FEISHU_BASE_URL}/docx/v1/documents"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {"title": title}
    if folder_token:
        payload["folder_token"] = folder_token

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            logger.error(f"创建文档失败: {data.get('msg')}")
            return None
        doc = data.get("data", {}).get("document", {})
        doc_id = doc.get("document_id")
        # 飞书文档 URL 格式
        doc_url = f"https://feishu.cn/docx/{doc_id}"
        logger.info(f"文档创建成功: {doc_url}")
        return {"document_id": doc_id, "url": doc_url}
    except Exception as e:
        logger.error(f"创建文档异常: {e}")
        return None


def _markdown_to_blocks(markdown: str) -> list:
    """
    将 Markdown 文本转换为飞书 docx 的 blocks 结构

    飞书 docx 使用 blocks 结构，支持：
    - heading1/heading2/heading3
    - text（段落）
    - bullet_list（无序列表）
    - quote（引用块，block_type=15）
    - callout（高亮块，block_type=34，用于 AI 总结）

    这是一个简化版转换，覆盖常见 Markdown 元素。

    特殊标记：
        <!--AI_SUMMARY_START--> ... <!--AI_SUMMARY_END-->
        标记内的内容会被转换为 callout 高亮块（block_type=34），
        用于在文档顶部展示 AI 核心总结。
    """
    import re

    blocks = []
    lines = markdown.split("\n")
    current_list_items = []

    # AI 总结块状态机：在 START/END 标记之间收集行
    in_summary_block = False
    summary_lines: list = []

    def flush_list():
        nonlocal current_list_items
        if current_list_items:
            blocks.append(
                {
                    "block_type": 12,  # bullet list
                    "bullet": {
                        "elements": [
                            {
                                "text_run": {
                                    "content": item,
                                    "text_element_style": {},
                                }
                            }
                            for item in current_list_items
                        ]
                    },
                }
            )
            current_list_items = []

    def flush_summary():
        """把收集到的 summary_lines 转换为引用块（模拟高亮块效果）

        飞书 callout block (block_type=34) 本身只是容器，内容需要作为子 block
        分两步创建，与当前 create_document_blocks 一次写入模型不兼容。
        因此降级用 quote block (15) + 加粗"💡 AI 总结"标题行模拟高亮块视觉。
        """
        nonlocal summary_lines
        if not summary_lines:
            return
        # 拼接总结文本，去掉首尾空白行
        summary_text = "\n".join(summary_lines).strip()
        if not summary_text:
            summary_lines = []
            return

        # 第一行：加粗的"💡 AI 总结"标题（独立 quote block，视觉更突出）
        blocks.append(
            {
                "block_type": 15,  # quote
                "quote": {
                    "elements": [
                        {
                            "text_run": {
                                "content": "💡 AI 总结",
                                "text_element_style": {"bold": True},
                            }
                        }
                    ]
                },
            }
        )
        # 后续行：总结内容（每个非空行一个 quote block，保持引用块整体视觉）
        for line in summary_text.split("\n"):
            line_stripped = line.strip()
            if not line_stripped:
                continue
            content = _process_inline_formatting(line_stripped)
            blocks.append(
                {
                    "block_type": 15,  # quote
                    "quote": {
                        "elements": [
                            {
                                "text_run": {
                                    "content": content,
                                    "text_element_style": {},
                                }
                            }
                        ]
                    },
                }
            )
        logger.info(f"AI 总结引用块已构建（{len(summary_text)} 字符）")
        summary_lines = []

    for line in lines:
        stripped = line.strip()

        # AI 总结块边界识别（优先级最高）
        if stripped == "<!--AI_SUMMARY_START-->":
            flush_list()
            in_summary_block = True
            summary_lines = []
            continue
        if stripped == "<!--AI_SUMMARY_END-->":
            flush_list()
            flush_summary()
            in_summary_block = False
            continue
        # 在 AI 总结块内：收集所有行（含空行），不解析为其他 block
        if in_summary_block:
            summary_lines.append(line)
            continue

        # 跳过空行
        if not stripped:
            flush_list()
            continue

        # 跳过 Markdown 分隔符（---、***、___），飞书 docx 无对应 block 类型
        if stripped in ("---", "***", "___"):
            flush_list()
            continue

        # 跳过 HTML 注释行（如 <!-- 第 X 段提纯失败 -->）
        if stripped.startswith("<!--") and stripped.endswith("-->"):
            flush_list()
            continue

        # 标题（飞书 docx block_type：heading1=3, heading2=4, heading3=5）
        if stripped.startswith("### "):
            flush_list()
            content = stripped[4:].strip()
            blocks.append(
                {
                    "block_type": 5,  # heading3
                    "heading3": {
                        "elements": [
                            {
                                "text_run": {
                                    "content": content,
                                    "text_element_style": {},
                                }
                            }
                        ]
                    },
                }
            )
        elif stripped.startswith("## "):
            flush_list()
            content = stripped[3:].strip()
            blocks.append(
                {
                    "block_type": 4,  # heading2
                    "heading2": {
                        "elements": [
                            {
                                "text_run": {
                                    "content": content,
                                    "text_element_style": {},
                                }
                            }
                        ]
                    },
                }
            )
        elif stripped.startswith("# "):
            flush_list()
            content = stripped[2:].strip()
            blocks.append(
                {
                    "block_type": 3,  # heading1
                    "heading1": {
                        "elements": [
                            {
                                "text_run": {
                                    "content": content,
                                    "text_element_style": {},
                                }
                            }
                        ]
                    },
                }
            )
        elif stripped.startswith("* ") or stripped.startswith("- "):
            # 列表项
            content = stripped[2:].strip()
            # 处理加粗
            content = _process_inline_formatting(content)
            current_list_items.append(content)
        elif stripped.startswith("> "):
            # 引用（飞书 docx block_type=15）
            flush_list()
            content = stripped[2:].strip()
            content = _process_inline_formatting(content)
            blocks.append(
                {
                    "block_type": 15,  # quote
                    "quote": {
                        "elements": [
                            {
                                "text_run": {
                                    "content": content,
                                    "text_element_style": {},
                                }
                            }
                        ]
                    },
                }
            )
        else:
            # 普通段落（飞书 docx block_type=2 = text）
            flush_list()
            content = _process_inline_formatting(stripped)
            blocks.append(
                {
                    "block_type": 2,  # text paragraph
                    "text": {
                        "elements": [
                            {
                                "text_run": {
                                    "content": content,
                                    "text_element_style": {},
                                }
                            }
                        ]
                    },
                }
            )

    flush_list()
    # 兜底：如果 AI 总结块未闭合（缺少 END 标记），也要把已收集的内容转成 callout
    if in_summary_block:
        logger.warning("AI 总结块缺少 END 标记，按兜底处理")
        flush_summary()
    return blocks


def _process_inline_formatting(text: str) -> str:
    """处理行内格式（简化版：去掉 Markdown 标记，保留纯文本）"""
    import re

    # 去掉加粗标记 **text** -> text
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    # 去掉斜体标记 *text* -> text
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    # 去掉行内代码 `text` -> text
    text = re.sub(r"`(.+?)`", r"\1", text)
    # 去掉链接 [text](url) -> text
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
    return text


def create_document_blocks(
    token: str,
    document_id: str,
    markdown_content: str,
) -> bool:
    """
    向飞书文档写入内容（创建 blocks）

    飞书 API 限制：单次最多创建 50 个 blocks，超过需分批写入。
    参考：https://open.feishu.cn/document/server-docs/docs/docs/docx-v1/document-block-children/create

    Args:
        token: tenant_access_token
        document_id: 文档 ID
        markdown_content: Markdown 内容

    Returns:
        bool: 是否成功
    """
    url = f"{FEISHU_BASE_URL}/docx/v1/documents/{document_id}/blocks/{document_id}/children"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    blocks = _markdown_to_blocks(markdown_content)
    total = len(blocks)
    logger.info(f"准备写入 {total} 个 blocks 到飞书文档")

    # 飞书单次最多 50 个 blocks，分批写入
    BATCH_SIZE = 50
    success_count = 0
    for i in range(0, total, BATCH_SIZE):
        batch = blocks[i : i + BATCH_SIZE]
        batch_no = i // BATCH_SIZE + 1
        total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
        payload = {"children": batch}

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            try:
                resp_data = resp.json()
            except Exception:
                resp_data = resp.text

            if resp.status_code != 200:
                logger.error(
                    f"第 {batch_no}/{total_batches} 批写入失败: HTTP {resp.status_code}"
                )
                logger.error(f"飞书返回: {resp_data}")
                return False

            if not isinstance(resp_data, dict) or resp_data.get("code") != 0:
                logger.error(
                    f"第 {batch_no}/{total_batches} 批写入失败: code={resp_data.get('code') if isinstance(resp_data, dict) else 'N/A'}, msg={resp_data.get('msg') if isinstance(resp_data, dict) else resp_data}"
                )
                logger.error(f"飞书返回: {resp_data}")
                return False

            success_count += len(batch)
            logger.info(
                f"第 {batch_no}/{total_batches} 批写入成功 ({len(batch)} 个 blocks，累计 {success_count}/{total})"
            )
        except Exception as e:
            logger.error(f"第 {batch_no}/{total_batches} 批写入异常: {e}")
            return False

    logger.info(f"文档内容写入完成: 共 {success_count} 个 blocks")
    return True


def add_collaborator(
    token: str,
    file_token: str,
    file_type: str = "docx",
    user_id: str = "",
    member_type: str = "openid",
    perm: str = "full_access",
) -> bool:
    """
    添加协作者并授权

    Args:
        token: tenant_access_token
        file_token: 文件 token（document_id）
        file_type: 文件类型（docx / sheet / bitable / ...）
        user_id: 用户 ID（openid 或 user_id）
        member_type: 成员类型（openid / userid / email / ...）
        perm: 权限（view / edit / full_access）

    Returns:
        bool: 是否成功
    """
    url = f"{FEISHU_BASE_URL}/drive/v1/permissions/{file_token}/members"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    params = {"type": file_type, "need_notification": "false"}
    payload = {
        "member_type": member_type,
        "member_id": user_id,
        "perm": perm,
    }

    try:
        resp = requests.post(
            url, headers=headers, params=params, json=payload, timeout=30
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            logger.error(f"添加协作者失败: {data.get('msg')}")
            return False
        logger.info(f"协作者添加成功: {user_id} ({perm})")
        return True
    except Exception as e:
        logger.error(f"添加协作者异常: {e}")
        return False


def set_public_permission(
    token: str,
    file_token: str,
    file_type: str = "docx",
    link_share_entity: str = "tenant_readable",
    anyone_access: str = "",
) -> bool:
    """
    设置文档的公开访问权限（作为协作者授权失败的降级方案）

    Args:
        token: tenant_access_token
        file_token: 文件 token
        file_type: 文件类型
        link_share_entity: 链接分享范围
            - "tenant_readable"（本企业可阅读）
            - "tenant_editable"（本企业可编辑）
            - "anyone_readable"（任何人可阅读）
        anyone_access: 任何人访问权限

    Returns:
        bool: 是否成功
    """
    url = f"{FEISHU_BASE_URL}/drive/v1/permissions/{file_token}/public"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    params = {"type": file_type}
    payload = {
        "link_share_entity": link_share_entity,
        "external_access_entity": "open",
        "security_entity": "anyone_with_link",
        "comment_entity": "anyone_can_comment",
        "share_entity": "anyone",
    }

    try:
        resp = requests.patch(
            url, headers=headers, params=params, json=payload, timeout=30
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            logger.error(f"设置公开权限失败: {data.get('msg')}")
            return False
        logger.info(f"公开权限设置成功: {link_share_entity}")
        return True
    except Exception as e:
        logger.error(f"设置公开权限异常: {e}")
        return False


def deliver_to_feishu(
    title: str,
    markdown_content: str,
    app_id: Optional[str] = None,
    app_secret: Optional[str] = None,
    user_id: Optional[str] = None,
    folder_token: Optional[str] = None,
    set_public: bool = True,
) -> Dict[str, Any]:
    """
    完整的飞书文档交付流程

    流程：
      1. 获取 tenant_access_token
      2. 创建飞书文档
      3. 写入 Markdown 内容（转换为 blocks）
      4. 授权本人为协作者（可管理权限）
      5. 如果授权失败，降级为设置公开访问权限
      6. 返回飞书文档链接

    Args:
        title: 文档标题
        markdown_content: Markdown 内容
        app_id: 飞书 App ID（默认从环境变量读取）
        app_secret: 飞书 App Secret（默认从环境变量读取）
        user_id: 用户 ID（openid 或 user_id，用于授权协作者）
        folder_token: 文件夹 token（可选）
        set_public: 授权失败时是否降级为公开访问

    Returns:
        {
            "success": bool,
            "document_id": str,
            "url": str,
            "permission_granted": bool,
            "error": str,
        }
    """
    result = {
        "success": False,
        "document_id": None,
        "url": None,
        "permission_granted": False,
        "error": None,
    }

    # 从环境变量读取配置
    app_id = app_id or os.environ.get("FEISHU_APP_ID")
    app_secret = app_secret or os.environ.get("FEISHU_APP_SECRET")
    user_id = user_id or os.environ.get("FEISHU_USER_ID")

    if not app_id or not app_secret:
        result["error"] = "未配置 FEISHU_APP_ID 或 FEISHU_APP_SECRET"
        logger.error(result["error"])
        return result

    # Step 1: 获取 token
    token = _get_tenant_access_token(app_id, app_secret)
    if not token:
        result["error"] = "获取 tenant_access_token 失败"
        return result

    # Step 2: 创建文档
    doc_info = create_docx_document(token, title, folder_token)
    if not doc_info:
        result["error"] = "创建飞书文档失败"
        return result

    result["document_id"] = doc_info["document_id"]
    result["url"] = doc_info["url"]

    # Step 3: 写入内容
    if not create_document_blocks(token, doc_info["document_id"], markdown_content):
        result["error"] = "文档已创建但内容写入失败"
        result["success"] = True  # 文档创建成功了，只是内容写入失败
        return result

    # Step 4: 授权协作者
    if user_id:
        if add_collaborator(token, doc_info["document_id"], user_id=user_id):
            result["permission_granted"] = True
        elif set_public:
            # 降级：设置公开访问权限
            logger.warning("协作者授权失败，降级为设置公开访问权限")
            if set_public_permission(token, doc_info["document_id"]):
                result["permission_granted"] = True
                result["error"] = "文档已创建，协作者授权失败，已设置为公开可访问"
    elif set_public:
        # 没有配置 user_id，直接设置公开访问
        logger.info("未配置 user_id，设置公开访问权限")
        if set_public_permission(token, doc_info["document_id"]):
            result["permission_granted"] = True
            result["error"] = "文档已创建，已设置为公开可访问（未配置协作者）"

    result["success"] = True
    if not result["permission_granted"]:
        result["error"] = "文档已创建，但协作者权限未完成，请手动添加"

    logger.info(
        f"飞书文档交付完成: {result['url']} "
        f"(权限: {'已授权' if result['permission_granted'] else '未完成'})"
    )
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="飞书文档交付工具")
    parser.add_argument("--input", required=True, help="Markdown 文件路径")
    parser.add_argument("--title", required=True, help="文档标题")
    parser.add_argument("--user-id", default=None, help="飞书用户 ID（openid）")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    with open(args.input, "r", encoding="utf-8") as f:
        content = f.read()

    result = deliver_to_feishu(
        title=args.title,
        markdown_content=content,
        user_id=args.user_id,
    )

    print("\n" + "=" * 60)
    if result["success"]:
        print(f"飞书文档交付成功！")
        print(f"  链接: {result['url']}")
        print(f"  权限: {'已授权' if result['permission_granted'] else '未完成'}")
    else:
        print(f"交付失败: {result['error']}")
    print("=" * 60)
