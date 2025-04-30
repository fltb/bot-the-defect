from melobot import Bot, PluginPlanner, on_start_match, send_text
from melobot.protocols.onebot.v11 import ForwardWebSocketIO, OneBotV11Protocol
# 初始化 ChatBot 实例，指定存储适配器 & 逻辑适配器
chatter = ChatBot(
    'QQChatter',
    storage_adapter='chatterbot.storage.SQLStorageAdapter',
    logic_adapters=[
        'chatterbot.logic.BestMatch'
    ]
)                                                     # 创建 ChatBot 对象&#8203;:contentReference[oaicite:6]{index=6}

# 初始化 melobot Bot
bot = Bot(__name__, protocol=OneBotV11Protocol)      # 实例化 Bot 并指定 OneBot v11 协议&#8203;:contentReference[oaicite:7]{index=7}

# 私聊或群聊 @ 时触发
@on_message(lambda ctx: (
    ctx.adapter.event_type == "message" and
    (
        ctx.adapter.event_detail.get("message_type") == "private" or
        (ctx.adapter.event_detail.get("message_type") == "group" and 
         ctx.adapter.event_detail.get("is_at") is True)
    )
))
async def handle_message(adapter: Adapter):           # 使用 on_message 装饰器注册事件处理函数&#8203;:contentReference[oaicite:8]{index=8}
    # 提取纯文本内容
    text = "".join([seg.text for seg in adapter.event_detail["message"] if hasattr(seg, "text")])
    # 调用 ChatterBot 生成回复
    reply = chatter.get_response(text)                # 获取 ChatBot 回复&#8203;:contentReference[oaicite:9]{index=9}
    # 发送回复至同一会话
    await adapter.send(reply.text)                    # 通过适配器发送文本消息&#8203;:contentReference[oaicite:10]{index=10}

if __name__ == "__main__":
    # 运行 melobot，连接到 OneBot 前端的 WebSocket
    bot.run(ForwardWebSocketIO("ws://127.0.0.1:6700"))  # 启动 Bot 并连接到 OneBot 实现&#8203;:contentReference[oaicite:11]{index=11}