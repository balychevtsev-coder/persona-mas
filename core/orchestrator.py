"""Orchestrator: маршрутизация сообщений пользователя к целевому агенту."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from rich.console import Console

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"

console = Console()

TargetAgent = Literal[
    "bio_agent",
    "cultural_agent",
    "financial_agent",
    "personal confidant",
    "general",
]


class RouteDecision(BaseModel):
    """Схема маршрутизации: один ключ target_agent."""

    target_agent: TargetAgent = Field(
        description=(
            "Identifier of the agent that should handle the user message. "
            "bio_agent: sports, running, marathon, keto, padel, sleep, biology. "
            "cultural_agent: art, music, books, jazz, piano, saxophone, concerts, "
            "literature, painting, museums, galleries, theater, classical culture. "
            "financial_agent: career, education, relocation (Dubai and general), "
            "personal finance, crypto, real estate, investments, wealth, "
            "ценные бумаги, фондовый рынок, акции, МСФО, инвестиции. "
            "personal confidant: psychologist, coach, reflection, emotions, inner work, "
            "children development, children psychology, parenting, Matvey, Esenia. "
            "general: everything else."
        )
    )


ROUTER_SYSTEM_PROMPT = """You are the Orchestrator Router for Persona MAS.

Analyze the user's message and select exactly one target agent.

Routing rules:
- bio_agent: sports, running, marathon, keto, padel, sleep, biology, biohacking, \
training, recovery, nutrition for performance.
- cultural_agent: art, music, books, literature, jazz, piano, saxophone, concerts, \
galleries, museums, painting, theater, classical culture, fiction, non-fiction \
recommendations.
- financial_agent: career, education, Dubai relocation, relocation in general, \
personal finance, crypto, real estate, investments, wealth, equities, IFRS/МСФО \
consulting finance. Russian keywords: ценные бумаги, фондовый рынок, акции, МСФО, \
инвестиции.
- personal confidant: psychologist, therapy, coaching, reflection, emotions, inner work, \
mental health (non-clinical support), children development, children psychology, \
parenting, family activities for kids, updates about Matvey or Esenia.
- general: greetings (e.g. "привет", "hello"), small talk, general knowledge, \
everyday questions, or topics that do not fit any specialist above.

Return only the structured JSON with the single key "target_agent"."""


class Orchestrator:
    """Router на базе ChatOpenAI с принудительной Pydantic-схемой."""

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.0) -> None:
        load_dotenv(ENV_PATH)

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY не найден в .env или переменных окружения."
            )

        llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=api_key,
        )
        self._router = llm.with_structured_output(RouteDecision)

    async def route(self, user_message: str) -> dict[str, TargetAgent]:
        """Анализирует intent и возвращает {"target_agent": "<agent_id>"}."""
        messages = [
            SystemMessage(content=ROUTER_SYSTEM_PROMPT),
            HumanMessage(content=user_message),
        ]

        try:
            decision: RouteDecision = await self._router.ainvoke(messages)
        except Exception as exc:
            console.print(
                f"[bold red]Orchestrator routing error:[/bold red] {exc}"
            )
            return {"target_agent": "general"}

        return {"target_agent": decision.target_agent}
