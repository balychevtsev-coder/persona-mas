"""Cultural Agent: искусство, литература, музыка и культурные события."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from rich.console import Console

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SYSTEM_PROMPT_PATH = PROJECT_ROOT / "agents" / "configs" / "cultural_agent.md"
USER_PROFILE_PATH = PROJECT_ROOT / "user_profile.json"
ENV_PATH = PROJECT_ROOT / ".env"

console = Console()

REALTIME_QUERY_PATTERN = re.compile(
    r"\b("
    r"concert|concerts|gig|gigs|exhibition|exhibitions|museum|museums|"
    r"gallery|galleries|festival|festivals|performance|performances|"
    r"theater|theatre|opera|symphony|recital|opening|event|events|"
    r"концерт|концерты|выставк|музе|галере|фестивал|спектакл|"
    r"опера|симфони|джаз|jazz|piano|фортепиано|саксофон|"
    r"when is|where is|upcoming|schedule|афиш|билет|сейчас|ближайш"
    r")\b",
    re.IGNORECASE,
)


class CulturalSearchTool:
    """Заглушка для TavilySearchTool / Google Search (real-time events)."""

    def __init__(self) -> None:
        self._enabled = bool(os.getenv("TAVILY_API_KEY") or os.getenv("GOOGLE_API_KEY"))

    async def search(self, query: str) -> str:
        """Выполняет поиск событий. Пока — stub до подключения API-ключей."""
        if self._enabled:
            # TODO: подключить langchain_community.tools.TavilySearchResults
            # или Google Search API, когда ключи будут в .env
            console.print(
                "[yellow]CulturalSearchTool:[/yellow] API key found, "
                "but integration is not implemented yet."
            )

        console.print(f"[dim]CulturalSearchTool stub query:[/dim] {query}")
        return (
            "[REAL-TIME SEARCH STUB]\n"
            f"Query: {query}\n"
            "Tavily / Google Search is not wired yet. "
            "Provide recommendations from your knowledge base and clearly note "
            "that dates, venues, and ticket availability must be verified online."
        )


class CulturalAgent:
    """Агент искусства, литературы и культурного кураторства для Романа."""

    def __init__(self, model: str = "gpt-4o", temperature: float = 0.5) -> None:
        load_dotenv(ENV_PATH)

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY не найден в .env или переменных окружения."
            )

        self._system_prompt = self._load_system_prompt()
        self._user_profile = self._load_user_profile()
        self._search_tool = CulturalSearchTool()
        self._llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=api_key,
        )

    @staticmethod
    def _load_system_prompt() -> str:
        """Загружает системный промпт из agents/configs/cultural_agent.md."""
        return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")

    @staticmethod
    def _load_user_profile() -> dict[str, Any]:
        """Загружает полный контекст пользователя из user_profile.json."""
        with USER_PROFILE_PATH.open(encoding="utf-8") as profile_file:
            return json.load(profile_file)

    def _build_system_message(self, search_context: str | None = None) -> str:
        """Объединяет системный промпт, профиль и опциональный контекст поиска."""
        profile_context = json.dumps(
            self._user_profile,
            ensure_ascii=False,
            indent=2,
        )
        system_message = (
            f"{self._system_prompt.strip()}\n\n"
            "### USER PROFILE (Full Context)\n"
            f"{profile_context}"
        )
        if search_context:
            system_message += (
                "\n\n### REAL-TIME SEARCH CONTEXT\n"
                f"{search_context}"
            )
        return system_message

    @staticmethod
    def _history_to_messages(history: list[Any]) -> list[BaseMessage]:
        """Преобразует историю диалога в сообщения LangChain."""
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

    @staticmethod
    def _needs_realtime_search(user_message: str) -> bool:
        """Определяет, нужен ли запрос актуальных данных о событиях."""
        return bool(REALTIME_QUERY_PATTERN.search(user_message))

    async def _fetch_realtime_context(self, user_message: str) -> str | None:
        """Запрашивает stub-поиск для сообщений про события и афишу."""
        if not self._needs_realtime_search(user_message):
            return None
        return await self._search_tool.search(user_message)

    async def respond(self, user_message: str, history: list[Any]) -> str:
        """Отправляет контекст в OpenAI и возвращает ответ агента."""
        search_context = await self._fetch_realtime_context(user_message)
        messages: list[BaseMessage] = [
            SystemMessage(content=self._build_system_message(search_context)),
            *self._history_to_messages(history),
            HumanMessage(content=user_message),
        ]

        try:
            response = await self._llm.ainvoke(messages)
        except Exception as exc:
            console.print(f"[bold red]CulturalAgent LLM error:[/bold red] {exc}")
            raise

        content = response.content
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "".join(str(part) for part in content)
        return str(content)
