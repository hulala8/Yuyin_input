# AI 语音输入

一个电脑端语音输入原型：浏览器负责听写，本地服务负责把口语化文本整理成可直接使用的文字。

## 运行

```bash
export OPENAI_API_KEY="你的 OpenAI API Key"
python3 server.py
```

打开：

```text
http://127.0.0.1:8787
```

如果没有设置 `OPENAI_API_KEY`，应用仍能运行，但只会做很基础的本地清理。

## 可选配置

```bash
export OPENAI_MODEL="gpt-4.1-mini"
export PORT="8787"
python3 server.py
```

## 当前能力

- 中文语音听写
- 原始口述编辑
- AI 整理成自然文本、聊天消息、邮件、要点或待办
- 一键复制整理稿

## 下一步可以做

- 打包成 macOS 菜单栏应用
- 增加全局快捷键
- 支持按住说话、松开发送
- 接入系统剪贴板，整理后自动粘贴到当前输入框
