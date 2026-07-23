"""Точка входа Persona Multi-Agent System."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ChatAction, ParseMode
from aiogram.types import Message
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from agents.bio_agent import BioAgent
from agents.cultural_agent import CulturalAgent
from agents.financial_agent import FinancialAgent
from agents.general_agent import GeneralAgent
from agents.psychologist_agent import PsychologistAgent
from core.orchestrator import Orchestrator, TargetAgent

PROJECT_ROOT = Path(__file__).resolve().parent
USER_PROFILE_PATH = PROJECT_ROOT / "user_profile.json"
ENV_PATH = PROJECT_ROOT / ".env"

TELEGRAM_MESSAGE_LIMIT = 4096

console = Console()


def load_user_profile() -> dict[str, Any]:
    """Загружает контекст пользователя из user_profile.json."""
    with USER_PROFILE_PATH.open(encoding="utf-8") as profile_file:
        return json.load(profile_file)


async def initialize_bot(token: str) -> tuple[Bot, Dispatcher]:
    """Создаёт экземпляры Bot и Dispatcher для Telegram API."""
    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher()
    return bot, dispatcher


def split_message(text: str, limit: int = TELEGRAM_MESSAGE_LIMIT) -> list[str]:
    """Делит длинный ответ на части, подходящие для Telegram."""
    if len(text) <= limit:
        return [text]
    return [text[index : index + limit] for index in range(0, len(text), limit)]


async def dispatch_to_agent(
    target_agent: TargetAgent,
    user_message: str,
    history: list[Any],
    session_id: str,
    bio_agent: BioAgent,
    cultural_agent: CulturalAgent,
    financial_agent: FinancialAgent,
    general_agent: GeneralAgent,
    psychologist_agent: PsychologistAgent,
) -> str:
    """Вызывает целевого агента по решению Orchestrator."""
    if target_agent == "bio_agent":
        return await bio_agent.respond(user_message, history)

    if target_agent == "cultural_agent":
        return await cultural_agent.respond(user_message, history)

    if target_agent == "financial_agent":
        return await financial_agent.respond(user_message, history)

    if target_agent == "personal confidant":
        return await psychologist_agent.respond(
            user_message,
            history,
            session_id=session_id,
        )

    if target_agent == "general":
        return await general_agent.respond(user_message, history)

    return await general_agent.respond(user_message, history)


def register_handlers(
    dispatcher: Dispatcher,
    orchestrator: Orchestrator,
    bio_agent: BioAgent,
    cultural_agent: CulturalAgent,
    financial_agent: FinancialAgent,
    general_agent: GeneralAgent,
    psychologist_agent: PsychologistAgent,
) -> None:
    """Регистрирует обработчики Telegram-сообщений."""
    chat_histories: dict[int, list[Any]] = defaultdict(list)

    @dispatcher.message(F.text)
    async def on_text_message(message: Message) -> None:
        if message.text is None or message.from_user is None:
            return

        user_message = message.text.strip()
        if not user_message:
            return

        chat_id = message.chat.id
        history = chat_histories[chat_id]

        await message.bot.send_chat_action(chat_id, ChatAction.TYPING)

        routing = await orchestrator.route(user_message)
        target_agent = routing["target_agent"]
        console.print(
            f"[dim]@{message.from_user.username or message.from_user.id}[/dim] "
            f"→ [bold cyan]{target_agent}[/bold cyan]"
        )

        try:
            reply = await dispatch_to_agent(
                target_agent=target_agent,
                user_message=user_message,
                history=history,
                session_id=str(chat_id),
                bio_agent=bio_agent,
                cultural_agent=cultural_agent,
                financial_agent=financial_agent,
                general_agent=general_agent,
                psychologist_agent=psychologist_agent,
            )
        except Exception as exc:
            console.print(f"[bold red]Agent error:[/bold red] {exc}")
            await message.answer(
                "Something went wrong while generating a response. Please try again."
            )
            return

        if target_agent != "personal confidant":
            history.extend(
                [
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": reply},
                ]
            )

        for chunk in split_message(reply):
            await message.answer(chunk)


async def main() -> None:
    load_dotenv(ENV_PATH)

    profile = load_user_profile()
    user_name: str = profile["personal_info"]["name"]

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        console.print(
            "[bold red]Ошибка:[/bold red] "
            "[cyan]TELEGRAM_BOT_TOKEN[/cyan] не найден в "
            f"[cyan]{ENV_PATH}[/cyan] или переменных окружения."
        )
        sys.exit(1)

    if not os.getenv("OPENAI_API_KEY"):
        console.print(
            "[bold red]Ошибка:[/bold red] "
            "[cyan]OPENAI_API_KEY[/cyan] не найден в "
            f"[cyan]{ENV_PATH}[/cyan] или переменных окружения."
        )
        sys.exit(1)

    bot: Bot | None = None
    try:
        bot, dispatcher = await initialize_bot(token)
        bot_info = await bot.get_me()

        orchestrator = Orchestrator()
        bio_agent = BioAgent()
        cultural_agent = CulturalAgent()
        financial_agent = FinancialAgent()
        general_agent = GeneralAgent()
        psychologist_agent = PsychologistAgent()
        register_handlers(
            dispatcher,
            orchestrator,
            bio_agent,
            cultural_agent,
            financial_agent,
            general_agent,
            psychologist_agent,
        )

        welcome = Text.assemble(
            ("Persona MAS", "bold magenta"),
            (" — система успешно запущена\n\n", "white"),
            ("Пользователь: ", "dim"),
            (user_name, "bold green"),
            ("\nTelegram-бот: ", "dim"),
            (f"@{bot_info.username}", "bold cyan"),
            ("\n\nСтек: ", "dim"),
            ("aiogram · Orchestrator · Bio · Cultural · Financial · Psych · General", "italic"),
        )

        console.print(
            Panel(
                welcome,
                title="[bold]Добро пожаловать[/bold]",
                border_style="green",
                padding=(1, 2),
            )
        )
        console.print("[dim]Polling запущен. Ожидание сообщений…[/dim]")

        await dispatcher.start_polling(bot)
    except Exception as exc:
        console.print(
            Panel(
                f"[bold red]Не удалось запустить систему:[/bold red]\n{exc}",
                title="Ошибка запуска",
                border_style="red",
            )
        )
        sys.exit(1)
    finally:
        if bot is not None:
            await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
