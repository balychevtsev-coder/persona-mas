# Persona MAS — Multi-Agent Personal Telegram Assistant

Персональный Telegram-бот с мультиагентной архитектурой. Сообщения пользователя маршрутизируются центральным **Orchestrator** к одному из пяти специализированных агентов на базе OpenAI GPT-4o / GPT-4o-mini. Каждый агент обладает собственной системной ролью, загружает полный контекст пользователя из `user_profile.json` и отвечает в соответствующем тоне и экспертизе.

> **Важно:** в репозитории содержатся только **шаблоны** профиля и настроек агентов. Заполняйте их своими реальными данными локально — эти файлы исключены из Git через `.gitignore`.

## Возможности

- **Умная маршрутизация**: Orchestrator определяет, какому агенту адресован запрос.
- **5 специализированных агентов**:
  - 🏃 **Bio-Agent** — спорт, бег, OCR, ракеточные виды спорта, кето/IF, биохакинг, сон, восстановление.
  - 🎭 **Cultural-Agent** — классическая музыка, джаз, литература, искусство, культурные события (с заглушкой под real-time поиск).
  - 💰 **Financial-Agent** — инвестиции, недвижимость, карьера, wealth-стратегия, релокация, личные финансы.
  - 🧠 **Psychologist-Agent** — личный confidant, рефлексия, эмоции, дети, семейные ситуации. История хранится изолированно и шифруется.
  - 🙋 **General-Agent** — приветствия, small talk, общие вопросы.
- **Контекст пользователя**: все агенты динамически подгружают локальный `user_profile.json` в системный промпт.
- **Безопасность и приватность**: терапевтический канал Psychologist-Agent не использует общую память чата; его история шифруется Fernet и сохраняется в `storage/secure/psychologist_history.json`.
- **Telegram-интерфейс**: асинхронный бот на `aiogram` с разбиением длинных сообщений на части.
- **Rich-логирование**: красивый вывод в терминале при запуске.

## Стек

