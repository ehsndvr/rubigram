"""A project assistant bot: answers questions about rubigram inside Rubika chats
through any OpenAI-compatible chat-completions API.

Configuration (environment variables):

- ``RUBIGRAM_AI_API_BASE``  e.g. ``https://api.example.com/v1``
- ``RUBIGRAM_AI_API_KEY``
- ``RUBIGRAM_AI_MODEL``     (optional) model name

The bot answers only private text messages that are not our own, keeps a short
per-chat history and grounds every answer in the project documentation.
"""

from __future__ import annotations

import asyncio
import os
from collections import defaultdict, deque
from pathlib import Path

import httpx

from rubigram import Client, filters
from rubigram.types import Message

APP_NAME = "ai_assistant"
MAX_HISTORY_ITEMS = 8
MAX_REPLY_CHARS = 3500
MAX_KNOWLEDGE_CHARS = 12000
MAX_FILE_CHARS = 3500

app = Client(APP_NAME)
histories: dict[str, deque[dict[str, str]]] = defaultdict(lambda: deque(maxlen=MAX_HISTORY_ITEMS))
knowledge = ""
settings: dict[str, str] = {}
http = httpx.AsyncClient(timeout=60.0)


def load_api_settings() -> dict[str, str]:
    api_base = os.getenv("RUBIGRAM_AI_API_BASE")
    api_key = os.getenv("RUBIGRAM_AI_API_KEY")
    if not api_base or not api_key:
        raise RuntimeError("Set RUBIGRAM_AI_API_BASE and RUBIGRAM_AI_API_KEY")
    return {"api_base": api_base.rstrip("/"), "api_key": api_key, "model": os.getenv("RUBIGRAM_AI_MODEL", "gpt-4o-mini")}


def shrink(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    half = max(1, limit // 2)
    return text[:half] + "\n\n[... truncated ...]\n\n" + text[-half:]


def load_project_knowledge() -> str:
    root = Path(__file__).resolve().parents[1]
    files = [root / "README.md", root / "docs" / "method-reference.md", root / "docs" / "updates-and-handlers.md", root / "pyproject.toml"]
    sections = [f"# FILE: {path.name}\n{shrink(path.read_text(encoding='utf-8'), MAX_FILE_CHARS)}" for path in files if path.exists()]
    if not sections:
        raise RuntimeError("Project docs were not found")
    return shrink("\n\n".join(sections), MAX_KNOWLEDGE_CHARS)


def build_messages(chat_id: str, user_text: str) -> list[dict[str, str]]:
    system_prompt = (
        "You are rubigram's project assistant inside a Rubika chat. "
        "Answer only about this project, its API surface, behaviour, examples and current limitations. "
        "Use Persian unless the user explicitly asks for English. Be concise and never invent unsupported features.\n\n"
        f"Project knowledge:\n{knowledge}"
    )
    return [{"role": "system", "content": system_prompt}, *histories[chat_id], {"role": "user", "content": user_text}]


async def ask_ai(chat_id: str, user_text: str) -> str:
    response = await http.post(
        f"{settings['api_base']}/chat/completions",
        headers={"Authorization": f"Bearer {settings['api_key']}", "Content-Type": "application/json"},
        json={"model": settings["model"], "temperature": 0.2, "max_tokens": 700, "messages": build_messages(chat_id, user_text)},
    )
    response.raise_for_status()
    answer = response.json()["choices"][0]["message"]["content"].strip()
    histories[chat_id].append({"role": "user", "content": user_text})
    histories[chat_id].append({"role": "assistant", "content": answer})
    return answer[:MAX_REPLY_CHARS]


@app.on_message(filters.text & filters.private & ~filters.me)
async def handle_text(client: Client, message: Message):
    text = (message.text or "").strip()
    if not text:
        return
    try:
        answer = await ask_ai(message.object_guid or "default", text)
    except Exception as exc:
        answer = f"AI request failed: {exc}"
    await message.reply(answer, parse_mode="markdown")


async def main() -> None:
    global knowledge, settings
    settings = load_api_settings()
    knowledge = load_project_knowledge()
    print("assistant running with model", settings["model"])
    try:
        async with app:
            await app.idle()
    finally:
        await http.aclose()


if __name__ == "__main__":
    asyncio.run(main())
