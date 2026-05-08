# NLP Endpoint: Index Answer (RAG + Memory)

## Overview

This endpoint answers a user question using the RAG pipeline. It retrieves relevant chunks from the vector database, builds a prompt, and generates a response with the LLM. When memory is enabled, it loads and stores conversation history in MongoDB and uses that history for query rewriting and response generation.

Query rewriting is used only for vector search. The final answer uses the original user query and the selected history.

## Endpoint Details

### HTTP Method & Path

```
POST /api/v1/nlp/index/answer/{project_id}
```

### Tags

- `api_v1`
- `nlp`

### Authentication

None (to be implemented in production)

## Request

### Path Parameters

| Parameter    | Type   | Required | Description                            |
| ------------ | ------ | -------- | -------------------------------------- |
| `project_id` | string | Yes      | Unique identifier for the project      |

### Request Headers

| Header         | Value              | Required |
| -------------- | ------------------ | -------- |
| `Content-Type` | `application/json` | Yes      |

### Request Body (JSON)

```json
{
  "text": "What are the payment terms in the contract?",
  "limit": 5,
  "conversation_id": "conv_123",
  "user_id": "user_42",
  "use_memory": true,
  "enable_query_rewrite": true
}
```

#### Request Fields

| Field                  | Type    | Required | Default | Description                                                                 |
| ---------------------- | ------- | -------- | ------- | --------------------------------------------------------------------------- |
| `text`                 | string  | Yes      | -       | The user question                                                          |
| `limit`                | integer | No       | 5       | Number of chunks to retrieve from vector search                             |
| `conversation_id`      | string  | No       | null    | Conversation identifier for memory                                          |
| `user_id`              | string  | No       | null    | User identifier for memory                                                  |
| `use_memory`           | boolean | No       | true    | Enable server-side conversation memory                                      |
| `enable_query_rewrite` | boolean | No       | true    | Rewrite query for retrieval using history                                   |
| `chat_history`         | array   | No       | null    | Client-provided history (used when memory is disabled or to seed memory)    |

#### Notes

- Memory is enabled only when `conversation_id`, `user_id`, and `use_memory=true` are provided.
- If a conversation is missing and `chat_history` is provided, the server will seed history and then append new messages.
- `chat_history` accepts objects with `role` and `content` (or `text`) fields.

## Response

### Success Response (200 OK)

```json
{
  "signal": "rag_answer_successfully",
  "answer": "Based on the contract, payment terms are as follows...",
  "full_prompt": "Document 1:\nArticle 5: Payment Terms...\n\nDocument 2:\nPayment shall be made...\n\nPlease answer: What are the payment terms?",
  "chat_history": [
    {
      "role": "system",
      "content": "You are an assistant to generate a response for the user."
    },
    {
      "role": "user",
      "content": "What are the payment terms?"
    }
  ],
  "conversation_id": "conv_123",
  "conversation_title": "Payment terms overview"
}
```

### Error Responses

#### 400 Bad Request - RAG Failed

```json
{
  "signal": "rag_answer_error"
}
```

**Causes**:

- No relevant documents found
- LLM API failure
- Template parser not configured

## Implementation Details

### Source Code Locations

- **Route**: `src/routes/nlp.py` - `search_index()`
- **Controller**: `src/controllers/nlp_controller.py` - `NLPController.answer_rag_question()`
- **Conversation Controller**: `src/controllers/conversation_controller.py`
- **Conversation Model**: `src/models/conversation_model.py`
- **VectorDB Provider**: `src/stores/vectordb/providers/QdrantDBProvider.py`

### Key Behaviors

1. Optional query rewrite is executed using history and templates.
2. Vector search runs against the project collection and system collections.
3. The LLM answer is generated using the original query and a packed history window.
4. When memory is enabled, the new user and assistant messages are appended atomically in MongoDB.

## Usage Examples

### cURL

```bash
curl -X POST "http://localhost:5000/api/v1/nlp/index/answer/101" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "What are the payment terms?",
    "limit": 5,
    "conversation_id": "conv_123",
    "user_id": "user_42",
    "use_memory": true,
    "enable_query_rewrite": true
  }'
```

### Python (requests)

```python
import requests

payload = {
    "text": "What are the payment terms?",
    "limit": 5,
    "conversation_id": "conv_123",
    "user_id": "user_42",
    "use_memory": True,
    "enable_query_rewrite": True,
}

response = requests.post(
    "http://localhost:5000/api/v1/nlp/index/answer/101",
    json=payload
)

print(response.json())
```
