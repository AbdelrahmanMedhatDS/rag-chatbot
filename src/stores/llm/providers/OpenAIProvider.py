from ..LLMInterface import LLMInterface
from ..LLMEnums import OpenAIEnums
from openai import OpenAI # type: ignore
import logging
import time

class OpenAIProvider(LLMInterface):

    def __init__(self, api_key: str, api_url: str=None,
                       default_input_max_characters: int=1000,
                       default_generation_max_output_tokens: int=1000,
                       default_generation_temperature: float=0.1):
        
        self.api_key = api_key
        self.api_url = api_url

        self.default_input_max_characters = default_input_max_characters
        self.default_generation_max_output_tokens = default_generation_max_output_tokens
        self.default_generation_temperature = default_generation_temperature

        self.generation_model_id = None

        self.embedding_model_id = None
        self.embedding_size = None

        self.client = OpenAI(
            api_key = self.api_key,
            base_url = self.api_url if self.api_url and self.api_url.strip() != "" else None,
        )

        self.logger = logging.getLogger(__name__)

        self.enums = OpenAIEnums

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
            self.logger.error("OpenAI client was not set")
            return None

        if not self.generation_model_id:
            self.logger.error("Generation model for OpenAI was not set")
            return None
        
        max_output_tokens = max_output_tokens if max_output_tokens else self.default_generation_max_output_tokens
        temperature = temperature if temperature else self.default_generation_temperature

        chat_history = list(chat_history) if chat_history else []
        chat_history.append(
            self.construct_prompt(prompt=prompt, role=OpenAIEnums.USER.value)
        )

        response = self.client.chat.completions.create(
            model = self.generation_model_id,
            messages = chat_history,
            max_tokens = max_output_tokens,
            temperature = temperature
        )

        if not response or not response.choices or len(response.choices) == 0 or not response.choices[0].message:
            self.logger.error("Error while generating text with OpenAI")
            return None

        return response.choices[0].message.content


    def embed_text(self, text: str, document_type: str = None):
        
        if not self.client:
            self.logger.error("OpenAI client was not set")
            return None

        if not self.embedding_model_id:
            self.logger.error("Embedding model for OpenAI was not set")
            return None
        
        response = self.client.embeddings.create(
            model = self.embedding_model_id,
            input = text,
        )

        if not response or not response.data or len(response.data) == 0 or not response.data[0].embedding:
            self.logger.error("Error while embedding text with OpenAI")
            return None

        return response.data[0].embedding

    def embed_texts(self, texts: list, document_type: str = None,
                    batch_size: int = 40, max_retries: int = 3):
        
        if not self.client:
            self.logger.error("OpenAI client was not set")
            return None

        if not self.embedding_model_id:
            self.logger.error("Embedding model for OpenAI was not set")
            return None

        all_embeddings = [None] * len(texts)  # Pre-allocate to preserve order

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_start = i

            for attempt in range(1, max_retries + 1):
                try:
                    response = self.client.embeddings.create(
                        model=self.embedding_model_id,
                        input=batch,
                    )

                    if not response or not response.data:
                        self.logger.error(f"Empty response on batch {i // batch_size + 1}")
                        if attempt < max_retries:
                            time.sleep(2 ** attempt)  # Exponential backoff
                            continue
                        return None

                    # Sort by index to guarantee order matches input order
                    sorted_data = sorted(response.data, key=lambda x: x.index)
                    for j, item in enumerate(sorted_data):
                        all_embeddings[batch_start + j] = item.embedding
                    break  # Success — exit retry loop

                except Exception as e:
                    self.logger.error(
                        f"Batch {i // batch_size + 1} attempt {attempt}/{max_retries} failed: {e}"
                    )
                    if attempt < max_retries:
                        time.sleep(2 ** attempt)  # Exponential backoff: 2s, 4s, 8s
                        continue
                    return None  # All retries exhausted

        # Final validation: ensure no gaps
        if any(v is None for v in all_embeddings):
            self.logger.error("Some embeddings are missing after batch processing")
            return None

        return all_embeddings

    def construct_prompt(self, prompt: str, role: str):
        return {
            "role": role,
            "content": self.process_text(prompt)
        }
    


    
