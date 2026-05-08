# API Harmony and Data Flow (MongoDB and Vector DB)

## Overview

This document explains how the API endpoints work together and how data flows between MongoDB and the vector database (Qdrant). It is intended to clarify the full RAG pipeline and how persistent memory integrates with retrieval.

## System Roles

### MongoDB (Source of Truth for Structured Data)

- **Projects**: `projects` collection
- **Assets**: `assets` collection (uploaded files metadata)
- **Chunks**: `chunks` collection (processed text chunks with metadata)
- **Conversations**: `conversations` collection (chat history and titles)

MongoDB stores durable, structured records used by both the processing and memory features.

### Vector DB (Qdrant)

- Stores high-dimensional embeddings for each chunk
- Used only for semantic similarity search
- Payloads include chunk text and metadata

Qdrant does not store conversation history. It is dedicated to retrieval.

## End-to-End Pipeline Harmony

### 1. Upload

**Endpoint:** `POST /data/upload/{project_id}`

- Saves file to disk under `src/assets/files/{project_id}`
- Inserts an asset record in MongoDB

### 2. Process

**Endpoint:** `POST /data/process/{project_id}`

- Reads files from disk
- Splits text into chunks
- Stores chunks in MongoDB

### 3. Index

**Endpoint:** `POST /nlp/index/push/{project_id}`

- Reads chunks from MongoDB
- Generates embeddings
- Stores vectors and payloads in Qdrant

### 4. Search

**Endpoint:** `POST /nlp/index/search/{project_id}`

- Embeds the query
- Searches Qdrant collections
- Returns top-k chunks

### 5. Answer (RAG)

**Endpoint:** `POST /nlp/index/answer/{project_id}`

- Optionally loads conversation history from MongoDB
- Optionally rewrites the query for better retrieval
- Retrieves relevant chunks from Qdrant
- Generates an answer with the LLM
- Optionally appends new messages to MongoDB

### 6. Conversations

**Endpoints:**

- `POST /nlp/conversations/{project_id}`
- `GET /nlp/conversations/{project_id}`
- `GET /nlp/conversations/{project_id}/{conversation_id}`
- `DELETE /nlp/conversations/{project_id}/{conversation_id}`

These endpoints manage conversation metadata and message history stored in MongoDB.

## MongoDB and Vector DB Consistency

### Key Principles

- MongoDB stores the canonical text chunks and conversation history.
- Qdrant stores only embeddings and payloads for fast retrieval.
- If chunking parameters change, reprocess and reindex to keep Qdrant aligned.
- Conversation memory does not affect Qdrant directly; it only shapes the query and prompt.

### When to Reset

- Use `do_reset=1` in `/data/process` when you want to rebuild chunks.
- Use `do_reset=1` in `/nlp/index/push` after chunk changes or embedding model changes.

## Memory and Retrieval Harmony

- **Query Rewrite** uses recent history to turn pronoun-based questions into standalone queries.
- **Dynamic History Budget** reserves space for system prompt and RAG chunks first, then packs history into the remaining budget.
- **Atomic Append** uses MongoDB `$push` to prevent race conditions when multiple messages arrive quickly.

## Operational Notes

- The health check (`GET /`) verifies MongoDB and Qdrant connectivity.
- Qdrant collection size should align with MongoDB chunk counts after indexing.
- Conversation titles are generated asynchronously and stored when empty.

## Recommended Workflow

1. Upload files
2. Process into chunks
3. Index into Qdrant
4. Ask questions with memory enabled
5. Use conversation APIs for listing and retrieval

This ordering keeps MongoDB and Qdrant in sync and ensures memory is available for follow-up questions.
