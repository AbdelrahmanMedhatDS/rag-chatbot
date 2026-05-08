# Conversations API

## Overview

These endpoints manage conversation metadata and stored chat history. Conversations are stored in MongoDB and used by the answer endpoint when memory is enabled.

The create endpoint only creates the conversation record. Messages are appended by the answer endpoint when memory is enabled.

## Base Path

```
/api/v1/nlp/conversations
```

## 1. Create Conversation

### HTTP Method & Path

```
POST /api/v1/nlp/conversations/{project_id}
```

### Request Body (JSON)

```json
{
  "user_id": "user_42",
  "conversation_id": "conv_123"
}
```

#### Request Fields

| Field             | Type   | Required | Default | Description                                        |
| ----------------- | ------ | -------- | ------- | -------------------------------------------------- |
| `user_id`         | string | Yes      | -       | User identifier                                    |
| `conversation_id` | string | No       | null    | Optional conversation identifier (server generates)

### Success Response (200 OK)

```json
{
  "signal": "conversation_created_successfully",
  "conversation": {
    "conversation_id": "conv_123",
    "user_id": "user_42",
    "project_id": "101",
    "title": null,
    "created_at": "2026-05-05T12:00:00.000000",
    "updated_at": "2026-05-05T12:00:00.000000",
    "message_count": 0
  }
}
```

### Error Responses

```json
{
  "signal": "conversation_create_error"
}
```

## 2. List Conversations

### HTTP Method & Path

```
POST /api/v1/nlp/conversations/{project_id}/list
```

### Request Body (JSON)

```json
{
  "user_id": "user_42",
  "page": 1,
  "page_size": 20
}
```

#### Request Fields

| Field       | Type    | Required | Default | Description                           |
| ----------- | ------- | -------- | ------- | ------------------------------------- |
| `user_id`   | string  | Yes      | -       | User identifier                       |
| `page`      | integer | No       | 1       | Page number (minimum: 1)              |
| `page_size` | integer | No       | 20      | Page size (minimum: 1)                |

### Success Response (200 OK)

```json
{
  "signal": "conversation_list_retrieved_successfully",
  "page": 1,
  "page_size": 20,
  "count": 1,
  "conversations": [
    {
      "conversation_id": "conv_123",
      "user_id": "user_42",
      "project_id": "101",
      "title": "Payment terms overview",
      "created_at": "2026-05-05T12:00:00.000000",
      "updated_at": "2026-05-05T12:05:00.000000",
      "message_count": 4
    }
  ]
}
```

### Error Responses

```json
{
  "signal": "conversation_list_error"
}
```

## 3. Get Conversation

### HTTP Method & Path

```
GET /api/v1/nlp/conversations/{project_id}/{conversation_id}?user_id=...
```

### Success Response (200 OK)

```json
{
  "signal": "conversation_retrieved_successfully",
  "conversation": {
    "conversation_id": "conv_123",
    "user_id": "user_42",
    "project_id": "101",
    "title": "Payment terms overview",
    "created_at": "2026-05-05T12:00:00.000000",
    "updated_at": "2026-05-05T12:05:00.000000",
    "message_count": 4,
    "messages": [
      {
        "role": "user",
        "content": "What are the payment terms?",
        "created_at": "2026-05-05T12:00:05.000000"
      },
      {
        "role": "assistant",
        "content": "Based on the contract, payment terms are as follows...",
        "created_at": "2026-05-05T12:00:06.000000"
      }
    ]
  }
}
```

### Error Responses

```json
{
  "signal": "conversation_not_found"
}
```

## 4. Delete Conversation

### HTTP Method & Path

```
DELETE /api/v1/nlp/conversations/{project_id}/{conversation_id}?user_id=...
```

### Success Response (200 OK)

```json
{
  "signal": "conversation_deleted_successfully",
  "deleted": true
}
```

### Error Responses

```json
{
  "signal": "conversation_delete_error"
}
```

## Implementation Details

### Source Code Locations

- **Routes**: `src/routes/conversations.py`
- **Model**: `src/models/conversation_model.py`

### Storage Notes

- Conversations are stored in MongoDB `conversations` collection.
- Messages are appended atomically using `$push` to prevent race conditions.
- Titles are generated asynchronously on first answer and stored when empty.
