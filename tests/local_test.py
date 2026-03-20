import asyncio
import os
from collections import defaultdict, deque
from pathlib import Path
from typing import Deque

import httpx

from rubigram import Client, filters, enums

APP_NAME = "my_account"
PREFERRED_MODELS = (
    ("Qwen 3.5", "gapgpt-qwen-3.5"),
    ("GPT-5.2", "gpt-5.2"),
)
CONFIG_PATH = Path.home() / ".continue" / "config.yaml"
MAX_HISTORY_ITEMS = 8
MAX_REPLY_CHARS = 3500
MAX_KNOWLEDGE_CHARS = 12000
MAX_FILE_CHARS = 3500

app = Client(APP_NAME)
_chat_histories: dict[str, Deque[dict[str, str]]] = defaultdict(lambda: deque(maxlen=MAX_HISTORY_ITEMS))
_http_client: httpx.AsyncClient | None = None
_project_knowledge: str | None = None
_api_settings: dict[str, str] | None = None


def _strip_quotes(value: str) -> str:
    return value.strip().strip('"\'')


def _parse_simple_yaml_blocks(text: str) -> list[dict[str, str]]:
    blocks: list[dict[str, str]] = []
    current: dict[str, str] | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("- name:"):
            if current:
                blocks.append(current)
            current = {"name": _strip_quotes(line.split(":", 1)[1])}
            continue
        if current is None or ":" not in line:
            continue
        key, value = line.split(":", 1)
        current[key.strip()] = _strip_quotes(value)

    if current:
        blocks.append(current)
    return blocks


def _is_chat_capable(block: dict[str, str]) -> bool:
    roles = block.get("roles", "")
    return not roles or "chat" in roles


def load_api_settings() -> dict[str, str]:
    env_api_base = os.getenv("RUBIGRAM_AI_API_BASE")
    env_api_key = os.getenv("RUBIGRAM_AI_API_KEY")
    env_model = os.getenv("RUBIGRAM_AI_MODEL")
    if env_api_base and env_api_key:
        return {
            "api_base": env_api_base.rstrip("/"),
            "api_key": env_api_key,
            "model": env_model or PREFERRED_MODELS[0][1],
        }

    if not CONFIG_PATH.exists():
        raise RuntimeError(
            "AI config not found. Set RUBIGRAM_AI_API_BASE/RUBIGRAM_AI_API_KEY or create ~/.continue/config.yaml"
        )

    blocks = _parse_simple_yaml_blocks(CONFIG_PATH.read_text(encoding="utf-8"))
    openai_blocks = [
        block
        for block in blocks
        if block.get("provider") == "openai" and block.get("apiBase") and block.get("apiKey")
    ]
    if not openai_blocks:
        raise RuntimeError("No OpenAI-style model config was found in ~/.continue/config.yaml")

    for preferred_name, preferred_model in PREFERRED_MODELS:
        for block in openai_blocks:
            if block.get("name") == preferred_name and _is_chat_capable(block):
                return {
                    "api_base": block["apiBase"].rstrip("/"),
                    "api_key": block["apiKey"],
                    "model": block.get("model", preferred_model),
                }
        for block in openai_blocks:
            if block.get("model") == preferred_model and _is_chat_capable(block):
                return {
                    "api_base": block["apiBase"].rstrip("/"),
                    "api_key": block["apiKey"],
                    "model": block["model"],
                }

    for block in openai_blocks:
        if _is_chat_capable(block):
            return {
                "api_base": block["apiBase"].rstrip("/"),
                "api_key": block["apiKey"],
                "model": block["model"],
            }

    raise RuntimeError("No chat-capable OpenAI-style model config was found in ~/.continue/config.yaml")


def _shrink_text(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    half = max(1, limit // 2)
    return text[:half] + "\n\n[... truncated ...]\n\n" + text[-half:]


def load_project_knowledge() -> str:
    root = Path(__file__).resolve().parents[1]
    files = [
        root / "README.md",
        root / "docs" / "client-methods.md",
        root / "docs" / "update-message-types.md",
        root / "pyproject.toml",
    ]
    sections: list[str] = []

    for file_path in files:
        if not file_path.exists():
            continue
        file_text = file_path.read_text(encoding="utf-8")
        sections.append(f"# FILE: {file_path.name}\n{_shrink_text(file_text, MAX_FILE_CHARS)}")

    if not sections:
        raise RuntimeError("Project docs were not found")

    return _shrink_text("\n\n".join(sections), MAX_KNOWLEDGE_CHARS)


async def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=60.0)
    return _http_client


def build_messages(chat_id: str, user_text: str) -> list[dict[str, str]]:
    assert _project_knowledge is not None

    system_prompt = (
        "You are Rubigram's project assistant inside a Rubika chat. "
        "Answer only about this Rubigram project, its implemented API surface, behavior, examples, and current limitations. "
        "Use Persian unless the user explicitly asks for English. "
        "Be concise, technically precise, and never invent unsupported features. "
        "If the question is outside the project scope, say that your scope is limited to the Rubigram project.\n\n"
        f"Project knowledge:\n{_project_knowledge}"
    )

    messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": system_prompt,
        }
    ]
    messages.extend(list(_chat_histories[chat_id]))
    messages.append({"role": "user", "content": user_text})
    return messages


async def ask_ai(chat_id: str, user_text: str) -> str:
    assert _api_settings is not None

    client = await get_http_client()
    response = await client.post(
        f"{_api_settings['api_base']}/chat/completions",
        headers={
            "Authorization": f"Bearer {_api_settings['api_key']}",
            "Content-Type": "application/json",
        },
        json={
            "model": _api_settings["model"],
            "temperature": 0.2,
            "max_tokens": 700,
            "messages": build_messages(chat_id, user_text),
        },
    )

    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        body = _shrink_text(exc.response.text.strip(), 600)
        raise RuntimeError(f"HTTP {exc.response.status_code} from AI API: {body}") from exc

    payload = response.json()

    try:
        answer = payload["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected AI response shape: {_shrink_text(str(payload), 600)}") from exc

    _chat_histories[chat_id].append({"role": "user", "content": user_text})
    _chat_histories[chat_id].append({"role": "assistant", "content": answer})
    return answer[:MAX_REPLY_CHARS]


@app.on_message(filters.text & filters.private & ~filters.me)
async def handle_text_message(client: Client, message):
    text = (getattr(message, "text", "") or "").strip()
    if not text:
        return

    chat_id = str(getattr(message, "object_guid", None) or getattr(message, "chat_id", "default"))

    try:
        answer = await ask_ai(chat_id, text)
    except Exception as exc:
        answer = f"AI request failed: {exc}"

    await message.reply(answer[:MAX_REPLY_CHARS], parse_mode=enums.ParseMode.MARKDOWN)


async def main():
    global _api_settings, _project_knowledge

    _api_settings = load_api_settings()
    _project_knowledge = load_project_knowledge()

    print(f"start rubigram ai bot with model: {_api_settings['model']}")
    await app.start()
    await app.idle()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        if _http_client is not None:
            asyncio.run(_http_client.aclose())
