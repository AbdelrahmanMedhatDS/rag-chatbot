from stores.llm.templates.template_parser import TemplateParser
from .base_controller import BaseController
from schemas import ProjectSchema, ChunkSchema
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
                                   chunks_ids: List[int], 
                                   do_reset: bool = False):
        
        # step1: get collection name
        collection_name = self.create_collection_name(project_id=project.project_id)

        # step2: manage items
        texts = [ c.chunk_text for c in chunks ]
        metadata = [ c.chunk_metadata for c in  chunks]
        vectors = [
            self.embedding_client.embed_text(text=text, 
                                             document_type=DocumentTypeEnum.DOCUMENT.value)
            for text in texts
        ]

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

    async def answer_rag_question(self, project: ProjectSchema, query: str, limit: int = 5, chat_history: list = None):
        
        answer, full_prompt, final_chat_history = None, None, None

        # step1: retrieve related documents 
        retrieved_documents = await self.search_vector_db_collection(
            project=project,
            text=query,
            limit=limit
        )

        # validation
        if not retrieved_documents or len(retrieved_documents) == 0:
            return answer, full_prompt, final_chat_history
        
        # step2: construct the LLM Prompt 
        system_prompt = self.template_parser.get(
            group="rag",
            key="system_prompt",
            vars={
                # empty
            }
        )
        
        documents_prompt = "\n".join([ # to enventually get all chunks in the list "be joined".
            self.template_parser.get(
                group="rag",
                key="document_prompt",
                vars={
                    "doc_num": indx + 1, # to start from 1
                    "chunk_text": doc.text,
                }
            )

            for indx, doc in enumerate(retrieved_documents)
        ])
        
        footer_prompt = self.template_parser.get("rag", "footer_prompt", vars={"query": query})

        
        # step3: Construct Generation Client Prompts
        # Use provided chat_history or create new one with system prompt
        if chat_history is None or len(chat_history) == 0:
            final_chat_history = [
                self.generation_client.construct_prompt(
                    prompt=system_prompt,
                    role=self.generation_client.enums.SYSTEM.value,
                )
            ]
        else:
            # Use the chat history provided by the client
            final_chat_history = chat_history

        full_prompt = "\n\n".join([documents_prompt, footer_prompt])

        # step4: Retrieve the Answer
        answer = self.generation_client.generate_text(
            prompt=full_prompt,
            chat_history=final_chat_history
        )

        return answer, full_prompt, final_chat_history