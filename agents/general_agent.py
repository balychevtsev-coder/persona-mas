"""General Assistant: приветствия и общие вопросы."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from rich.console import Console

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SYSTEM_PROMPT_PATH = PROJECT_ROOT / "agents" / "configs" / "general_agent.md"
USER_PROFILE_PATH = PROJECT_ROOT / "user_profile.json"
ENV_PATH = PROJECT_ROOT / ".env"

console = Console()


class GeneralAgent:
    """Агент для общих сообщений, приветствий и универсальных вопросов."""

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.6) -> None:
        load_dotenv(ENV_PATH)

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY не найден в .env или переменных окружения."
            )

        self._system_prompt = self._load_system_prompt()
        self._user_profile = self._load_user_profile()
        self._llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=api_key,
        )

    @staticmethod
    def _load_system_prompt() -> str:
        return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")

    @staticmethod
    def _load_user_profile() -> dict[str, Any]:
        with USER_PROFILE_PATH.open(encoding="utf-8") as profile_file:
            return json.load(profile_file)

    def _build_system_message(self) -> str:
        profile_context = json.dumps(
            self._user_profile,
            ensure_ascii=False,
            indent=2,
        )
        return (
            f"{self._system_prompt.strip()}\n\n"
            "### USER PROFILE (Full Context)\n"
            f"{profile_context}"
        )

    @staticmethod
    def _history_to_messages(history: list[Any]) -> list[BaseMessage]:
        messages: list[BaseMessage] = []

        for item in history:
            role: str | None = None
            content: str | None = None

            if isinstance(item, dict):
                role = str(item.get("role", "")).lower()
                content = item.get("content")
            elif isinstance(item, (list, tuple)) and len(item) == 2:
                role = str(item[0]).lower()
                content = item[1]

            if not role or content is None:
                continue

            if role in {"user", "human"}:
                messages.append(HumanMessage(content=str(content)))
            elif role in {"assistant", "ai"}:
                messages.append(AIMessage(content=str(content)))

        return messages

    async def respond(self, user_message: str, history: list[Any]) -> str:
        messages: list[BaseMessage] = [
            SystemMessage(content=self._build_system_message()),
            *self._history_to_messages(history),
            HumanMessage(content=user_message),
        ]

        try:
            response = await self._llm.ainvoke(messages)
        except Exception as exc:
            console.print(f"[bold red]GeneralAgent LLM error:[/bold red] {exc}")
            raise

        content = response.content
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "".join(str(part) for part in content)
        return str(content)
