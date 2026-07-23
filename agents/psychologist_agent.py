"""Psychologist Agent: изолированный Personal Confidant с зашифрованной памятью."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from rich.console import Console

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SYSTEM_PROMPT_PATH = PROJECT_ROOT / "agents" / "configs" / "psychologist_agent.md"
USER_PROFILE_PATH = PROJECT_ROOT / "user_profile.json"
ENV_PATH = PROJECT_ROOT / ".env"
SECURE_DIR = PROJECT_ROOT / "storage" / "secure"
HISTORY_PATH = SECURE_DIR / "psychologist_history.json"
CHILDREN_DEV_PATH = SECURE_DIR / "children_development.json"
KEY_PATH = SECURE_DIR / ".psychologist_key"

console = Console()

DEFAULT_CHILDREN_DEVELOPMENT: dict[str, Any] = {
    "matvey": {
        "current_milestones": [],
        "psychological_notes": [],
        "action_plan_father": "",
    },
    "esenia": {
        "current_milestones": [],
        "psychological_notes": [],
        "action_plan_father": "",
    },
    "joint_activities": {"plans": []},
}


class ChildDevelopmentUpdate(BaseModel):
    """Обновление одного ребёнка в children_development.json."""

    child_key: Literal["matvey", "esenia"] = Field(
        description="matvey = Matvey/Матвей (son, 9). esenia = Esenia/Есения (daughter, 8)."
    )
    psychological_notes: list[str] = Field(
        default_factory=list,
        description="New emotional/psychological observations to append.",
    )
    current_milestones: list[str] = Field(
        default_factory=list,
        description="New achievements, progress markers, or development milestones to append.",
    )


class ChildrenDevelopmentExtraction(BaseModel):
    """Structured extraction of child-related updates from Roman's message."""

    has_updates: bool = Field(
        description="True if the message reports new facts about Matvey or Esenia."
    )
    updates: list[ChildDevelopmentUpdate] = Field(default_factory=list)


class PsychologistMemoryManager:
    """Изолированное хранилище сессий. Не использует глобальную память оркестратора."""

    def __init__(self, history_path: Path = HISTORY_PATH) -> None:
        SECURE_DIR.mkdir(parents=True, exist_ok=True)
        self._history_path = history_path
        self._fernet = Fernet(self._resolve_encryption_key())

    @staticmethod
    def _resolve_encryption_key() -> bytes:
        env_key = os.getenv("PSYCHOLOGIST_ENCRYPTION_KEY")
        if env_key:
            key_bytes = env_key.encode()
            try:
                Fernet(key_bytes)
                return key_bytes
            except ValueError:
                console.print(
                    "[yellow]PsychologistMemoryManager:[/yellow] invalid "
                    "PSYCHOLOGIST_ENCRYPTION_KEY in .env, falling back to key file."
                )

        if KEY_PATH.exists():
            key_bytes = KEY_PATH.read_bytes().strip()
            Fernet(key_bytes)
            return key_bytes

        key = Fernet.generate_key()
        KEY_PATH.write_bytes(key)
        console.print(
            "[yellow]PsychologistMemoryManager:[/yellow] generated local "
            f"encryption key -> {KEY_PATH}"
        )
        return key

    def _load_store(self) -> dict[str, list[dict[str, str]]]:
        if not self._history_path.exists():
            return {}

        raw = self._history_path.read_bytes()
        if not raw:
            return {}

        try:
            decrypted = self._fernet.decrypt(raw)
        except InvalidToken as exc:
            console.print(
                "[bold red]PsychologistMemoryManager:[/bold red] "
                "failed to decrypt history — returning empty store."
            )
            raise ValueError("Invalid psychologist history encryption key.") from exc

        data = json.loads(decrypted.decode("utf-8"))
        if not isinstance(data, dict):
            return {}
        return data

    def _save_store(self, store: dict[str, list[dict[str, str]]]) -> None:
        payload = json.dumps(store, ensure_ascii=False, indent=2).encode("utf-8")
        self._history_path.write_bytes(self._fernet.encrypt(payload))

    def load_session(self, session_id: str) -> list[dict[str, str]]:
        """Загружает историю одной изолированной сессии."""
        store = self._load_store()
        session = store.get(session_id, [])
        if not isinstance(session, list):
            return []
        return [
            {"role": str(item["role"]), "content": str(item["content"])}
            for item in session
            if isinstance(item, dict) and "role" in item and "content" in item
        ]

    def append_turn(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str,
    ) -> None:
        """Сохраняет один turn диалога в зашифрованный файл."""
        store = self._load_store()
        session = store.setdefault(session_id, [])
        session.extend(
            [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": assistant_message},
            ]
        )
        self._save_store(store)

    def clear_session(self, session_id: str) -> None:
        """Удаляет историю одной сессии."""
        store = self._load_store()
        if session_id in store:
            del store[session_id]
            self._save_store(store)


