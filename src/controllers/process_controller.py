import os
from .base_controller import BaseController
from .project_controller import ProjectController
from langchain_community.document_loaders import TextLoader # type: ignore
from langchain_community.document_loaders import PyMuPDFLoader # type: ignore
from enums import ProcessingEnum
from langchain_text_splitters import RecursiveCharacterTextSplitter # type: ignore

class ProcessController(BaseController):

    def __init__(self, project_id:str, file_id:str):
        super().__init__()
        self.project_id= project_id
        self.file_id= file_id
        self.project_path = ProjectController().get_project_path(project_id=project_id)

    
    def get_file_extension(self):
        return os.path.splitext(self.file_id)[-1]


    # 1. Instantiate the loader with the file path
    def get_file_loader(self):

        file_ext = self.get_file_extension()
        
        file_path = os.path.join(
            self.project_path,
            self.file_id
        )

        if file_ext == ProcessingEnum.TXT.value:
            return TextLoader(file_path, encoding="utf-8")

        if file_ext == ProcessingEnum.PDF.value:
            return PyMuPDFLoader(file_path)
        
        return None
    
    # 2. "Load" the data (Fetch -> Parse -> Standardize)
    def get_file_content(self):

        loader = self.get_file_loader()
        docs = loader.load()
        return docs # Result: docs is a list of Document objects
    
    
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