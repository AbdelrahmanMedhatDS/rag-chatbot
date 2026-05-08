from typing import List
from stores.llm.templates.template_parser import TemplateParser
from .base_controller import BaseController
from schemas import ChatMessageSchema


class ConversationController(BaseController):

    def __init__(self, generation_client, template_parser: TemplateParser):
        super().__init__()
        self.generation_client = generation_client
        self.template_parser = template_parser

    def _normalize_role(self, role: str):
        if not role:
            return None

        role_value = str(role).strip().lower()
        if role_value in ["system", "sys"]:
            return "system"
        if role_value in ["assistant", "bot", "chatbot"]:
            return "assistant"
        if role_value in ["user", "human"]:
            return "user"

        return None

    def normalize_chat_history(self, chat_history: list) -> List[ChatMessageSchema]:
        normalized: List[ChatMessageSchema] = []
        if not chat_history:
            return normalized

        for item in chat_history:
            if not isinstance(item, dict):
                continue

            role = self._normalize_role(item.get("role"))
            if not role or role == "system":
                continue

            content = item.get("content")
            if content is None:
                content = item.get("text")
            if content is None:
                content = item.get("message")

            if content is None:
                continue

            content_text = str(content).strip()
            if not content_text:
                continue

            normalized.append(ChatMessageSchema(role=role, content=content_text))

        return normalized

    def pack_messages_by_budget(self, messages: List[ChatMessageSchema], max_messages: int, max_chars: int):
        if not messages:
            return []

        if max_messages is None or max_messages <= 0:
            max_messages = len(messages)

        if max_chars is not None and max_chars <= 0:
            return []

        if max_chars is None:
            max_chars = None

        packed = []
        total_chars = 0

        for message in reversed(messages):
            if len(packed) >= max_messages:
                break

            message_len = len(message.content) if message.content else 0
            if max_chars is not None and total_chars + message_len > max_chars:
                if not packed:
                    packed.append(message)
                break

            packed.append(message)
            total_chars += message_len

        packed.reverse()
        return packed

    def build_provider_history(self, system_prompt: str, messages: List[ChatMessageSchema]):
        history = [
            self.generation_client.construct_prompt(
                prompt=system_prompt,
                role=self.generation_client.enums.SYSTEM.value,
            )
        ]

        for message in messages:
            role_value = self.generation_client.enums.USER.value
            if message.role == "assistant":
                role_value = self.generation_client.enums.ASSISTANT.value

            history.append(
                self.generation_client.construct_prompt(
                    prompt=message.content,
                    role=role_value,
                )
            )

        return history

    def calculate_history_budget(self, system_prompt: str, full_prompt: str):
        total_budget = getattr(self.app_settings, "CHAT_CONTEXT_MAX_CHARS", 0)
        max_history_chars = getattr(self.app_settings, "CHAT_HISTORY_MAX_CHARS", 0)

        if not total_budget or total_budget <= 0:
            return max_history_chars

        reserved = len(system_prompt or "") + len(full_prompt or "")
        available = total_budget - reserved
        if available < 0:
            available = 0

        if max_history_chars and max_history_chars > 0:
            return min(available, max_history_chars)

        return available

    def rewrite_query(self, query: str, history_messages: List[ChatMessageSchema]):
        if not history_messages:
            return query

        rewrite_system_prompt = self.template_parser.get(
            group="rag",
            key="query_rewrite_system_prompt",
            vars={}
        )

        rewrite_prompt = self.template_parser.get(
            group="rag",
            key="query_rewrite_prompt",
            vars={
                "query": query,
            }
        )

        if not rewrite_system_prompt or not rewrite_prompt:
            return query

        rewrite_history = self.build_provider_history(
            system_prompt=rewrite_system_prompt,
            messages=history_messages,
        )

        response = self.generation_client.generate_text(
            prompt=rewrite_prompt,
            chat_history=list(rewrite_history),
            max_output_tokens=128,
            temperature=0.0
        )

        if not response:
            return query

        return str(response).strip()

    def generate_conversation_title(self, query: str):
        title_system_prompt = self.template_parser.get(
            group="rag",
            key="conversation_title_system_prompt",
            vars={}
        )

        title_prompt = self.template_parser.get(
            group="rag",
            key="conversation_title_prompt",
            vars={
                "query": query,
            }
        )

        if not title_system_prompt or not title_prompt:
            return None

        history = [
            self.generation_client.construct_prompt(
                prompt=title_system_prompt,
                role=self.generation_client.enums.SYSTEM.value,
            )
        ]

        response = self.generation_client.generate_text(
            prompt=title_prompt,
            chat_history=list(history),
            max_output_tokens=32,
            temperature=0.2
        )

        if not response:
            return None

        title = str(response).strip().replace("\n", " ")
        if len(title) > 120:
            title = title[:120].strip()

        return title