class ChildrenDevelopmentManager:
    """Чтение и запись /storage/secure/children_development.json."""

    def __init__(self, data_path: Path = CHILDREN_DEV_PATH) -> None:
        SECURE_DIR.mkdir(parents=True, exist_ok=True)
        self._data_path = data_path

    def load(self) -> dict[str, Any]:
        if not self._data_path.exists():
            self.save(DEFAULT_CHILDREN_DEVELOPMENT.copy())
            return json.loads(json.dumps(DEFAULT_CHILDREN_DEVELOPMENT))

        with self._data_path.open(encoding="utf-8") as data_file:
            data = json.load(data_file)

        if not isinstance(data, dict):
            return json.loads(json.dumps(DEFAULT_CHILDREN_DEVELOPMENT))
        return data

    def save(self, data: dict[str, Any]) -> None:
        with self._data_path.open("w", encoding="utf-8") as data_file:
            json.dump(data, data_file, ensure_ascii=False, indent=2)

    def format_for_context(self) -> str:
        return json.dumps(self.load(), ensure_ascii=False, indent=2)

    @staticmethod
    def _append_unique(target_list: list[Any], new_items: list[str]) -> None:
        existing = {str(item).strip().lower() for item in target_list}
        for item in new_items:
            normalized = item.strip()
            if normalized and normalized.lower() not in existing:
                target_list.append(normalized)
                existing.add(normalized.lower())

    def apply_updates(self, updates: list[ChildDevelopmentUpdate]) -> bool:
        """Дописывает psychological_notes и current_milestones; возвращает True при изменениях."""
        if not updates:
            return False

        data = self.load()
        changed = False
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        for update in updates:
            child_block = data.get(update.child_key)
            if not isinstance(child_block, dict):
                child_block = {
                    "current_milestones": [],
                    "psychological_notes": [],
                    "action_plan_father": "",
                }
                data[update.child_key] = child_block

            notes: list[Any] = child_block.setdefault("psychological_notes", [])
            milestones: list[Any] = child_block.setdefault("current_milestones", [])

            notes_before = len(notes)
            milestones_before = len(milestones)

            prefixed_notes = [
                f"[{timestamp}] {note}" if not note.startswith("[") else note
                for note in update.psychological_notes
            ]
            prefixed_milestones = [
                f"[{timestamp}] {milestone}" if not milestone.startswith("[") else milestone
                for milestone in update.current_milestones
            ]

            self._append_unique(notes, prefixed_notes)
            self._append_unique(milestones, prefixed_milestones)

            if len(notes) != notes_before or len(milestones) != milestones_before:
                changed = True

        if changed:
            self.save(data)
            console.print(
                "[green]ChildrenDevelopmentManager:[/green] updated "
                f"{self._data_path.name}"
            )

        return changed


