from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict

@dataclass
class SessionInfo:
    session_id: str
    session_mode: str
    user_role: Optional[str] = None
    bot_role: Optional[str] = None
    config: Dict[str, Any] = field(default_factory=dict)

@dataclass
class UserProfile:
    user_id: int
    active_session_id: Optional[str] = None
    sessions: Dict[str, SessionInfo] = field(default_factory=dict)