
# Chatbot Project

Use `uv` as the package manager.

A chatbot built with LlamaIndex, designed to roleplay characters from a visual novel.

## Project Structure

```
roleplay-chatbot/
├── adapters/
│   ├── __init__.py
│   ├── cli_adapter.py          # CLI interaction adapter
│   └── onebot_adapter.py       # OneBot v11 adapter
├── config/
│   ├── __init__.py
│   └── settings.py             # Centralized configuration file
├── core/
│   ├── __init__.py
│   ├── admin.py                # Admin logic
│   ├── interfaces.py           # Core abstraction interfaces
│   ├── models.py               # Data models (UserProfile, SessionInfo)
│   └── user_service.py         # Core user service (coordinator)
├── knowledge/
│   ├── roles.json              # Character definitions
│   ├── dialogs.json            # Dialogue data
│   └── background.txt          # Background knowledge
├── services/
│   ├── __init__.py
│   ├── factories.py            # ChatService factory function
│   ├── general_chat_service.py # General chat logic
│   ├── llm_factory.py          # LLM factory function
│   ├── news_service.py         # News fetching functionality
│   ├── roleplay_pwvn/
│   │   ├── __init__.py
│   │   ├── chatter.py          # Chat functionality
│   │   ├── loader.py           # Data loader
│   │   └── query_engine.py     # RAG (Retrieval-Augmented Generation)
│   └── scheduler_service.py    # Scheduled tasks
├── storage/
│   ├── chat-session/           # Chat session storage (auto-generated)
│   └── user-session/           # User session storage (auto-generated)
├── .env.example                # Example environment variables
├── README.md                   # Project documentation
├── requirements.txt            # Python dependencies
└── run.py                      # Main entry point
```
