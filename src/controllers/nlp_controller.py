from stores.llm.templates.template_parser import TemplateParser
from .base_controller import BaseController
from .conversation_controller import ConversationController
from schemas import ProjectSchema, ChunkSchema, ChatMessageSchema
from stores.llm.LLMEnums import DocumentTypeEnum
from helpers.collections import build_collection_name, get_system_collection_names
from typing import List
import json

class NLPController(BaseController):

    def __init__(self, vectordb_client, generation_client, 
                 embedding_client, template_parser:TemplateParser):
        super().__init__()

        self.vectordb_client = vectordb_client
        self.generation_client = generation_client
        self.embedding_client = embedding_client
        self.template_parser = template_parser
        self.conversation_controller = ConversationController(
            generation_client=generation_client,
            template_parser=template_parser
        )

    def create_collection_name(self, project_id: str):
        return build_collection_name(project_id=project_id)

    def get_search_collection_names(self, project_id: str) -> List[str]:
        system_collections = get_system_collection_names()
        user_collection = self.create_collection_name(project_id=project_id)
        return list(dict.fromkeys(system_collections + [user_collection]))
    
    def reset_vector_db_collection(self, project: ProjectSchema):
        collection_name = self.create_collection_name(project_id=project.project_id)
        return self.vectordb_client.delete_collection(collection_name=collection_name)
    
    def get_vector_db_collection_info(self, project: ProjectSchema):
        collection_name = self.create_collection_name(project_id=project.project_id)
        collection_info = self.vectordb_client.get_collection_info(collection_name=collection_name)
                
        return json.loads(
            json.dumps(collection_info, default=lambda x: x.__dict__)
        )
    
    def index_into_vector_db(self, project: ProjectSchema, chunks: List[ChunkSchema],
                                   chunks_ids: List[str], 
                                   do_reset: bool = False):
        
        # step1: get collection name
        collection_name = self.create_collection_name(project_id=project.project_id)

        # step2: manage items
        texts = [ c.chunk_text for c in chunks ]
        metadata = [ c.chunk_metadata for c in  chunks]
        
        vectors = self.embedding_client.embed_texts(
            texts=texts,
            document_type=DocumentTypeEnum.DOCUMENT.value
        )
        
        if not vectors or len(vectors) != len(texts):
            return False

        # step3: create collection if not exists
        _ = self.vectordb_client.create_collection(
            collection_name=collection_name,
            embedding_size=self.embedding_client.embedding_size,
            do_reset=do_reset,
        )

        # step4: insert into vector db
        _ = self.vectordb_client.insert_many(
            collection_name=collection_name,
            texts=texts,
            metadata=metadata,
            vectors=vectors,
            record_ids=chunks_ids,
        )

        return True

    async def search_vector_db_collection(self, project: ProjectSchema, text: str, limit: int = 5):

        # step1: get collection name
        collection_names = self.get_search_collection_names(project_id=project.project_id)

        # step2: get text embedding vector
        vector = self.embedding_client.embed_text(text=text, 
                                                 document_type=DocumentTypeEnum.QUERY.value)

        if not vector or len(vector) == 0:
            return False

        # step3: do semantic search
        results = await self.vectordb_client.search_by_vector_multi_collection_async(
            collection_names=collection_names,
            vector=vector,
            limit=limit
        )

        if not results or len(results) == 0:
            return False

        return results

    async def answer_rag_question(self, project: ProjectSchema, query: str, limit: int = 5,
                                  chat_history: list = None, conversation_model: object = None,
                                  conversation_id: str = None, user_id: str = None,
                                  use_memory: bool = True, enable_query_rewrite: bool = True):

        answer, full_prompt, final_chat_history = None, None, None
        conversation = None

        memory_enabled = bool(conversation_model and use_memory and conversation_id and user_id)

        canonical_history: List[ChatMessageSchema] = []
        seed_history: List[ChatMessageSchema] = []

        if memory_enabled:
            conversation = await conversation_model.get_conversation(
                project_id=project.project_id,
                user_id=user_id,
                conversation_id=conversation_id
            )

            if conversation and conversation.messages:
                canonical_history = conversation.messages
            elif chat_history:
                seed_history = self.conversation_controller.normalize_chat_history(chat_history)
                canonical_history = seed_history

        elif chat_history:
            canonical_history = self.conversation_controller.normalize_chat_history(chat_history)

        max_messages = getattr(self.app_settings, "CHAT_HISTORY_MAX_MESSAGES", 0)
        max_chars = getattr(self.app_settings, "CHAT_HISTORY_MAX_CHARS", 0)

        rewrite_history = self.conversation_controller.pack_messages_by_budget(
            messages=canonical_history,
            max_messages=max_messages,
            max_chars=max_chars
        )

        query_for_retrieval = query
        if enable_query_rewrite and rewrite_history:
            rewritten_query = self.conversation_controller.rewrite_query(query=query, history_messages=rewrite_history)
            if rewritten_query:
                query_for_retrieval = rewritten_query

        # step1: retrieve related documents
        retrieved_documents = await self.search_vector_db_collection(
            project=project,
            text=query_for_retrieval,
            limit=limit
        )

        # validation
        if not retrieved_documents or len(retrieved_documents) == 0:
            return answer, full_prompt, final_chat_history, conversation

        # step2: construct the LLM Prompt
        system_prompt = self.template_parser.get(
            group="rag",
            key="system_prompt",
            vars={
                # empty
            }
        )

        documents_prompt = "\n".join([
            self.template_parser.get(
                group="rag",
                key="document_prompt",
                vars={
                    "doc_num": indx + 1,
                    "chunk_text": doc.text,
                }
            )
            for indx, doc in enumerate(retrieved_documents)
        ])

        footer_prompt = self.template_parser.get("rag", "footer_prompt", vars={"query": query})

        full_prompt = "\n\n".join([documents_prompt, footer_prompt])

        # step3: Construct Generation Client Prompts
        if memory_enabled:
            history_budget = self.conversation_controller.calculate_history_budget(system_prompt, full_prompt)
            packed_history = self.conversation_controller.pack_messages_by_budget(
                messages=canonical_history,
                max_messages=max_messages,
                max_chars=history_budget
            )

            final_chat_history = self.conversation_controller.build_provider_history(
                system_prompt=system_prompt,
                messages=packed_history
            )

        else:
            history_budget = self.conversation_controller.calculate_history_budget(system_prompt, full_prompt)
            packed_history = self.conversation_controller.pack_messages_by_budget(
                messages=canonical_history,
                max_messages=max_messages,
                max_chars=history_budget
            )
            final_chat_history = self.conversation_controller.build_provider_history(
                system_prompt=system_prompt,
                messages=packed_history
            )

        history_for_llm = list(final_chat_history) if final_chat_history else []

        # step4: Retrieve the Answer
        answer = self.generation_client.generate_text(
            prompt=full_prompt,
            chat_history=history_for_llm
        )

        if not answer:
            return answer, full_prompt, history_for_llm, conversation

        if memory_enabled:
            messages_to_append: List[ChatMessageSchema] = []

            if seed_history:
                messages_to_append.extend(seed_history)

            messages_to_append.append(
                ChatMessageSchema(role="user", content=str(query).strip())
            )
            messages_to_append.append(
                ChatMessageSchema(role="assistant", content=str(answer).strip())
            )

            conversation = await conversation_model.append_messages(
                project_id=project.project_id,
                user_id=user_id,
                conversation_id=conversation_id,
                messages=messages_to_append
            )

        return answer, full_prompt, history_for_llm, conversation