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

os.makedirs('storage/user-session/', exist_ok=True)
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
        self.DIALOGS_BOT = {
            'session_not_found': f"[目标]根据当前用户会话指定的角色模块提供对话\n[定义]模块\n[错误]无法检索到当前用户会话\n[提示]使用命令创建会话 /new [用户角色] [机器人角色]\n[提示]可选机器人角色: {', '.join(self.AVAILABLE_ROLES)}",
        }
        self. _COMMANDS = {
        'new': {
            'aliases': ['n'],
            'handler': self._handle_new,
            'help': '/new [user] [bot] - 创建新会话'
        },
        'switch_llm': {
            'aliases': ['sl', 'model'],
            'handler': self._handle_switch_llm,
            'help': '/sl <model> - 切换大模型'
        },
        'display_session': {
            'aliases': ['ds'],
            'handler': self._handle_display,
            'help': '/ds - 显示当前会话信息'
        },
        'switch_session': {
            'aliases': ['ss'],
            'handler': self._handle_switch_session,
            'help': '/ss <id> - 根据 ID 切换到其他会话'
        },
        'delete_session': {
            'aliases': ['dels'],
            'handler': self._handle_delete_session,
            'help': '/dels <id> - 根据 ID 删除会话'
        },
        'list_sessions': {
            'aliases': ['ls'],
            'handler': self._handle_list_sessions,
            'help': '/ls - 列出当前用户所有会话'
        },
        'help': {
            'aliases': ['h', '?'],
            'handler': self._handle_help,
            'help': '/h - 打印帮助信息'
        }
    }
        
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
            json.dump(self.USER_SESSIONS, f, indent=2)

    def _validate_role(self, role_name: str):
        if role_name not in self.AVAILABLE_ROLES:
            raise ValueError(f"[错误]无法检索到角色： '{role_name}'\n[提示]可用角色列表: {self.AVAILABLE_ROLES}")
        return None
    
    def _init_llm(self) -> None:
        try:
            llm = get_llm_by_name("ollama/qwen2.5") if os.getenv("USEOLLAMA") == "true" else get_llm_by_name("deepseek-chat")
            Settings.llm = llm
        except ValueError as e:
            raise RuntimeError(f"[错误]大模型初始化失败: {e}")

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
            return self.DIALOGS_BOT["session_not_found"]
        self.USER_SESSIONS[user_id].update({
            'session_id': target['session_id'],
            'bot_role': target['bot_role'],
            'user_role': target['user_role'],
        })
        self.save_user_sessions()
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
        except Exception as e:
            return f"[错误]切换会话失败: {str(e)}"
        return f"[信息]切换到会话： {session_id}"

    def delete_session(self, user_id: str, session_id: str) -> str:
        """Delete a specific session"""
        if user_id not in self.USER_SESSIONS:
            return self.DIALOGS_BOT['session_not_found']
        
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
    
    def modify_session(self, user_id: str, session_id: str, user_role: str=None, bot_role: str=None) -> str:
        """Delete a specific session"""
        if user_id not in self.USER_SESSIONS:
            return "User not found"

        try:
            with self._session_lock:
                session = self._sessions.get(user_id)
                if not session: return "No active session"
                self._validate_role(bot_role)
        except RoleValidationError as e:
            return str(e)
        
        modified = False
        # Update stored sessions
        for session in self.USER_SESSIONS[user_id]['own_sessions']:
            if session['session_id'] == session_id:
                if user_role is not None:
                    session['user_role'] = user_role
                if bot_role is not None:
                    session['bot_role'] = bot_role
                modified = True
                break
        
        if self.USER_SESSIONS[user_id]['session_id'] == session_id:
            if user_role is not None:
                self.USER_SESSIONS[user_id]['user_role'] = user_role
            if bot_role is not None:
                self.USER_SESSIONS[user_id]['bot_role'] = bot_role
            modified = True
        
        # Update active session if needed
        with self._session_lock:
            active_session = self._sessions.get(user_id)
            if active_session and active_session['session_id'] == session_id:
                if user_role is not None:
                    active_session['user_role'] = user_role
                    active_session['chatter'].user_role = user_role
                if bot_role is not None:
                    active_session['bot_role'] = bot_role
                    active_session['chatter'].bot_role = bot_role
                    active_session['chatter'].bot_role_info = self.ROLES_CONFIG.get(bot_role, "")
        
        if not modified:
            return f"Session {session_id} not found"
        
        self.save_user_sessions()
        return f"[信息]更新会话 {session_id}: user={user_role or 'unchanged'}, bot={bot_role or 'unchanged'}"
    
    def modify_active_session(self, user_id: str, user_role: str=None, bot_role: str=None) -> str:
        with self._session_lock:
            session = self._sessions.get(user_id, {})
            session_id = session.get('session_id', None)
        return self.modify_session(user_id, session_id, user_role, bot_role)       

    def load_session(self, user_id: str):
        if user_id not in self.USER_SESSIONS:
            return None

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
                    'session_id': session_id,
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
        parts = message.lstrip('/').split(maxsplit=1)
        cmd_key = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ''

        for cmd, meta in self._COMMANDS.items():
            if cmd_key in [cmd] + meta['aliases']:
                handler = meta['handler']
                res = handler(user_id, args)
                return res
        return f"[错误]无法检索到指令 {cmd_key}\n[提示]使用 /help 获取指令使用信息"

    def _handle_help(self, user_id: str, args: str) -> str:
        help_lines = [meta['help'] for meta in self._COMMANDS.values()]
        return "[提示]可用命令:\n" + "\n".join(help_lines)

    def _handle_new(self, user_id: str, args: str) -> str:
        parts = args.split()
        try:
            with self._session_lock:
                current = self._sessions.get(user_id, {})
                new_user = parts[0] if len(parts)>=1 else current.get('user_role', DEFAULT_USER_ROLE)
                new_bot = parts[1] if len(parts)>=2 else current.get('bot_role', DEFAULT_BOT_ROLE)
                self._validate_role(new_bot)
            self.create_session(user_id, new_user, new_bot)
            return f"New session: {new_user} ↔ {new_bot}"
        except Exception as e:
            return f"[错误] {str(e)}"

    def _handle_switch_bot(self, user_id: str, args: str) -> str:
        if not args: 
            return "[错误]未指定角色名称"
        return self.modify_active_session(
            user_id=user_id,
            bot_role=args
        )

    def _handle_switch_user(self, user_id: str, args: str) -> str:
        if not args: 
            return "[错误]未指定角色名称"
        return self.modify_active_session(
            user_id=user_id,
            user_role=args
        )

    def _handle_display(self, user_id: str, args: str) -> str:
        with self._session_lock:
            session = self._sessions.get(user_id)
            if not session:
                return self.DIALOGS_BOT["session_not_found"]
            return f"Bot: {session['bot_role']} | User: {session['user_role']}\nID: {session['session_id']}"

    def _handle_switch_session(self, user_id: str, args: str) -> str:
        if not args:
            return "[错误]未指定会话 ID"
        try:
            return self.switch_session(user_id, args.strip())
        except Exception as e:
            return f"Switch failed: {str(e)}"

    def _handle_delete_session(self, user_id: str, args: str) -> str:
        if not args:
            return "[错误]未指定会话 ID"
        try:
            return self.delete_session(user_id, args.strip())
        except Exception as e:
            return f"[错误]: {str(e)}"

    def _handle_list_sessions(self, user_id: str, args: str) -> str:
        sessions = self.list_sessions(user_id)
        if not sessions:
            return self.DIALOGS_BOT["session_not_found"]
        return "\n".join([
            f"{i+1}. {s['session_id']} | {s['user_role']} ↔ {s['bot_role']}"
            for i, s in enumerate(sessions)
        ])

    def _handle_switch_llm(self, user_id:str, args: str) -> str:
        sessions = self.list_sessions(user_id)
        new_llm = args.strip()
        try:
            llm = get_llm_by_name(new_llm)
            with self._session_lock:
                session = self._sessions.get(user_id)
                if not session: return self.DIALOGS_BOT["session_not_found"]
                session['chatter'].llm = llm
                return f"LLM switched to {new_llm}"
        except ValueError as err:
            return str(err)

    def get_response(self, user_id: str, message: str) -> str:
        with self._session_lock:
            session = self._sessions.get(user_id)
            if not session:
                return self.DIALOGS_BOT["session_not_found"]
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
        if msg.startswith('/'):
            reply = manager.handle_command(user, msg)
        else:
            reply = manager.get_response(user, msg)
        print(f"Bot> {reply}")