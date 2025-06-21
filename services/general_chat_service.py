import logging
from typing import Any, Optional
from llama_index.core.llms import ChatMessage

from core.interfaces import IChatService
# 注意：这个服务可以不依赖 RAG，或者使用一个通用的 KnowledgeBase

class GeneralChatService(IChatService):
    """
    一个通用的、无角色设定的聊天服务。
    """
    DEFAULT_SYSTEM_PROMPT = "You are a helpful assistant."
    def __init__(self, session_id: str, llm: Any, system_prompt_template: Optional[str] = None):
        self.session_id = session_id
        self.llm = llm
        self.system_prompt = system_prompt_template or self.DEFAULT_SYSTEM_PROMPT
        # 这个服务可以有自己的聊天记录管理，或者我们也可以抽象一个通用的历史记录模块
        # 为简单起见，暂时省略历史记录
        self.history: list[ChatMessage] = [] 
        logging.info(f"GeneralChatService for session {session_id} initialized.")

    def _build_prompt(self, message: str) -> list[ChatMessage]:
        messages = [
            ChatMessage(role="system", content=self.system_prompt),
            *self.history,
            ChatMessage(role="user", content=message)
        ]
        return messages

    def get_response(self, message: str) -> str:
        messages = self._build_prompt(message)
        response = self.llm.chat(messages)
        reply = response.message.content

        # 更新历史
        self.history.append(ChatMessage(role="user", content=message))
        self.history.append(ChatMessage(role="assistant", content=reply))
        
        return reply

    def switch_llm(self, llm: Any) -> None:
        self.llm = llm