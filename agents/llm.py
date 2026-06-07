"""LLM backend switch: Anthropic Claude (default) or a local OpenAI-compatible
server (e.g. Qwen3-80B via MLX). Selected by env LLM_BACKEND=anthropic|local.

Exposes a uniform `client.messages.create(model, max_tokens, system, messages)`
returning an object with `.content[0].text`, so call sites stay unchanged.
"""
import os

BACKEND = os.environ.get("LLM_BACKEND", "anthropic").lower()

if BACKEND == "local":
    from openai import OpenAI

    BASE_URL = os.environ.get("LOCAL_LLM_BASE_URL", "http://100.122.173.111:8080/v1")
    MODEL = os.environ.get("LOCAL_LLM_MODEL", "mlx-community/Qwen3-Next-80B-A3B-Instruct-4bit")
    _oai = OpenAI(base_url=BASE_URL, api_key=os.environ.get("LOCAL_LLM_KEY", "local"))

    class _Block:
        __slots__ = ("text",)
        def __init__(self, text): self.text = text

    class _Resp:
        def __init__(self, text): self.content = [_Block(text)]

    class _Messages:
        def create(self, model=None, max_tokens=1024, system=None, messages=None, temperature=0, **_):
            chat = []
            if system:
                chat.append({"role": "system", "content": system})
            for m in (messages or []):
                c = m.get("content", "")
                if isinstance(c, list):  # anthropic-style content blocks
                    c = " ".join(b.get("text", "") for b in c if isinstance(b, dict))
                chat.append({"role": m.get("role", "user"), "content": c})
            r = _oai.chat.completions.create(
                model=MODEL, messages=chat, max_tokens=max_tokens, temperature=temperature)
            return _Resp(r.choices[0].message.content or "")

    class _Client:
        messages = _Messages()

    client = _Client()
else:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    MODEL = "claude-haiku-4-5-20251001"
