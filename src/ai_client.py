"""
Shared AI Client — OpenAI-compatible client for OpenClaw (Gemini backend).
Used by: Chart Vision, RAG Financial Report, Sentiment AI, Macro Sentiment.
"""

import os
import json
import base64
import urllib.request
import urllib.error

# OpenClaw config (already connected to Gemini)
OPENCLAW_URL = os.getenv("OPENCLAW_URL", "http://host.docker.internal:18792/v1")
OPENCLAW_MODEL = os.getenv("OPENCLAW_MODEL", "gemini-2.0-flash")


def chat_completion(messages, model=None, temperature=0.3):
    """
    Send a chat completion request to OpenClaw (OpenAI-compatible API).
    Returns the assistant's message content as string.
    """
    url = f"{OPENCLAW_URL}/chat/completions"
    model = model or OPENCLAW_MODEL

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return f"[AI Error {e.code}]: {body[:500]}"
    except Exception as e:
        return f"[AI Error]: {str(e)}"


def vision_completion(image_bytes, prompt, model=None):
    """
    Send an image + prompt to OpenClaw for vision analysis.
    image_bytes: raw bytes of the image.
    Returns the AI response as string.
    """
    b64 = base64.b64encode(image_bytes).decode("utf-8")

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}"},
                },
            ],
        }
    ]

    return chat_completion(messages, model=model, temperature=0.2)
