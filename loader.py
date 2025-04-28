import json
from llama_index.core import Document
from llama_index.core import SimpleDirectoryReader

def load_chunk_documents(json_path="knowledge/dialogs.json"):
    docs = []
    with open(json_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)
        for chunk in chunks:
            docs.append(Document(
                text=chunk["text"],
                metadata={
                    "type": "chunk",
                    "day": chunk["day"],
                    "path": chunk.get("path", ""),
                    "chunk_id": chunk["chunk_id"],
                    "roles": chunk.get("roles", [])
                }
            ))
    return docs

def load_background_documents(path="knowledge/background.txt"):
    # 使用 SimpleDirectoryReader 简化文档加载
    
    # 自动加载并添加元数据
    loader = SimpleDirectoryReader(
        input_files=[path],
        file_metadata=lambda _: {"type": "background"}
    )
    return loader.load_data()

