# Persona MAS — Project Skill

Use this skill whenever you work with the **Persona MAS** repository: a multi-agent Telegram assistant built with Python, aiogram, LangChain/OpenAI, and Pydantic.

## Project Overview

- **Language**: Python 3.11+ (strict async/await).
- **Entry point**: `main.py` — starts the aiogram Telegram bot and registers handlers.
- **Architecture**: Orchestrator routes incoming Telegram messages to one of five specialized agents.
- **Agents**: Bio, Cultural, Financial, Psychologist (Personal Confidant), General.
- **Config-driven**: each agent loads its system prompt from `agents/configs/<agent>.md` and user context from `user_profile.json`.
- **Security-critical**: Psychologist-Agent uses isolated encrypted memory in `storage/secure/` and must never share history with other agents or global chat memory.

## Directory Structure

```
.
├── main.py                      # Entry point: bot, dispatcher, polling
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variable template
├── .gitignore                   # Excludes secrets, profiles, secure storage, real configs
├── README.md                    # Public project documentation
├── user_profile.example.json    # Template for user profile
├── .cursorrules                 # Development rules for AI editors
├── .claude/skills/persona-mas.md   # This skill
├── agents/
│   ├── __init__.py
│   ├── bio_agent.py
│   ├── cultural_agent.py
│   ├── financial_agent.py
│   ├── general_agent.py
│   ├── psychologist_agent.py
│   └── configs/
│       ├── bio_agent.md                  # Real config — local only
│       ├── bio_agent_example.md          # Public template
│       ├── cultural_agent.md             # Real config — local only
│       ├── cultural_agent_example.md     # Public template
│       ├── financial_agent.md            # Real config — local only
│       ├── financial_agent_example.md    # Public template
│       ├── general_agent.md              # Real config — local only
│       ├── general_agent_example.md      # Public template
│       ├── psychologist_agent.md         # Real config — local only
│       └── psychologist_agent_example.md # Public template
├── core/
│   ├── __init__.py
│   └── orchestrator.py          # LLM-based router with Pydantic structured output
├── bot/
│   └── __init__.py              # Reserved for future handlers/middleware
├── tools/
│   └── __init__.py              # Reserved for custom tools
└── storage/
    └── secure/                  # Encrypted psychologist memory + children records
        ├── .gitkeep
        └── children_development.example.json
```

## Critical Rules

1. **Never commit real personal data**:
   - `user_profile.json`
   - `.env`
   - `storage/secure/psychologist_history.json`
   - `storage/secure/.psychologist_key`
   - `storage/secure/children_development.json`
   - `agents/configs/*.md` (real configs)

2. **Only templates/examples belong in Git**:
   - `*.example.json`
   - `*_example.md`
   - `.env.example`

3. **Psychologist-Agent isolation**:
   - The Orchestrator only routes messages; it does not inspect psychologist content.
   - Psychologist-Agent uses its own encrypted history, not the global Telegram chat history.
   - No other agent reads from or writes to `storage/secure/`.

4. **Code style**:
   - Explicit type hints on all functions and methods.
   - Strict async/await — no synchronous network calls in the main path.
   - Use `rich` for terminal logging/output.
   - Wrap LLM/JSON parsing calls in robust `try-except` blocks.

## Common Workflows

### Start the bot locally

1. Ensure `.env` exists with `TELEGRAM_BOT_TOKEN` and `OPENAI_API_KEY`.
2. Ensure `user_profile.json` exists and is filled out.
3. Activate virtual environment (`.venv`).
4. Run:
   ```bash
   python main.py
   ```

### Add a new agent

1. Create `agents/<name>_agent.py` following the existing agent pattern:
   - `__init__` loads `.env`, validates `OPENAI_API_KEY`, loads system prompt + user profile.
   - `respond(user_message, history)` builds LangChain messages and calls `ChatOpenAI`.
2. Add system prompt template as `agents/configs/<name>_agent_example.md`.
3. Add the real config `agents/configs/<name>_agent.md` locally and add it to `.gitignore`.
4. Update `core/orchestrator.py`:
   - Add new value to `TargetAgent` Literal.
   - Describe it in `RouteDecision` Field description.
   - Add routing rule to `ROUTER_SYSTEM_PROMPT`.
5. Update `main.py`:
   - Import the new agent.
   - Instantiate it in `main()`.
   - Add it to `register_handlers()` and `dispatch_to_agent()` signatures.
6. Update `README.md` and this skill with the new agent.

### Modify an existing agent

1. Read the relevant agent file and its config.
2. Preserve the existing pattern: load prompt/profile, build messages, call LLM, return string.
3. If changing routing behavior, also update `core/orchestrator.py`.
4. Run a quick syntax/import check:
   ```bash
   python -c "from agents.<agent>_agent import <AgentClass>; print('OK')"
   ```

### Update README

- Keep the README free of real personal details (names, locations, family, finances, goals).
- Use generic placeholders like `<USER_NAME>`, `<AGE>`, `<LOCATION>` when describing features.
- Mention that real configs and profiles are loaded locally and excluded from Git.
- After editing, verify no personal data leaked by grepping for known real values.

### Check for errors / lint

- Run import checks for all agents:
  ```bash
  python -c "from agents.bio_agent import BioAgent; from agents.cultural_agent import CulturalAgent; from agents.financial_agent import FinancialAgent; from agents.general_agent import GeneralAgent; from agents.psychologist_agent import PsychologistAgent; from core.orchestrator import Orchestrator; print('All imports OK')"
  ```
- If available, run `ruff check .` or `mypy` on changed files.
- Test the bot only with `.env` present; do not commit `.env`.

### Prepare for publication

1. Verify `.gitignore` excludes all real data files.
2. Ensure example templates exist for every real config.
3. Check that no real personal data appears in:
   - `README.md`
   - `agents/configs/*.md` (only `*_example.md` should be tracked)
   - any other committed file
4. Run:
   ```bash
   git status
   ```
   Confirm only safe files are tracked.
5. Commit and push.

## Environment Variables

Required:
- `TELEGRAM_BOT_TOKEN`
- `OPENAI_API_KEY`

Optional:
- `PSYCHOLOGIST_ENCRYPTION_KEY` — custom Fernet key for secure memory.
- `TAVILY_API_KEY` / `GOOGLE_API_KEY` — future real-time search for CulturalAgent.

## When in Doubt

- If a change touches `storage/secure/` or psychologist memory, stop and confirm the security implications.
- If a change adds new personal data, ensure it is loaded from `user_profile.json` or local config, never hardcoded.
- When updating documentation, default to generic examples rather than the user's real profile.
