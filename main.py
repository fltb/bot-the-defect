# main.py

import os
from dotenv import load_dotenv
import json

# LlamaIndex v0.10+ 新版 API
from llama_index.core import VectorStoreIndex, load_index_from_storage
from llama_index.core import Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.deepseek import DeepSeek
from llama_index.core.storage.storage_context import StorageContext  # Add missing import
from llama_index.core.vector_stores import (
    VectorStoreQuery,
    MetadataFilters,
    MetadataFilter,        # Or potentially ExactMatchFilter
    FilterCondition,
    FilterOperator
)

# 自定义加载函数
from loader import load_chunk_documents, load_background_documents

load_dotenv()
deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
if not deepseek_api_key:
    raise EnvironmentError("请在 .env 中设置 DEEPSEEK_API_KEY。")

# ———— 模型配置 ————
embed_model = HuggingFaceEmbedding(model_name="all-MiniLM-L6-v2")
llm = DeepSeek(model="deepseek-chat", api_key=deepseek_api_key)

Settings.llm = llm
Settings.embed_model = embed_model

# ———— 存储上下文 ————
storage_context = StorageContext.from_defaults()

# ———— 构建或加载索引 ————
if not os.path.exists("./storage"):
    print("正在初始化索引…")
    docs = load_chunk_documents() + load_background_documents()
    index = VectorStoreIndex.from_documents(
        docs,
        storage_context=storage_context,
        show_progress=True
    )
    # 修正：首次持久化时指定目录
    index.storage_context.persist(persist_dir="./storage")
else:
    print("加载已有索引…")
    # 修正：加载时明确指定持久化目录
    storage_context = StorageContext.from_defaults(persist_dir="./storage")
    index = load_index_from_storage(
        storage_context=storage_context,
    )


# ———— 6. 聊天循环 ————
def build_prompt(user_role, bot_role, history, question, retrieved_ctx):
    hist = "\n".join(f"{h['role']}: {h['content']}" for h in history)
    return f"""\
# 游戏设定
你是 {bot_role}，与你对话的玩家扮演 {user_role}，请严格遵守角色性格设定。

# 历史对话
{hist}

# 场景检索上下文
{retrieved_ctx}

# 玩家输入
{user_role}: {question}

# {bot_role} 的回复（保持角色风格）:
"""

def main():
    print("🌟 角色扮演 ChatBot 启动")
    user_role = input("请输入玩家角色名：")
    bot_role = input("请输入 Chatbot 扮演的角色名：")
    filters = MetadataFilters(
        filters=[  # 使用 'filters' 列表参数
            MetadataFilter(
                key="roles",
                value=bot_role,
                operator=FilterOperator.CONTAINS 
            )
        ],
        condition=FilterCondition.AND  
    )    
    # ———— 5. 构建查询引擎 ————
    # 直接在 as_query_engine 中传入 llm（通过 Settings） :contentReference[oaicite:2]{index=2}
    query_engine = index.as_query_engine(
        similarity_top_k=6,
        filters=filters,
        response_mode="compact",
    )

    history = []
    while True:
        q = input(f"{user_role}: ")
        if q.lower() in ("exit","quit"):
            break

        # RAG 检索上下文
        retrieved_nodes = query_engine.retrieve(q)
        retrieved = "\n".join(node.get_content() for node in retrieved_nodes)
        
        # 组装 Prompt
        prompt = build_prompt(user_role, bot_role, history, q, retrieved)
        print(f'promt ${prompt}')
        # 直接调用 Settings.llm（DeepSeek）生成
        resp = llm.complete( prompt )

        print(f"{resp}\n")

        # 更新对话历史
        history.append({"role": user_role, "content": q})
        history.append({"role": bot_role, "content": resp})

if __name__ == "__main__":
    main()
