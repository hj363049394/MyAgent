# 原始资料来源索引

本知识库所有内容均整理自以下公开技术资料，按主题分类整理。如有需要追溯原始细节，可查阅对应链接。

---

## 一、Hermes Agent 框架专题

### 1. Hermes Agent 深度调研
- **标题**：爆火出圈的Hermes Agent深度调研：自进化AI Agent的真相与实践
- **作者 / 平台**：CSDN（weixin_41645817）
- **发布时间**：2026-04-12 原创 / 2026-07-13 推荐
- **链接**：https://blog.csdn.net/weixin_41645817/article/details/160073929
- **整理到**：`01-hermes-agent/01-hermes-agent-overview.md`
- **核心内容**：Hermes Agent 自进化学习闭环、三大核心组件、hermes-agent-self-evolution 五阶段规划与现状

### 2. Hermes Agent 12 大核心集成
- **标题**：Hermes Agent 的 12 大核心集成：把一个 AI 聊天机器人变成全能智能体
- **作者 / 平台**：头条
- **链接**：http://m.toutiao.com/group/7641270291070468642/
- **整理到**：`01-hermes-agent/02-hermes-agent-integrations.md`
- **核心内容**：消息平台、模型、MCP、浏览器、Skills、Curator、记忆、智能家居、语音、Cron、诊断迁移、多 Agent 协作

### 3. Hermes Agent 安装与企业微信对接
- **标题**：Hermes Agent 安装教程：对接企业微信 AI Bot
- **作者 / 平台**：CSDN（u013084266）
- **发布时间**：2026-04-23 原创 / 2026-07-12 推荐
- **链接**：https://blog.csdn.net/u013084266/article/details/160452040
- **整理到**：`01-hermes-agent/03-hermes-agent-installation.md`、`02-platform-integrations/03-wecom-bot.md`
- **核心内容**：完整安装部署流程、企业微信 AI Bot 对接、两种模式对比、踩坑解决方案

### 4. Hermes Agent vs OpenClaw 对比
- **标题**：Hermes Agent vs OpenClaw：AI Agent 框架和工作流控制平台的本质区别
- **作者 / 平台**：头条
- **链接**：http://m.toutiao.com/group/7628927130394509824/
- **核心内容**：Hermes Agent 定位为 AI Agent 框架，OpenClaw 定位为 AI 工作流控制平台

### 5. Hermes Agent 知识点速览
- **标题**：每天吃透一个 AI 知识点 -- Hermes Agent（爱马仕）
- **作者 / 平台**：头条
- **链接**：http://m.toutiao.com/group/7632156040942944818/
- **核心内容**：Hermes（赫尔墨斯）是希腊神话里的信使，框架命名由来

---

## 二、平台对接专题

### 6. 飞书 Bot 部署经验
- **标题**：【AIGC】Hermes Agent 飞书 Bot 部署经验总结
- **作者 / 平台**：博客园 Timmoc
- **发布时间**：2026-07-05
- **链接**：https://www.cnblogs.com/timmoc/p/21137621
- **整理到**：`02-platform-integrations/01-feishu-bot.md`
- **核心内容**：Ubuntu 24.04 虚拟机部署、智谱 bigmodel 接入、飞书 WebSocket 双向消息、完整踩坑清单

### 7. 飞书 Lark OpenAPI MCP
- **标题**：飞书/Lark API 调用工具
- **作者 / 平台**：ModelScope
- **链接**：https://modelscope.cn/mcp/servers/@larksuite/lark-openapi-mcp
- **核心内容**：人工智能助手直接调用飞书/Lark API，文档处理、会话管理、日历安排等自动化场景

### 8. 飞书开放平台 Go SDK
- **标题**：飞书开放平台 Go SDK 使用教程
- **作者 / 平台**：GitCode 博客
- **链接**：https://blog.gitcode.com/de624b74883c1eb8391a6cb43178f66b.html
- **核心内容**：Go 语言库简化飞书开放平台交互，消息发送、用户管理等

### 9. 微信 ClawBot 对接教程
- **标题**：2026 最新｜Hermes Agent 与微信 ClawBot 对接教程
- **作者 / 平台**：头条
- **链接**：http://m.toutiao.com/group/7629598924122096147/
- **整理到**：`02-platform-integrations/02-wechat-clawbot.md`
- **核心内容**：Windows + WSL 环境下微信 ClawBot 完整对接步骤，保姆级手把手教学

