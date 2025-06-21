import json
from typing import Any

from config import settings
from core.interfaces import IChatService, IChatServiceFactory
from core.models import SessionInfo
from services.roleplay_pwvn.chatter import PWVNRoleplayChatService
from services.general_chat_service import GeneralChatService

class PWVNRoleplayChatServiceFactory(IChatServiceFactory):
    """
    为 'pwvn' 模式创建服务的工厂。
    它负责加载和注入该模式所需的所有依赖，比如角色配置。
    """
    def __init__(self, roles_config_path: str):
        try:
            with open(settings.PWVN_ROLES_CONFIG_PATH, 'r', encoding='utf-8') as f:
                self.ROLES_CONFIG = json.load(f)
        except FileNotFoundError:
            # 如果配置文件不存在，提供一个空字典以避免崩溃
            self.ROLES_CONFIG = {}
            print(f"Warning: Roles config file not found at {roles_config_path}")

    def create_service(self, session_info: SessionInfo, llm: Any, config_updater: Any) -> IChatService:
        """根据会话信息创建角色扮演聊天服务实例"""
        if session_info.session_mode != 'pwvn':
            raise ValueError("This factory only supports 'pwvn' mode.")
        
        if not session_info.bot_role or not session_info.user_role:
             raise ValueError("user_role and bot_role are required for 'pwvn' mode.")

        bot_role_info = self.ROLES_CONFIG.get(session_info.bot_role)
        if not bot_role_info:
            raise ValueError(f"Role '{session_info.bot_role}' not found in roles config.")

        return PWVNRoleplayChatService(
            llm=llm,
            session_id=session_info.session_id,
            user_role=session_info.user_role,
            bot_role=session_info.bot_role,
            bot_role_info=bot_role_info,
        )

class GeneralChatServiceFactory(IChatServiceFactory):
    """
    为 'general_qa' 等通用模式创建服务的工厂。
    这个工厂的逻辑相对简单，因为它没有复杂的外部依赖。
    """
    def create_service(self, session_info: SessionInfo, llm: Any, config_updater: Any) -> IChatService:
        """根据会话信息创建通用问答聊天服务实例"""
        if session_info.session_mode not in ['general_qa', 'plain']:
            raise ValueError(f"Mode '{session_info.session_mode}' not supported by GeneralChatServiceFactory.")
            
        # 从会话的配置字典中获取可选参数，提供更高的灵活性
        system_prompt = session_info.config.get('system_prompt')
        
        return GeneralChatService(
            session_id=session_info.session_id,
            llm=llm,
            system_prompt_template=system_prompt 
        )