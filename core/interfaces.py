from abc import ABC, abstractmethod
from typing import List, Optional, Any, Dict

from .models import SessionInfo, UserProfile

class IMessagePusher(ABC):
    @abstractmethod
    async def send_private_message(self, user_id: int, message: str) -> None:
        pass

    @abstractmethod
    async def send_group_message(self, group_id: int, message: str) -> None:
        pass

class IChatService(ABC):
    @abstractmethod
    def get_response(self, message: str) -> str:
        pass

    @abstractmethod
    def switch_llm(self, llm: Any) -> None:
        pass

class IChatServiceFactory(ABC):
    @abstractmethod
    def create_service(self, session_info: SessionInfo, llm: Any, config_updater: Any) -> IChatService:
        pass

class IUserService(ABC):
    @abstractmethod
    async def handle_message(self, user_id: int, message: str) -> str:
        pass