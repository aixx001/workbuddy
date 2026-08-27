# AIXX — 一个 Key，调用全世界的 AI

> Google for AI — One line. Every AI model.

AIXX 是一个统一的 AI 网关 MCP 插件。**一个 API Key** 即可在 CodeBuddy / WorkBuddy 里调用几十个主流大模型（Claude / GPT / Gemini / DeepSeek 等），并支持 AI 出图、AI 视频。接口完全 **OpenAI 兼容**，底层通过 `npx -y aixx-mcp@latest` 启动标准 MCP 服务。

## 能力

- 🧠 **38+ 大模型**：Claude、GPT、Gemini、DeepSeek、Qwen、GLM 等，一个 Key 全通
- 🎨 **AI 出图**：文生图
- 🎬 **AI 视频**：文生视频 / 图生视频
- 🔌 **OpenAI 兼容**：已有的 OpenAI 工具链可直接改 base URL 使用
- 🔑 **凭证隔离**：每个用户填自己的 Key，插件本身不含任何密钥

## 获取 Key

1. 打开控制台注册（新用户送 ¥5 额度）：https://baodan.run/console/
2. 登录后进入「令牌」页，生成你的 API Key
3. 安装插件时把 Key 填入 `AIXX_API_KEY` 即可

## 安装

在 CodeBuddy / WorkBuddy 对话框中：

```
/plugin marketplace add https://gitee.com/kk0803/aixx-workbuddy-marketplace.git
/plugin install aixx@aixx-workbuddy-marketplace
```

或在官方市场收录后直接：

```
/plugin install aixx
```

## 配置

插件通过环境变量读取凭证（`.mcp.json`）：

| 变量 | 说明 |
|---|---|
| `AIXX_API_KEY` | 你的 AIXX 令牌（必填） |
| `AIXX_BASE_URL` | 网关地址，默认 `https://baodan.run/v1` |

## 安全说明

- 插件仅启动一个本地 stdio MCP 服务（`npx aixx-mcp`），不读取、不上传你的任何项目文件
- 所有请求直发 AIXX 网关，凭证只存在你本机的插件配置里
- 源码与 npm 包公开可查：`aixx-mcp`（npm）

## 许可

MIT
