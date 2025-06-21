from llama_index.core import Document
from llama_index.core import SimpleDirectoryReader
import json
from config.settings import PWVN_BG_CONFIG_PATH, PWVN_DIALOGS_CONFIG_PATH

class RoleplayDataLoader:
    @staticmethod
    def load_chunk_documents(json_path=PWVN_DIALOGS_CONFIG_PATH):
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

    @staticmethod
    def load_background_documents(path=PWVN_BG_CONFIG_PATH):
        loader = SimpleDirectoryReader(
            input_files=[path],
            file_metadata=lambda _: {"type": "background"}
        )
        return loader.load_data()