### 10. 微信 ClawBot 官方插件解析
- **标题**：微信终于开放官方 Bot API!ClawBot 插件深度解析，AI 开发者的新机遇
- **作者 / 平台**：CSDN（weixin_43025151）
- **发布时间**：2026-03-22
- **链接**：https://blog.csdn.net/weixin_43025151/article/details/159355899
- **整理到**：`02-platform-integrations/02-wechat-clawbot.md`（背景章节）
- **核心内容**：2026 年 3 月 22 日腾讯微信正式发布 ClawBot 官方插件，通过 iLink 协议开放个人微信 Bot API

### 11. 微信 AI 官方内测
- **标题**：微信 AI 官宣：开发者内测启动
- **作者 / 平台**：头条
- **链接**：http://m.toutiao.com/group/7649304029587178020/
- **核心内容**：2026 Q1 微信月活 14.32 亿，小程序/支付/公众号/视频号/服务通知全生态 Agent 能力

### 12. wechaty 微信机器人框架
- **标题**：wechat-bot 开源下载和安装教程
- **作者 / 平台**：AtomGit
- **链接**：https://blog.gitcode.com/2cf6e7cfde8c9f1875d53aa337d12fa3.html
- **整理到**：`02-platform-integrations/02-wechat-clawbot.md`（生态补充章节）
- **核心内容**：基于 WeChaty 框架，集成 DeepSeek/ChatGPT/Kimi/讯飞等 AI 服务

---

## 三、Agent 架构专题

### 13. 8 大 AI Agent 主流架构全拆解
- **标题**：2026硬核干货｜8大AI Agent主流架构全拆解：从基础 ReAct 到全自动自主智能体
- **作者 / 平台**：掘金（用户061770854495，AI 智能体研究所专栏）
- **发布时间**：2026-07-05
- **链接**：https://juejin.cn/post/7658567805047504937
- **整理到**：`03-agent-architecture/01-eight-architectures.md`
- **核心内容**：ReAct、Plan-and-Execute、Multi-Agent、Reflective、Tool-Augmented、Memory-Augmented、RAG Agent、Autonomous Loop 8 大架构完整拆解，含代码案例与选型指南

### 14. 2026 ReAct Agent 架构解析
- **标题**：2026年的 ReAct Agent 架构解析：原生 Tool Calling 与 LangGraph 状态机
- **作者 / 平台**：头条
- **链接**：http://m.toutiao.com/group/7632673388507202102/
- **整理到**：`03-agent-architecture/01-eight-architectures.md`（Tool-Augmented 章节）
- **核心内容**：原生结构化 API tool calling 取代字符串解析，schema 校验由 LLM 提供方负责

### 15. AI Agent 架构设计与实践
- **标题**：AI Agent 架构设计与实践：React、Plan-Exec、Reflect 与混合模式
- **作者 / 平台**：CSDN（qq_48896417）
- **链接**：https://blog.csdn.net/qq_48896417/article/details/160193843
- **核心内容**：用户提问 → LLM 生成答案 → 返回结果 不算真正意义上的 Agent，真正的 Agent 需要多步推理、自主选择工具、维护状态

### 16. 从零手写 AI 编程 Agent
- **标题**：从零手写 AI 编程 Agent!带你实现一个 Mini Cursor（LangChain）
- **作者 / 平台**：CSDN（suger__salt）
- **链接**：https://blog.csdn.net/suger__salt/article/details/162707327
- **核心内容**：ReAct 模式（思考 → 行动 → 观察）、Tool Calling、手写 Mini-Cursor 实战

### 17. 从 ReAct 到 AI Agent 完整实践
- **标题**：别再只会调 LLM 了：从 ReAct 到 AI Agent 的完整实践
- **作者 / 平台**：CSDN（2401_84080967）
- **链接**：https://blog.csdn.net/2401_84080967/article/details/158571602
- **核心内容**：Agent 特征 —— 多步推理、自主选择并调用工具、多轮交互维护状态（记忆）。ReAct 负责怎么想，Agent 负责怎么做

---

## 资料时效与可信度说明

- **整理时间**：2026-07-16
- **资料时效**：2026 年 3 月 - 7 月公开技术文章
- **可信度**：均为公开技术博客或官方文档，部分含一手踩坑经验
- **维护原则**：保留原始技术细节与踩坑经验，便于工程实战直接复用

## 后续补充建议

如需扩展知识库，可继续补充以下方向：
- **Hermes Agent 官方文档**：https://hermes-agent.nousresearch.com/docs/
- **GitHub 源码**：https://github.com/NousResearch/hermes-agent
- **Discord 社区**：https://discord.gg/NousResearch
- **MCP 协议规范**：Model Context Protocol 官方文档
- **LangGraph 状态机**：2026 主流 Agent 编排框架
- **agentskills.io 标准**：Skill 共享与复用开放标准
