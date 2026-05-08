import json
import logging
import os
from typing import List, Tuple
from .base_controller import BaseController
from .project_controller import ProjectController
from langchain_community.document_loaders import TextLoader # type: ignore
from langchain_community.document_loaders import PyMuPDFLoader # type: ignore
from langchain_core.documents import Document # type: ignore
from enums import ProcessingEnum
from langchain_text_splitters import RecursiveCharacterTextSplitter # type: ignore

class ProcessController(BaseController):

    def __init__(self, project_id:str):
        super().__init__()
        self.project_id= project_id
        self.project_path = ProjectController().get_project_path(project_id=project_id)

    
    def get_file_extension(self, file_id:str):
        return os.path.splitext(file_id)[-1]


    # 1. Instantiate the loader with the file path
    def get_file_loader(self, file_id:str):

        file_ext = self.get_file_extension(file_id=file_id)
        
        file_path = os.path.join(
            self.project_path,
            file_id
        )

        if not os.path.exists(file_path):
            return None
        
        if file_ext == ProcessingEnum.TXT.value:
            return TextLoader(file_path, encoding="utf-8")

        if file_ext == ProcessingEnum.PDF.value:
            return PyMuPDFLoader(file_path)
        
        return None
    
    # 2. "Load" the data (Fetch -> Parse -> Standardize)
    def get_file_content(self,file_id:str):

        file_ext = self.get_file_extension(file_id=file_id)
        file_path = os.path.join(self.project_path, file_id)

        if file_ext == ProcessingEnum.JSONL.value:
            return self.load_jsonl_documents(file_path=file_path)

        loader = self.get_file_loader(file_id=file_id)
       
        if loader is None:
            return None
        
        docs = loader.load()
        return docs # Result: docs is a list of Document objects

    def load_jsonl_records(self, file_path: str) -> List[dict]:
        records: List[dict] = []

        if not os.path.exists(file_path):
            return records

        logger = logging.getLogger(__name__)

        with open(file_path, "r", encoding="utf-8") as handle:
            for line_no, raw_line in enumerate(handle, start=1):
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    logger.warning("Skipping JSONL line %s: %s", line_no, exc)
                    continue

                if isinstance(record, dict):
                    records.append(record)
                else:
                    logger.warning("Skipping JSONL line %s: expected object", line_no)

        return records

    def load_jsonl_documents(self, file_path: str) -> List[Document]:
        records = self.load_jsonl_records(file_path=file_path)
        documents: List[Document] = []

        for record in records:
            legal_basis = str(record.get("legal_basis") or "").strip()
            instruction = str(record.get("instruction") or "").strip()
            page_content = legal_basis or instruction

            if not page_content:
                page_content = json.dumps(record, ensure_ascii=False)

            documents.append(
                Document(
                    page_content=page_content,
                    metadata=record,
                )
            )

        return documents

    def build_legal_dataset_documents(self, records: List[dict]) -> Tuple[List[Document], List[Document]]:
        law_documents: List[Document] = []
        qa_documents: List[Document] = []

        for record in records:
            instruction = str(record.get("instruction") or "").strip()
            output = str(record.get("output") or "").strip()
            legal_basis = str(record.get("legal_basis") or "").strip()

            article = record.get("article")
            chapter = record.get("chapter")
            question_type = record.get("question_type")

            if legal_basis:
                law_documents.append(
                    Document(
                        page_content=legal_basis,
                        metadata={
                            "question": instruction,
                            "answer": output,
                            "article": article,
                            "chapter": chapter,
                            "type": "law",
                        },
                    )
                )

            qa_text_parts = [part for part in (instruction, output) if part]
            qa_text = "\n\n".join(qa_text_parts).strip()
            if qa_text:
                qa_documents.append(
                    Document(
                        page_content=qa_text,
                        metadata={
                            "question": instruction,
                            "answer": output,
                            "article": article,
                            "chapter": chapter,
                            "question_type": question_type,
                            "type": "qa",
                        },
                    )
                )

        return law_documents, qa_documents
    
    
    def process_file_content(self, docs: list,
                        chunk_size: int=100, overlap_size: int=20):

        # get the splitter obj 
        # text splitter take text while loader return docs:list
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap_size,
            length_function=len,
        )

        file_content_texts = [ # list compreh.
            doc.page_content
            for doc in docs
        ]

        file_content_metadata = [ # list compreh.
            doc.metadata
            for doc in docs
        ]

        chunks = text_splitter.create_documents(
            file_content_texts,
            metadatas=file_content_metadata
        )

        #                        --- OR --- 
        # The splitter is smart enough to handle the list of Documents directly.
        # chunks = text_splitter.split_documents(docs)
        
        return chunks