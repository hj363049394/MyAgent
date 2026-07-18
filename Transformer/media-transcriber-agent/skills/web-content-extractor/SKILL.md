---
name: web-content-extractor
description: >
  网页正文抽取 Skill。用于从普通网页文章（非视频平台）中提取正文内容，
  输出干净的 Markdown 文本，跳过 ASR 转录流程。
  支持微信公众号、知乎、博客、新闻等文章类页面。
  当用户发来非视频平台的 http(s) 链接时调用此 Skill。
version: 1.0.0
author: media-transcriber
tags:
  - web
  - extract
  - article
  - readability
---

# web-content-extractor Skill

## 触发条件

当用户发来的链接满足以下条件时调用：
- 是 http(s) 链接
- **不属于**以下视频平台：youtube.com, youtu.be, bilibili.com, b23.tv, xiaoyuzhoufm.com, douyin.com, iesdouyin.com, xiaohongshu.com, xhslink.com
- 即"普通网页文章"（微信公众号、知乎、博客、新闻等）

## 职责

1. 接收网页 URL
2. 用 `trafilatura` 库抽取正文（自动去除导航、广告、侧边栏、评论等噪音）
3. 保留标题、作者、发布时间等元信息（如可获取）
4. 输出干净的 Markdown 文本
5. 将结果传给 `refine` 模块做提纯整理

## 执行步骤

### Step 1: 验证 URL
- 检查 URL 格式是否合法
- 检查是否为视频平台链接（如果是，提示改用下载流程）

### Step 2: 抽取正文
调用 `scripts/extract_web.py`：

```bash
python scripts/extract_web.py --url "<URL>" --output "./tmp/web_content.md"
```

参数说明：
- `--url`：网页链接
- `--output`：输出 Markdown 文件路径（可选，默认输出到 stdout）

### Step 3: 质量校验
- 检查抽取的正文是否为空（可能是 JS 渲染页面，trafilatura 抽不到）
- 检查正文长度是否合理（< 100 字符视为抽取失败）
- 如果抽取失败，尝试备用方案：用 LLM 视觉模型 `glm-4.6v` 截图识别

### Step 4: 输出
- 输出格式：Markdown
- 包含：标题 + 元信息（作者/时间）+ 正文
- 将结果传给 `refine` 模块

## 依赖工具

- `trafilatura`（Python 库）：网页正文抽取
- `requests`（Python 库）：HTTP 请求（trafilatura 内部依赖）

## 异常处理

| 场景 | 处理方式 |
|---|---|
| URL 无法访问（404/超时） | 回复"网页无法访问，请检查链接" |
| 抽取内容为空 | 尝试用浏览器截图 + 视觉模型识别；仍失败则回复"该页面可能是 JS 渲染，无法直接抽取" |
| 抽取内容过短（<100字） | 回复"抽取内容过短，可能是登录墙或付费内容" |
| 需要登录的内容 | 回复"该内容需要登录，请提供 cookie 或复制正文发给我" |

## 与其他 Skill 的协作

```
用户发链接
  ├─ 视频平台链接 → media-transcription-pipeline（下载+ASR）
  └─ 普通网页链接 → web-content-extractor（本 Skill）
                      ↓
                    refine 模块（LLM 提纯）
                      ↓
                    交付（本地 Markdown / 飞书文档）
```

## 示例

**输入**：
```
用户：https://mp.weixin.qq.com/s/xxxxx
```

**处理**：
1. 识别为微信公众号文章 → 调用 web-content-extractor
2. 执行 `python scripts/extract_web.py --url "https://mp.weixin.qq.com/s/xxxxx"`
3. 抽取正文成功 → 传给 refine 模块

**输出**：
```markdown
# 文章标题

> 作者：xxx  发布时间：2026-07-15

[正文内容...]
```
