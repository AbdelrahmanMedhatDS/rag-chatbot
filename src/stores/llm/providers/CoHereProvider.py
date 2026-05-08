from ..LLMInterface import LLMInterface
from ..LLMEnums import CoHereEnums, DocumentTypeEnum
import cohere # type: ignore
import logging
import time

class CoHereProvider(LLMInterface):

    def __init__(self, api_key: str,
                       default_input_max_characters: int=1000,
                       default_generation_max_output_tokens: int=1000,
                       default_generation_temperature: float=0.1):
        
        self.api_key = api_key

        self.default_input_max_characters = default_input_max_characters
        self.default_generation_max_output_tokens = default_generation_max_output_tokens
        self.default_generation_temperature = default_generation_temperature

        self.generation_model_id = None

        self.embedding_model_id = None
        self.embedding_size = None

        self.client = cohere.Client(api_key=self.api_key)

        self.logger = logging.getLogger(__name__)

        
        self.enums = CoHereEnums

    def set_generation_model(self, model_id: str):
        self.generation_model_id = model_id

    def set_embedding_model(self, model_id: str, embedding_size: int):
        self.embedding_model_id = model_id
        self.embedding_size = embedding_size

    def process_text(self, text: str):
        return text[:self.default_input_max_characters].strip()

    def generate_text(self, prompt: str, chat_history: list=None, max_output_tokens: int=None,
                            temperature: float = None):

        if not self.client:
            self.logger.error("CoHere client was not set")
            return None

        if not self.generation_model_id:
            self.logger.error("Generation model for CoHere was not set")
            return None
        
        max_output_tokens = max_output_tokens if max_output_tokens else self.default_generation_max_output_tokens
        temperature = temperature if temperature else self.default_generation_temperature

        chat_history = list(chat_history) if chat_history else []

        response = self.client.chat(
            model = self.generation_model_id,
            chat_history = chat_history,
            message = self.process_text(prompt),
            temperature = temperature,
            max_tokens = max_output_tokens
        )

        if not response or not response.text:
            self.logger.error("Error while generating text with CoHere")
            return None
        
        return response.text
    
    def embed_text(self, text: str, document_type: str = None):
        if not self.client:
            self.logger.error("CoHere client was not set")
            return None
        
        if not self.embedding_model_id:
            self.logger.error("Embedding model for CoHere was not set")
            return None
        
        input_type = CoHereEnums.DOCUMENT.value
        if document_type == DocumentTypeEnum.QUERY.value:
            input_type = CoHereEnums.QUERY.value

        response = self.client.embed(
            model = self.embedding_model_id,
            texts = [self.process_text(text)],
            input_type = input_type,
            embedding_types=['float'],
        )

        
        try:
            float_embeddings = response.embeddings.float
            
            if not float_embeddings or len(float_embeddings) == 0:
                self.logger.error("Empty embeddings returned from CoHere")
                return None
                
            return float_embeddings[0]

        except (AttributeError, TypeError) as e:
            self.logger.error(f"Failed to parse CoHere response: {e}")
            return None
            
    def embed_texts(self, texts: list, document_type: str = None,
                    batch_size: int = 96, max_retries: int = 3):
        if not self.client:
            self.logger.error("CoHere client was not set")
            return None
            
        if not self.embedding_model_id:
            self.logger.error("Embedding model for CoHere was not set")
            return None
            
        input_type = CoHereEnums.DOCUMENT.value
        if document_type == DocumentTypeEnum.QUERY.value:
            input_type = CoHereEnums.QUERY.value

        all_embeddings = [None] * len(texts)  # Pre-allocate to preserve order

        for i in range(0, len(texts), batch_size):
            batch = [self.process_text(t) for t in texts[i:i + batch_size]]
            batch_start = i

            for attempt in range(1, max_retries + 1):
                try:
                    response = self.client.embed(
                        model=self.embedding_model_id,
                        texts=batch,
                        input_type=input_type,
                        embedding_types=['float'],
                    )

                    float_embeddings = response.embeddings.float
                    if not float_embeddings or len(float_embeddings) == 0:
                        self.logger.error(f"Empty embeddings on batch {i // batch_size + 1}")
                        if attempt < max_retries:
                            time.sleep(2 ** attempt)
                            continue
                        return None

                    for j, emb in enumerate(float_embeddings):
                        all_embeddings[batch_start + j] = emb
                    break  # Success

                except Exception as e:
                    self.logger.error(
                        f"Batch {i // batch_size + 1} attempt {attempt}/{max_retries} failed: {e}"
                    )
                    if attempt < max_retries:
                        time.sleep(2 ** attempt)
                        continue
                    return None

        # Final validation
        if any(v is None for v in all_embeddings):
            self.logger.error("Some embeddings are missing after batch processing")
            return None

        return all_embeddings
            
    def construct_prompt(self, prompt: str, role: str):
        return {
            "role": role,
            "text": self.process_text(prompt)
        }