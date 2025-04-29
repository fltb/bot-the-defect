import os
import json
import threading
import logging
from chatter import Chatter
from dotenv import load_dotenv

from llama_index.core import Settings
from llama_index.llms.deepseek import DeepSeek
from llama_index.llms.ollama import Ollama  # 替换导入

# Load available roles from JSON configuration
with open('knowledge/roles.json', 'r', encoding='utf-8') as f:
    ROLES_CONFIG = json.load(f)
    AVAILABLE_ROLES = ROLES_CONFIG.keys()

with open('storage/user-session/users.json', 'r', encoding='utf-8') as f:
    USER_SESSIONS = json.load(f)
    print(USER_SESSIONS)  # Debugging line to check if the file is being read correctly

import uuid

# Global dictionary to hold user sessions
# Key: user identifier, Value: Chatter instance
_sessions = {}
# Lock for thread-safe session management
_session_lock = threading.Lock()

class RoleValidationError(Exception):
    pass

def get_llm_by_name(model_name: str):
    """LLM factory supporting multiple model types"""
    if model_name.startswith("deepseek-"):
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("DeepSeek API key not found in environment variables")
        return DeepSeek(model=model_name, api_key=api_key)
    elif model_name.startswith("ollama/"):
        _, ollama_model = model_name.split("/", 1)
        return Ollama(model=ollama_model)
    else:
        logging.error(f"Unsupported model: {model_name}")
        return Settings.llm


def _validate_role(role_name: str):
    """
    Check if the provided role_name exists in AVAILABLE_ROLES.
    Raises RoleValidationError if invalid.
    """
    if role_name not in AVAILABLE_ROLES:
        raise RoleValidationError(f"Role '{role_name}' is not available. Choose from: {AVAILABLE_ROLES}")


def create_session(user_id: str, user_role:str, bot_role: str) -> Chatter:
    """
    Instantiate a new Chatter session for the user with the given role.
    If a session already exists, it will be replaced.
    """
    _validate_role(bot_role)

    load_dotenv()
    try:
        if os.getenv("USEOLLAMA") == "true":
            llm = get_llm_by_name("ollama/qwen2.5")
        else:
            llm = get_llm_by_name("deepseek-chat")
        Settings.llm = llm
    except ValueError as e:
        print(f"LLM initialization failed: {e}")
        sys.exit(1)

    if user_id in USER_SESSIONS:
        session_id = USER_SESSIONS[user_id]
    else:
        session_id = uuid.uuid4().hex
        USER_SESSIONS[user_id] = session_id
        with open('storage/user-session/users.json', 'w') as f:
            json.dump(USER_SESSIONS, f)

    chatter = Chatter(
        bot_role=bot_role,
        bot_role_info=ROLES_CONFIG[bot_role],
        user_role=user_role,
        llm=Settings.llm,
        session_id=session_id,  # Assuming user_id is unique and can be used as a session ID
    )
    with _session_lock:
        _sessions[user_id] = {
            'bot_role': bot_role,
            'user_role': user_role,
            'role_info': ROLES_CONFIG[bot_role],
            'llm': Settings.llm,
            'session': session_id,
            'chatter': chatter,  # Store the Chatter instance in the session dictionary
        }
    return chatter


def clear_session(user_id: str):
    """
    Clear the Chatter session context for the given user.
    """
    with _session_lock:
        if user_id in _sessions:
            del _sessions[user_id]


def chat_bot(user_id: str, message: str) -> str:
    # Handle clearing context
    if message.strip().lower() == '/clear':
        # ... existing clear logic ...
        USER_SESSIONS[user_id] = None  
        with _session_lock:
            session = _sessions[user_id]
        create_session(
            user_id=user_id,
            user_role=session['user_role'],
            bot_role=session['bot_role'],
        )
        return "Context cleared. Start a new session."
    elif message.startswith('/switch_bot_role '):
        with _session_lock:
            chatter = _sessions[user_id]["chatter"]
        if not chatter:
            return "No active session. Start a session first."
        new_role = message.split(' ', 1)[1].strip()
        try:
            _validate_role(new_role)
            chatter.bot_role = new_role
            chatter.bot_role_info = ROLES_CONFIG[new_role]
            return f"Bot role switched to {new_role}"
        except RoleValidationError as e:
            return str(e)

    elif message.startswith('/switch_user_role '):
        with _session_lock:
            chatter = _sessions[user_id]["chatter"]
        if not chatter:
            return "No active session. Start a session first."
        new_role = message.split(' ', 1)[1].strip()
        chatter.user_role = new_role
        return f"User role switched to {new_role}"

    elif message.startswith('/switch_llm '):
        with _session_lock:
            chatter = _sessions[user_id]["chatter"]
        if not chatter:
            return "No active session. Start a session first."
        new_llm = message.split(' ', 1)[1].strip()
        # Assuming you have LLM configuration logic here
        chatter.llm = get_llm_by_name(new_llm)  # Implement your LLM loader
        return f"LLM switched to {new_llm}"
    elif message.startswith('/display_session'):
        with _session_lock:
            session = _sessions[user_id]
        return str(session)
    else:
        with _session_lock:
            chatter = _sessions[user_id]["chatter"]
        if not chatter:
            return "No active session. Start a session first."
        response = chatter.chat(message)
        return response


if __name__ == '__main__':
    # Example usage in a simple REPL
    import sys

    print("Welcome to the chatbot interface.")
    print(f"Available roles: {AVAILABLE_ROLES}")
    user = input("Enter your user ID: ").strip()
    user_role = input("Enter your user role: ").strip()
    role = input("Select a role to start session: ").strip()
    try:
        create_session(user, user_role, role)
        print(f"Session created for user '{user}' with role '{role}'. Type '/clear' to reset.")
    except RoleValidationError as err:
        print(err)
        sys.exit(1)

    while True:
        msg = input(f"{user}> ").strip()
        if msg.lower() in ('exit', 'quit'):
            print("Goodbye!")
            break
        reply = chat_bot(user, msg)
        print(f"Bot> {reply}")