- Python 3.11+
- [aiogram](https://docs.aiogram.dev/) — Telegram Bot API
- [LangChain](https://python.langchain.com/) + [langchain-openai](https://pypi.org/project/langchain-openai/) — LLM-вызовы
- [Pydantic](https://docs.pydantic.dev/) — структурированный вывод роутера и экстракторов
- [cryptography](https://cryptography.io/) — шифрование изолированной памяти Psychologist-Agent
- [rich](https://rich.readthedocs.io/) — терминальный UI
- [python-dotenv](https://pypi.org/project/python-dotenv/) — переменные окружения

## Архитектура

```
main.py
├── Orchestrator (route)
│   └── GPT-4o-mini with structured output → target_agent
└── Dispatcher (aiogram)
    └── on_text_message
        └── dispatch_to_agent(...)
            ├── BioAgent
            ├── CulturalAgent
            ├── FinancialAgent
            ├── PsychologistAgent  ← isolated encrypted memory
            └── GeneralAgent
```

Каждый агент:
1. Загружает свой системный промпт из `agents/configs/<agent>.md`.
2. Загружает `user_profile.json` как полный контекст пользователя.
3. Преобразует историю диалога в сообщения LangChain.
4. Вызывает `ChatOpenAI` и возвращает ответ.

Psychologist-Agent дополнительно:
- Использует только собственную зашифрованную историю из `storage/secure/psychologist_history.json`.
- Извлекает из сообщений обновления о детях и сохраняет их в `storage/secure/children_development.json`.
- Не участвует в глобальной истории чата Telegram.

## Структура проекта

```
.
├── main.py                      # Точка входа: бот, диспетчер, polling
├── requirements.txt             # Зависимости Python
├── .env.example                 # Шаблон переменных окружения
├── .gitignore                   # Исключения (.env, профили, secure-хранилище)
├── .cursorrules                 # Правила разработки для Cursor/AI-редакторов
├── README.md                    # Этот файл
├── user_profile.example.json    # Шаблон пользовательского профиля
├── agents/
│   ├── __init__.py
│   ├── bio_agent.py
│   ├── cultural_agent.py
│   ├── financial_agent.py
│   ├── general_agent.py
│   ├── psychologist_agent.py
│   └── configs/
│       ├── bio_agent.md
│       ├── cultural_agent.md
│       ├── financial_agent.md
│       ├── general_agent.md
│       └── psychologist_agent.md
├── core/
│   ├── __init__.py
│   └── orchestrator.py          # Роутер на базе ChatOpenAI + Pydantic
├── bot/
│   └── __init__.py              # Зарезервировано под handlers/middleware
├── tools/
│   └── __init__.py              # Зарезервировано под кастомные инструменты
└── storage/
    └── secure/
        ├── .gitkeep
        └── children_development.example.json  # Шаблон трекера развития детей
```

## Установка

### 1. Клонирование и создание окружения

```bash
git clone https://github.com/balychevtsev-coder/persona-mas.git
cd persona-mas

# Создать виртуальное окружение (рекомендуется)
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Установить зависимости
pip install -r requirements.txt
```

### 2. Настройка окружения

Скопируйте шаблон и заполните реальными значениями:

```bash
cp .env.example .env
```

Отредактируйте `.env`:

```env
TELEGRAM_BOT_TOKEN=your_token_from_BotFather
OPENAI_API_KEY=your_openai_api_key

# Опционально: собственный ключ шифрования для Psychologist-Agent
# PSYCHOLOGIST_ENCRYPTION_KEY=...

# Опционально: ключи для real-time поиска
# TAVILY_API_KEY=...
# GOOGLE_API_KEY=...
```

### 3. Пользовательский профиль

Скопируйте шаблон профиля и заполните его:

```bash
cp user_profile.example.json user_profile.json
```

Отредактируйте `user_profile.json` под себя — все агенты будут использовать эти данные как контекст.

### 4. Конфигурация агентов

Системные промпты агентов находятся в `agents/configs/`. В репозитории они содержат **примерные** роли и плейсхолдеры. Перед запуском замените в них обобщённые данные (`<имя>`, `<возраст>`, `<город>`, `<цели>`) на свои, чтобы агенты отвечали персонализированно.

### 5. Secure-хранилище

Для Psychologist-Agent создайте файл трекера развития детей (если планируете использовать):

```bash
cp storage/secure/children_development.example.json storage/secure/children_development.json
```

Ключ шифрования для `psychologist_history.json` генерируется автоматически при первом запуске, либо берётся из `PSYCHOLOGIST_ENCRYPTION_KEY`.

## Запуск

```bash
python main.py
```

При успешном запуске в терминале появится приветственная панель с именем пользователя, юзернеймом бота и активными агентами. Бот начнёт polling и будет отвечать на сообщения в Telegram.

## Безопасность и приватность

- **Никогда не коммитьте** `user_profile.json`, `.env`, `storage/secure/psychologist_history.json`, `storage/secure/.psychologist_key` и `storage/secure/children_development.json`. Они исключены в `.gitignore`.
- **Также не коммитьте** реальные версии `agents/configs/*.md`, если вы заменили в них примеры на свои персональные данные. Держите свои конфиги локально или в приватном хранилище.
- Psychologist-Agent — единственный агент с доступом к терапевтическим данным и истории. Orchestrator лишь маршрутизирует сообщение, не читая его содержимое.
- История Psychologist-Agent шифруется алгоритмом Fernet (AES-128-CBC + HMAC).
- В репозиторий включены только `.example.json` шаблоны, `.env.example` и примерные `.md`-конфиги.

## Дальнейшее развитие

- [ ] Подключить real-time поиск к Cultural-Agent (Tavily / Google Search).
- [ ] Реализовать финансовые инструменты: калькуляторы, парсеры рыночных данных.
- [ ] Добавить SQLite-хранилище операционного состояния.
- [ ] Интеграция с Ollama для локального инференса (уже заложено в `.cursorrules`).
- [ ] Web-интерфейс помимо Telegram.

## Лицензия

MIT — свободное использование и модификация.
