import os
import json
import threading
import logging
import uuid
from chatter import Chatter
from dotenv import load_dotenv

from llama_index.core import Settings
from llama_index.llms.deepseek import DeepSeek
from llama_index.llms.ollama import Ollama  # 替换导入

class RoleValidationError(Exception):
    pass

DEFAULT_USER_ROLE="Dave"
DEFAULT_BOT_ROLE="Dean"

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
        raise ValueError(f"Unsupported model: {model_name}")


class SessionManager:
    def __init__(self):
        load_dotenv()
        self._sessions = {}
        self._session_lock = threading.Lock()
        self.load_roles_config()
        self.load_user_sessions()
        self._init_llm()
        
    def load_roles_config(self):
        with open('knowledge/roles.json', 'r', encoding='utf-8') as f:
            self.ROLES_CONFIG = json.load(f)
            self.AVAILABLE_ROLES = self.ROLES_CONFIG.keys()
            
    def load_user_sessions(self):
        try:
            with open('storage/user-session/users.json', 'r', encoding='utf-8') as f:
                self.USER_SESSIONS = json.load(f)
                print("User sessions loaded successfully.")
                print(self.USER_SESSIONS)
        except FileNotFoundError:
            self.USER_SESSIONS = {}

    def save_user_sessions(self):
        with open('storage/user-session/users.json', 'w', encoding='utf-8') as f:
            print("Saving user sessions.")
            print(self.USER_SESSIONS)
            json.dump(self.USER_SESSIONS, f, indent=2)

    def _validate_role(self, role_name: str):
        if role_name not in self.AVAILABLE_ROLES:
            return (f"Role '{role_name}' is not available. Choose from: {self.AVAILABLE_ROLES}")
        return None
    
    def _init_llm(self) -> None:
        try:
            llm = get_llm_by_name("ollama/qwen2.5") if os.getenv("USEOLLAMA") == "true" else get_llm_by_name("deepseek-chat")
            Settings.llm = llm
        except ValueError as e:
            raise RuntimeError(f"LLM initialization failed: {e}")

    def list_sessions(self, user_id: str) -> list:
        """List all sessions for a user"""
        if user_id not in self.USER_SESSIONS:
            return []
        return self.USER_SESSIONS[user_id].get('own_sessions', [])

    def switch_session(self, user_id: str, session_id: str) -> str:
        """Switch to existing session"""
        sessions = self.list_sessions(user_id)
        target = next((s for s in sessions if s['session_id'] == session_id), None)
        if not target:
            return "Session not found"
        self.USER_SESSIONS[user_id].update({
            'session_id': target['session_id'],
            'bot_role': target['bot_role'],
            'user_role': target['user_role'],
        })
        try:
            with self._session_lock:
                # Recreate chatter with stored session data
                self._sessions[user_id] = {
                    'bot_role': target['bot_role'],
                    'user_role': target['user_role'],
                    'chatter': Chatter(
                        bot_role=target['bot_role'],
                        bot_role_info=self.ROLES_CONFIG[target['bot_role']],
                        user_role=target['user_role'],
                        llm=Settings.llm,
                        session_id=session_id
                    ),
                    'session_id': session_id,
                    'llm': Settings.llm
                }
            return f"Switched to session {session_id}"
        except Exception as e:
            return f"Switch failed: {str(e)}"

    def delete_session(self, user_id: str, session_id: str) -> str:
        """Delete a specific session"""
        if user_id not in self.USER_SESSIONS:
            return "User not found"
        
        # Remove from own_sessions
        new_sessions = [s for s in self.USER_SESSIONS[user_id]['own_sessions'] 
                    if s['session_id'] != session_id]
        self.USER_SESSIONS[user_id]['own_sessions'] = new_sessions
        
        # Clear active session if matches
        with self._session_lock:
            if self._sessions.get(user_id, {}).get('session_id') == session_id:
                del self._sessions[user_id]
        
        self.save_user_sessions()
        return f"Deleted session {session_id}"
    
    def load_session(self, user_id: str):
        if user_id not in self.USER_SESSIONS:
            return self.create_session(user_id)

        session_id = self.USER_SESSIONS[user_id]['session_id']
        user_role = self.USER_SESSIONS[user_id]['user_role']
        bot_role = self.USER_SESSIONS[user_id]['bot_role']
        chatter = Chatter(
            bot_role=bot_role,
            bot_role_info=self.ROLES_CONFIG[bot_role],
            user_role=user_role,
            llm=Settings.llm,
            session_id=session_id,
        )

        with self._session_lock:
            self._sessions[user_id] = {
                'bot_role': bot_role,
                'user_role': user_role,
                'chatter': chatter,
                'session_id': session_id,
                'llm': Settings.llm
            }
        return chatter


    def create_session(self, user_id: str, user_role: str=DEFAULT_USER_ROLE, bot_role: str=DEFAULT_BOT_ROLE) -> Chatter:
        self._validate_role(bot_role)
        session_id = uuid.uuid4().hex
        
        # Session data management
        if user_id in self.USER_SESSIONS:
            user_data = self.USER_SESSIONS[user_id]
            if isinstance(user_data, dict):
                own = self.list_sessions(user_id)
                print(f"Update with Own {own}")
                user_data.update({
                    'user_role': user_role, 
                    'bot_role': bot_role, 
                    'own_sessions': [
                        *self.list_sessions(user_id),  # Ensure deep copy
                         {
                        'session_id': session_id,
                        'user_role': user_role,
                        'bot_role': bot_role,
                    }]
                })
            else:  # Backward compatibility
                s = user_data
                self.USER_SESSIONS[user_id] = {
                    'session_id': session_id, 
                    'user_role': user_role, 
                    'bot_role': bot_role, 
                    'own_sessions': [{
                        'session_id': s,
                        'user_role': user_data['user_role'],
                        'bot_role': user_data['bot_role'],
                    }, {
                        'session_id': session_id,
                        'user_role': user_role,
                        'bot_role': bot_role,
                    }]
                }
        else:
            print(f"User {user_id} not found in USER_SESSIONS")
            print(self.USER_SESSIONS)
            self.USER_SESSIONS[user_id] = {
                'session_id': session_id, 
                'user_role': user_role, 
                'bot_role': bot_role, 
                'own_sessions': [{
                    'session_id': session_id,
                    'user_role': user_role,
                    'bot_role': bot_role,
                 }]
             }
        
        self.save_user_sessions()

        # Create Chatter instance
        chatter = Chatter(
            bot_role=bot_role,
            bot_role_info=self.ROLES_CONFIG[bot_role],
            user_role=user_role,
            llm=Settings.llm,
            session_id=session_id,
        )

        with self._session_lock:
            self._sessions[user_id] = {
                'bot_role': bot_role,
                'user_role': user_role,
                'chatter': chatter,
                'session_id': session_id,
                'llm': Settings.llm
            }
        return chatter

    def clear_session(self, user_id: str):
        with self._session_lock:
            if user_id in self._sessions:
                del self._sessions[user_id]

    def handle_command(self, user_id: str, message: str) -> str:
        msg = message.strip().lower()
        
        if msg.startswith('/new'):
            with self._session_lock:
                current_session = self._sessions.get(user_id, {})
            self.clear_session(user_id)
            parts = message.strip().split()
            
            # Default to current roles if available
            new_user = current_session.get('user_role', DEFAULT_USER_ROLE)
            new_bot = current_session.get('bot_role', DEFAULT_BOT_ROLE)
            
            # Parse optional args
            if len(parts) >= 2:
                new_user = parts[1]
            if len(parts) >= 3:
                new_bot = parts[2]
                try:
                    self._validate_role(new_bot)
                except RoleValidationError as e:
                    return str(e)

            # Create new session
            try:
                self.create_session(user_id, new_user, new_bot)
                return f"New session: {new_user} talking to {new_bot}"
            except Exception as e:
                return f"Error: {str(e)}"
        elif msg.startswith(('/switch_bot_role ', '/switch_user_role ', '/switch_llm ')):
            with self._session_lock:
                session = self._sessions.get(user_id)
                if not session:
                    return "No active session. Start a session first."
                chatter = session['chatter']
                if msg.startswith('/switch_bot_role '):
                    new_role = message.split(' ', 1)[1].strip()
                    err = self._validate_role(new_role)
                    if err is not None:
                        return err
                    chatter.bot_role = new_role
                    chatter.bot_role_info = self.ROLES_CONFIG[new_role]
                    return f"Bot role switched to {new_role}"
                
                elif msg.startswith('/switch_user_role '):
                    new_role = message.split(' ', 1)[1].strip()
                    chatter.user_role = new_role
                    return f"User role switched to {new_role}"
                
                elif msg.startswith('/switch_llm '):
                    new_llm = message.split(' ', 1)[1].strip()
                    try:
                        llm = get_llm_by_name(new_llm)
                    except ValueError as err:
                        return str(err)
                    chatter.llm = llm
                    return f"LLM switched to {new_llm}"

        elif msg == '/display_session':
            with self._session_lock:
                session = self._sessions.get(user_id)
                if not session:
                    return "No active session. Start with: /new <role>"
                return f"bot_role: {session['bot_role']} user_role: {session['user_role']} session_id: {session['session_id']}"
        elif message.startswith('/switch_session '):
            session_id = message.split(' ', 1)[1].strip()
            return self.switch_session(user_id, session_id)
        elif message.startswith('/delete_session '):
            session_id = message.split(' ', 1)[1].strip()
            return self.delete_session(user_id, session_id)
        elif message == '/list_sessions':
            sessions = self.list_sessions(user_id)
            return "\n".join([f"{s['session_id']} user: ({s['user_role']})  bot: ({s['bot_role']})" for s in sessions])
        elif message.startswith('/'):
            return "Unknown command."
        else:  # Normal message handling
            with self._session_lock:
                session = self._sessions.get(user_id)
                if not session:
                    return "No active session. Start with: /new <role>"
                return session['chatter'].chat(message)

if __name__ == '__main__':
    import sys
    manager = SessionManager()
    print("Welcome to the chatbot interface.")
    print(f"Available roles: {manager.AVAILABLE_ROLES}")
    
    user = input("Enter your user ID: ").strip()

    try:
        manager.load_session(user)
        print(f"Session created. Type '/new <user_role> <bot_role>' to reset. Commands available:")
        print("/switch_bot_role <role> | /switch_user_role <role> | /switch_llm <model>")
    except (RoleValidationError, RuntimeError) as err:
        print(err)
        sys.exit(1)

    while True:
        msg = input(f"{user}> ").strip()
        if msg.lower() in ('exit', 'quit'):
            print("Goodbye!")
            break
        reply = manager.handle_command(user, msg)
        print(f"Bot> {reply}")