class PsychologistAgent:
    """Personal Confidant с изолированной зашифрованной памятью сессий."""

    _EXTRACTION_PROMPT = """You extract structured updates about Roman's children from his message.

Children:
- matvey / Matvey / Матвей — son, 9 years old
- esenia / Esenia / Есения — daughter, 8 years old

Set has_updates=true when Roman reports:
- new achievements, progress, competitions, skills
- emotional states, moods, stress, motivation shifts
- behavioral or psychological observations
- development milestones or setbacks

For each affected child, append concise entries to psychological_notes and/or current_milestones.
Use the same language as Roman's message. Do not invent facts not stated or clearly implied.
If the message is not about the children, return has_updates=false and an empty updates list."""

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.6) -> None:
        load_dotenv(ENV_PATH)

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY не найден в .env или переменных окружения."
            )

        self._system_prompt = self._load_system_prompt()
        self._user_profile = self._load_user_profile()
        self._memory = PsychologistMemoryManager()
        self._children_dev = ChildrenDevelopmentManager()
        self._llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=api_key,
        )
        self._extractor = ChatOpenAI(
            model=model,
            temperature=0.0,
            api_key=api_key,
        ).with_structured_output(ChildrenDevelopmentExtraction)

    @staticmethod
    def _load_system_prompt() -> str:
        """Загружает системный промпт из agents/configs/psychologist_agent.md."""
        return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")

    @staticmethod
    def _load_user_profile() -> dict[str, Any]:
        """Загружает метрики и контекст пользователя из user_profile.json."""
        with USER_PROFILE_PATH.open(encoding="utf-8") as profile_file:
            return json.load(profile_file)

    def _build_system_message(self) -> str:
        profile_context = json.dumps(
            self._user_profile,
            ensure_ascii=False,
            indent=2,
        )
        children_context = self._children_dev.format_for_context()
        return (
            f"{self._system_prompt.strip()}\n\n"
            "### USER PROFILE (General Context — non-therapeutic record)\n"
            f"{profile_context}\n\n"
            "### CHILDREN DEVELOPMENT RECORD (secure/local)\n"
            f"{children_context}\n\n"
            "When Roman shares new information about Matvey or Esenia, acknowledge it "
            "empathetically. Relevant entries will be saved to children_development.json "
            "automatically after your response."
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

    async def _extract_and_persist_child_updates(self, user_message: str) -> bool:
        """Извлекает обновления о детях и сохраняет их в children_development.json."""
        messages = [
            SystemMessage(content=self._EXTRACTION_PROMPT),
            HumanMessage(content=user_message),
        ]

        try:
            extraction: ChildrenDevelopmentExtraction = await self._extractor.ainvoke(
                messages
            )
        except Exception as exc:
            console.print(
                f"[bold red]ChildrenDevelopment extraction error:[/bold red] {exc}"
            )
            return False

        if not extraction.has_updates or not extraction.updates:
            return False

        return self._children_dev.apply_updates(extraction.updates)

    async def respond(
        self,
        user_message: str,
        history: list[Any],
        *,
        session_id: str,
    ) -> str:
        """
        Отправляет сообщение в OpenAI и сохраняет turn в изолированную память.

        Параметр ``history`` игнорируется — используется только зашифрованная
        история из ``/storage/secure/psychologist_history.json``.
        """
        _ = history  # глобальная память оркестратора намеренно не используется

        isolated_history = self._memory.load_session(session_id)
        messages: list[BaseMessage] = [
            SystemMessage(content=self._build_system_message()),
            *self._history_to_messages(isolated_history),
            HumanMessage(content=user_message),
        ]

        try:
            response = await self._llm.ainvoke(messages)
        except Exception as exc:
            console.print(f"[bold red]PsychologistAgent LLM error:[/bold red] {exc}")
            raise

        content = response.content
        if isinstance(content, str):
            reply = content
        elif isinstance(content, list):
            reply = "".join(str(part) for part in content)
        else:
            reply = str(content)

        await self._extract_and_persist_child_updates(user_message)
        self._memory.append_turn(session_id, user_message, reply)
        return reply
