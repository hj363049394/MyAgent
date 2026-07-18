# 个人微信 ClawBot 对接教程（iLink 协议）

> 资料来源：2026 最新｜Hermes Agent 与微信 ClawBot 对接教程（头条，2026）
> 原文链接：http://m.toutiao.com/group/7629598924122096147/
>
> 本文档基于 Hermes Agent 已安装完成，提供 **Windows + WSL 环境** 下微信 ClawBot 完整对接步骤。

---

## 背景：微信 ClawBot 官方插件

> 参考：微信终于开放官方 Bot API!ClawBot 插件深度解析（CSDN，2026-03-22）
> 原文链接：https://blog.csdn.net/weixin_43025151/article/details/159355899

**2026 年 3 月 22 日**，腾讯微信正式发布 **ClawBot 官方插件**，通过 **iLink 协议**开放了个人微信的 Bot API。这标志着个人微信生态正式进入 Bot 时代，AI 开发者获得了新的机遇。

### 微信做 Agent 的生态底牌

截至 2026 年一季度，微信及 WeChat 合并月活 **14.32 亿**。小程序覆盖数百个细分领域，微信支付、公众号、视频号、服务通知一应俱全 —— 这是微信做 Agent 的生态底牌。

---

## 一、启动网关配置 ⚙️

1. 打开终端，执行配置命令：

```bash
hermes gateway setup
```

2. 终端弹出平台选择列表，用方向键选中 **Weixin/WeChat（微信）**，按回车确认。

---

## 二、微信登录授权

1. 终端提示 `Start QR Login now?[Y/n]`，输入 **Y** 开始二维码登录。
2. 复制终端里的二维码地址，在浏览器打开。
3. 打开手机微信，用**扫一扫**扫描二维码，完成授权登录。
4. 授权成功后，Hermes 会自动把账号 ID / Token 保存到 `~/.hermes/.env` 文件中。

---

## 三、消息权限配置

### 1. 私聊消息授权

选择**第一项（推荐）**：

- ✅ **Use DM pairing approval**（通过配对批准，推荐）
- Allow all direct messages（允许所有私聊）
- Only allow Listed user IDs（仅允许指定用户 ID）
- Disable direct messages（禁用私聊）

### 2. 群聊权限配置

按需求选择，本教程默认选**第一项**：

- ✅ **Disable group chats**（禁用群聊，推荐）
- Allow all group chats（允许所有群聊）
- Only allow Listed group chat IDs（仅允许指定群聊 ID）

---

## 四、主频道与服务配置

1. 提示 `Use your Weixin user ID as the home channel? [Y/n]`，输入 **Y** 确认。
2. 提示 `Install the gateway as a systemd service? [Y/n]`，输入 **Y** 安装后台服务。
3. 选择后台运行方式，**本地电脑选第一项**：
   - ✅ **User service**（无需 sudo，适合笔记本 / 开发机）
   - System service（开机自启，需 sudo，适合服务器）
   - Skip service install for now（暂不安装，临时运行）
4. 输入 **Y** 确认对接配置。

---

## 五、完成配对与对接 ✅

1. 打开微信机器人窗口，发送任意消息，自动生成**一键配对命令**。
2. 重新打开 Ubuntu 终端，粘贴一键配对命令并执行。
3. 终端提示**对接成功**，即可正常使用微信 ClawBot。

---

## 六、能力支持

对接完成后，ClawBot 支持：

- 收发文本
- 收发图片
- 收发视频
- 收发文件
- 多种消息类型

---

## 七、后续维护

如需修改权限或重新登录，只需再次执行：

```bash
hermes gateway setup
```

即可重新配置。

---

## 八、生态补充：wechaty 框架（社区方案）

> 参考：wechat-bot 开源下载和安装教程（AtomGit）

除了官方 ClawBot，社区还有基于 **WeChaty 框架** 的微信机器人方案：

### wechaty 特点

- 基于 WeChaty 框架，集成 DeepSeek/ChatGPT/Kimi/讯飞等 AI 服务
- 支持自动回复消息
- 支持群管理
- 支持好友检测等功能

### 适用场景对比

| 方案 | 协议 | 官方支持 | 推荐度 |
|---|---|---|---|
| **ClawBot 官方插件** | iLink | ✅ 腾讯官方 | ⭐⭐⭐⭐⭐（推荐） |
| **wechaty 框架** | 多种（含非官方） | ❌ 社区维护 | ⭐⭐⭐（备选） |

**结论**：2026 年起，个人微信对接优先选择官方 ClawBot，稳定性和合规性都有保障。
