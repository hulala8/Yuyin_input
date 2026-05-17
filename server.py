#!/usr/bin/env python3
import json
import os
import pathlib
import urllib.error
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


ROOT = pathlib.Path(__file__).resolve().parent
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8787"))
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")


STYLE_PROMPTS = {
    "natural": "整理成自然、清晰、可直接发送的中文文本。保留说话者本意，删掉口头禅和重复。",
    "message": "整理成简洁礼貌的聊天消息。语气自然，不要过度正式。",
    "email": "整理成一封结构清楚的中文邮件。补全称呼、正文和结尾，但不要编造事实。",
    "bullets": "整理成层次清楚的要点列表。合并重复内容，突出结论和原因。",
    "tasks": "整理成待办清单。每条都用动词开头，并尽量保留时间、对象和条件。",
}


SYSTEM_PROMPT = """你是一个语音输入整理助手。
你的任务不是逐字记录，而是把口语化转写整理成用户真正想输入的文字。
规则：
- 只基于用户提供的内容整理，不编造事实。
- 删除口头禅、重复、停顿词和明显误识别造成的噪声。
- 保留用户的语气、意图、关键细节、数字、日期和专有名词。
- 如果原文同时包含中文和英文，保持自然混合，不强行翻译专有名词。
- 直接输出整理后的文本，不要解释你的处理过程。"""


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_POST(self):
        if self.path != "/api/polish":
            self.send_error(404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            transcript = str(payload.get("transcript", "")).strip()
            style = str(payload.get("style", "natural"))
        except (ValueError, json.JSONDecodeError):
            self._json_response({"error": "请求内容无法读取。"}, status=400)
            return

        if not transcript:
            self._json_response({"error": "还没有可整理的语音文本。"}, status=400)
            return

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            fallback = local_cleanup(transcript)
            self._json_response(
                {
                    "text": fallback,
                    "offline": True,
                    "note": "未检测到 OPENAI_API_KEY，已使用本地基础整理。",
                }
            )
            return

        try:
            text = polish_with_openai(api_key, transcript, style)
            self._json_response({"text": text, "model": OPENAI_MODEL})
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            self._json_response(
                {"error": f"AI 服务返回错误：{exc.code}", "detail": body[:600]},
                status=502,
            )
        except Exception as exc:
            self._json_response({"error": f"整理失败：{exc}"}, status=502)

    def _json_response(self, payload, status=200):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def polish_with_openai(api_key, transcript, style):
    style_instruction = STYLE_PROMPTS.get(style, STYLE_PROMPTS["natural"])
    body = {
        "model": OPENAI_MODEL,
        "input": [
            {
                "role": "system",
                "content": [{"type": "input_text", "text": SYSTEM_PROMPT}],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": f"整理风格：{style_instruction}\n\n原始语音转写：\n{transcript}",
                    }
                ],
            },
        ],
        "temperature": 0.2,
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=45) as response:
        payload = json.loads(response.read().decode("utf-8"))

    output_text = payload.get("output_text")
    if output_text:
        return output_text.strip()

    chunks = []
    for item in payload.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                chunks.append(content["text"])
    return "\n".join(chunks).strip()


def local_cleanup(text):
    replacements = [
        ("嗯", ""),
        ("呃", ""),
        ("就是", ""),
        ("然后然后", "然后"),
        ("那个那个", "那个"),
        ("  ", " "),
    ]
    cleaned = text.strip()
    for old, new in replacements:
        cleaned = cleaned.replace(old, new)
    return cleaned


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Voice input app running at http://{HOST}:{PORT}")
    server.serve_forever()
