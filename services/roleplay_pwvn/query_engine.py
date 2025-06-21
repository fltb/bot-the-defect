from llama_index.core import VectorStoreIndex, load_index_from_storage
from llama_index.core.storage.storage_context import StorageContext
from llama_index.core.vector_stores import (
    MetadataFilters,
    MetadataFilter,
    FilterCondition,
    FilterOperator
)
import os
from typing import List
from llama_index.core.schema import NodeWithScore
from .loader import RoleplayDataLoader
from config.settings import PWVN_QUERY_STORE_PATH

class RoleplayQueryEngine:
    def __init__(self, bot_role: str):
        self.bot_role = bot_role
        self.storage_dir = PWVN_QUERY_STORE_PATH
        self._init_index()

    def _init_index(self):
        if not os.path.exists(self.storage_dir):
            bg_docs = RoleplayDataLoader.load_background_documents()
            chunk_docs = RoleplayDataLoader.load_chunk_documents()
            self.index = VectorStoreIndex.from_documents(
                chunk_docs + bg_docs,
                storage_context=StorageContext.from_defaults(),
                show_progress=True
            )
            self.index.storage_context.persist(persist_dir=self.storage_dir)
        else:
            storage = StorageContext.from_defaults(persist_dir=self.storage_dir)
            self.index = load_index_from_storage(storage)

        self.query_engine = self.index.as_query_engine(
            similarity_top_k=15,
            filters=self._get_filters(),
            response_mode="compact"
        )

    def _get_filters(self):
        return MetadataFilters(
            filters=[
                MetadataFilter(key="roles", value=self.bot_role, operator=FilterOperator.CONTAINS),
                MetadataFilter(key="type", value="background", operator=FilterOperator.CONTAINS)
            ],
            condition=FilterCondition.OR
        )

    def retrieve(self, query: str) -> List[NodeWithScore]:
        return self.query_engine.retrieve(query)