import os

from melobot import Bot, PluginPlanner, on_start_match, send_text

from melobot.protocols.onebot.v11.handle import on_at_qq
from melobot.protocols.onebot.v11 import MessageEvent, on_message
from melobot.protocols.onebot.v11 import ForwardWebSocketIO, OneBotV11Protocol
from dotenv import load_dotenv
from chatter_interface import SessionManager

_sessions = {}  # {user_id: SessionManager}

def _get_manager(user_id: str) -> SessionManager:
    if user_id not in _sessions:
        _sessions[user_id] = SessionManager()
        _sessions[user_id].load_session(user_id)
    return _sessions[user_id]

load_dotenv()

qqid = int(os.getenv("BOTQQ_ID"))

@on_at_qq(qid=qqid)  # 匹配命令或@消息
async def echo_at(event: MessageEvent) -> None:
    user_id = event.user_id
    manager = _get_manager(str(user_id))

    msg = event.message
    text = "".join([m.to_dict()['data']['text'] if m.to_dict()['type'] == "text" else "" for m in msg])
    text = text.lstrip()
    if text.startswith("/"):
        reply = manager.handle_command(str(user_id), text)
    else:
        reply = manager.get_response(str(user_id), text)
    
    await send_text(reply)



@on_message()
async def echo_is_private(event: MessageEvent) -> None:
    if not event.is_private():
        return
    user_id = event.user_id
    manager = _get_manager(str(user_id))

    msg = event.message
    text = "".join([m.to_dict()['data']['text'] if m.to_dict()['type'] == "text" else "" for m in msg])
    text = text.lstrip()
    if text.startswith("/"):
        reply = manager.handle_command(str(user_id), text)
    else:
        reply = manager.get_response(str(user_id), text)
    await send_text(reply)


test_plugin = PluginPlanner(version="1.0.0", flows=[echo_at, echo_is_private])

if __name__ == "__main__":

    bot = Bot(__name__)

    bot.add_protocol(OneBotV11Protocol(ForwardWebSocketIO("ws://127.0.0.1:8080")))

    bot.load_plugin(test_plugin)

    bot.run()