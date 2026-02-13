# API Endpoints Summary - Legal RAG Chatbot

**Version:** 0.1  
**Base URL:** `http://localhost:5000/api/v1`  
**Last Updated:** February 2, 2026

---

## Table of Contents

1. [Quick Reference](#quick-reference)
2. [Base Endpoints](#base-endpoints)
3. [Data Management Endpoints](#data-management-endpoints)
4. [NLP & Search Endpoints](#nlp--search-endpoints)
5. [Error Codes](#error-codes)
6. [Common Workflows](#common-workflows)


---

## Quick Reference

[check that illustrated image](./images/API_Endpoints_Summary.png)


| Endpoint | Method | Purpose | Auth Required |
|----------|--------|---------|---------------|
| `/` | GET | Health check | No |
| `/data/upload/{project_id}` | POST | Upload document | No |
| `/data/process/{project_id}` | POST | Process document into chunks | No |
| `/nlp/index/push/{project_id}` | POST | Create vector embeddings | No |
| `/nlp/index/info/{project_id}` | GET | Get collection statistics | No |
| `/nlp/index/search/{project_id}` | POST | Semantic search | No |


---

## Base Endpoints

### Health Check

**Endpoint:** `GET /`

**Description:** Check if API is running and get version info

**Request:**
```bash
curl -X GET "http://localhost:5000/api/v1/"
```

**Response:**
```json
{
  "app name": "legal-rag-chatbot",
  "app version": "0.1"
}
```

**Status Codes:**
- `200 OK` - API is running

---

## Data Management Endpoints

### 1. Upload Document

**Endpoint:** `POST /data/upload/{project_id}`

**Description:** Upload a PDF or TXT file to a project

**Path Parameters:**
- `project_id` (string, required) - Unique project identifier (alphanumeric)

**Request Body:** `multipart/form-data`
- `file` (file, required) - Document file (PDF or TXT, max 10MB)

**Example:**
```bash
curl -X POST "http://localhost:5000/api/v1/data/upload/101" \
  -F "file=@contract.pdf"
```

**Success Response:** `200 OK`
```json
{
  "signal": "file_upload_success",
  "file_id": "abc123xyz456_contract.pdf",
  "asset's refrence": "abc123xyz456_contract.pdf"
}
```

**Error Responses:**

| Status | Signal | Reason |
|--------|--------|--------|
| `400` | `file_type_not_supported` | Invalid file type (not PDF/TXT) |
| `400` | `file_size_exceeded` | File larger than 10MB |
| `400` | `file_upload_failed` | Server error during upload |

**Notes:**
- Project is auto-created if it doesn't exist
- File is saved to `src/assets/files/{project_id}/{file_id}`
- Returns unique `file_id` for reference

---

### 2. Process Document

**Endpoint:** `POST /data/process/{project_id}`

**Description:** Extract text and split into searchable chunks

**Path Parameters:**
- `project_id` (string, required) - Project identifier

**Request Body:** `application/json`
```json
{
  "file_id": "abc123xyz456_contract.pdf",
  "chunk_size": 1000,
  "overlap_size": 200,
  "do_reset": 0
}
```

**Parameters:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `file_id` | string | No | null | Specific file to process (null = all files) |
| `chunk_size` | integer | No | 100 | Max characters per chunk (recommended: 1000-1500) |
| `overlap_size` | integer | No | 20 | Characters overlap between chunks (15-20% of chunk_size) |
| `do_reset` | integer | No | 0 | 1 = delete existing chunks first, 0 = append |

**Example:**
```bash
curl -X POST "http://localhost:5000/api/v1/data/process/101" \
  -H "Content-Type: application/json" \
  -d '{
    "file_id": "abc123xyz456_contract.pdf",
    "chunk_size": 1000,
    "overlap_size": 200,
    "do_reset": 0
  }'
```

**Success Response:** `200 OK`
```json
{
  "signal": "processing_completed",
  "inserted_chunks": 245,
  "processed_files": 1
}
```

**Error Responses:**

| Status | Signal | Reason |
|--------|--------|--------|
| `400` | `no_file_found_with_this_id` | Invalid file_id |
| `400` | `not_found_files` | No files in project |
| `400` | `processing_failed` | Error during text extraction |

**Notes:**
- Supports PDF and TXT files
- Chunks stored in MongoDB with metadata (page numbers, source)
- Use `do_reset=1` to reprocess with different parameters

---

## NLP & Search Endpoints

### 3. Index Vectors (Create Embeddings)

**Endpoint:** `POST /nlp/index/push/{project_id}`

**Description:** Convert chunks to vector embeddings and store in Qdrant

**Path Parameters:**
- `project_id` (string, required) - Project identifier

**Request Body:** `application/json`
```json
{
  "do_reset": 0
}
```

**Parameters:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `do_reset` | integer | No | 0 | 1 = delete collection and reindex, 0 = append |

**Example:**
```bash
curl -X POST "http://localhost:5000/api/v1/nlp/index/push/101" \
  -H "Content-Type: application/json" \
  -d '{"do_reset": 0}'
```

**Success Response:** `200 OK`
```json
{
  "signal": "inserted_into_vectordb_successfully",
  "inserted_items_count": 245
}
```

**Error Responses:**

| Status | Signal | Reason |
|--------|--------|--------|
| `400` | `project_not_found` | Invalid project_id |
| `400` | `insert_into_vectordb_error` | Embedding API failure or Qdrant error |

**Notes:**
- Processes chunks in batches of 50
- Generates embeddings using Cohere (384-dim) or OpenAI (1536-dim)
- Stores vectors + text + metadata in Qdrant
- Use `do_reset=1` when changing embedding models

**Processing Time:**
- ~5-10 seconds for 100 chunks
- ~30-60 seconds for 1000 chunks

---

### 4. Get Collection Info

**Endpoint:** `GET /nlp/index/info/{project_id}`

**Description:** Get vector collection statistics and health status

**Path Parameters:**
- `project_id` (string, required) - Project identifier

**Example:**
```bash
curl -X GET "http://localhost:5000/api/v1/nlp/index/info/101"
```

**Success Response:** `200 OK`
```json
{
  "signal": "vectordb_collection_retrieved_successfully",
  "collection_info": {
    "status": "green",
    "optimizer_status": "ok",
    "points_count": 245,
    "vectors_count": null,
    "indexed_vectors_count": 0,
    "segments_count": 1,
    "config": {
      "params": {
        "vectors": {
          "size": 384,
          "distance": "Cosine"
        }
      },
      "hnsw_config": {
        "m": 16,
        "ef_construct": 100
      }
    }
  }
}
```

**Key Fields:**

| Field | Description |
|-------|-------------|
| `status` | Collection health: "green" (healthy), "yellow" (warning), "red" (error) |
| `points_count` | **Actual number of vectors** (use this, not vectors_count) |
| `config.params.vectors.size` | Vector dimensions (384 for Cohere, 1536 for OpenAI) |
| `config.params.vectors.distance` | Similarity metric (Cosine recommended) |

**Use Cases:**
- Verify indexing completed
- Check collection health before searching
- Debug indexing issues
- Monitor vector count

---

### 5. Semantic Search

**Endpoint:** `POST /nlp/index/search/{project_id}`

**Description:** Find relevant document chunks using semantic similarity

**Path Parameters:**
- `project_id` (string, required) - Project identifier

**Request Body:** `application/json`
```json
{
  "text": "What are the payment terms?",
  "limit": 5
}
```

**Parameters:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `text` | string | Yes | - | Search query (natural language) |
| `limit` | integer | No | 5 | Number of results to return (recommended: 5-10) |

**Example:**
```bash
curl -X POST "http://localhost:5000/api/v1/nlp/index/search/101" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "What are the payment terms?",
    "limit": 5
  }'
```

**Success Response:** `200 OK`
```json
{
  "signal": "vectordb_search_successfully",
  "results": [
    {
      "id": 42,
      "version": 0,
      "score": 0.8756,
      "payload": {
        "text": "Article 5: Payment Terms. The Client shall pay within 30 days...",
        "metadata": {
          "source": "/path/to/contract.pdf",
          "page": 5,
          "file_path": "/path/to/contract.pdf"
        }
      },
      "vector": null
    }
  ]
}
```

**Score Interpretation:**

| Score Range | Relevance |
|-------------|-----------|
| 0.9 - 1.0 | Extremely similar |
| 0.8 - 0.9 | Highly relevant |
| 0.7 - 0.8 | Relevant |
| 0.6 - 0.7 | Moderately relevant |
| < 0.6 | Weakly relevant |

**Error Responses:**

| Status | Signal | Reason |
|--------|--------|--------|
| `400` | `vectordb_search_error` | Collection not indexed, embedding API failure, or empty query |

**Notes:**
- Uses cosine similarity for ranking
- Returns text and metadata in payload (no MongoDB query needed)
- Query is converted to vector using same embedding model as indexing

**Response Time:** 100-300ms typical

---

### 6. RAG Question Answering

**Endpoint:** `POST /nlp/index/answer/{project_id}`

**Description:** Get AI-generated answers based on document content (RAG)

**Path Parameters:**
- `project_id` (string, required) - Project identifier

**Request Body:** `application/json`
```json
{
  "text": "What are the payment terms in the contract?",
  "limit": 5
}
```

**Parameters:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `text` | string | Yes | - | Question to answer |
| `limit` | integer | No | 5 | Number of context chunks to retrieve (5-10 recommended) |

**Example:**
```bash
curl -X POST "http://localhost:5000/api/v1/nlp/index/answer/101" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "What are the payment terms?",
    "limit": 5
  }'
```

**Success Response:** `200 OK`
```json
{
  "signal": "rag_answer_successfully",
  "answer": "Based on the contract, payment terms are as follows: The Client shall pay the Service Provider within 30 days of invoice date. Late payments will incur a 2% monthly interest charge. Payment shall be made via wire transfer to the account specified in Appendix A.",
  "full_prompt": "Document 1:\nArticle 5: Payment Terms...\n\nDocument 2:\nPayment shall be made...\n\nPlease answer: What are the payment terms?",
  "chat_history": [
    {
      "role": "system",
      "text": "You are a helpful legal assistant..."
    }
  ]
}
```

**Error Responses:**

| Status | Signal | Reason |
|--------|--------|--------|
| `400` | `rag_answer_error` | No relevant documents, LLM API failure, or template parser not configured |

**Notes:**
- Combines semantic search + LLM generation
- Uses GPT-3.5-turbo (OpenAI) or Command (Cohere)
- Temperature: 0.1 (low randomness for factual accuracy)
- Max tokens: 200 (configurable)
- **Current Limitation:** Template parser not implemented (may need hardcoded prompts)

**Response Time:** 1.5-6 seconds typical

---

## Error Codes

### HTTP Status Codes

| Code | Meaning | When It Occurs |
|------|---------|----------------|
| `200` | OK | Request successful |
| `400` | Bad Request | Invalid parameters, validation error, or business logic error |
| `500` | Internal Server Error | Unexpected server error |

### Signal Values

All responses include a `signal` field indicating the operation result:

**Success Signals:**
- `file_upload_success`
- `processing_completed`
- `inserted_into_vectordb_successfully`
- `vectordb_collection_retrieved_successfully`
- `vectordb_search_successfully`
- `rag_answer_successfully`

**Error Signals:**
- `file_type_not_supported`
- `file_size_exceeded`
- `file_upload_failed`
- `no_file_found_with_this_id`
- `not_found_files`
- `processing_failed`
- `project_not_found`
- `insert_into_vectordb_error`
- `vectordb_search_error`
- `rag_answer_error`

---

## Common Workflows

### Workflow 1: Complete Setup (New Project)

```bash
# Step 1: Upload document
curl -X POST "http://localhost:5000/api/v1/data/upload/101" \
  -F "file=@contract.pdf"
# Response: {"file_id": "abc123_contract.pdf"}

# Step 2: Process into chunks
curl -X POST "http://localhost:5000/api/v1/data/process/101" \
  -H "Content-Type: application/json" \
  -d '{"chunk_size": 1000, "overlap_size": 200}'
# Response: {"inserted_chunks": 245}

# Step 3: Index vectors
curl -X POST "http://localhost:5000/api/v1/nlp/index/push/101" \
  -H "Content-Type: application/json" \
  -d '{"do_reset": 0}'
# Response: {"inserted_items_count": 245}

# Step 4: Verify indexing
curl -X GET "http://localhost:5000/api/v1/nlp/index/info/101"
# Check: points_count should equal inserted_items_count

# Step 5: Ask questions
curl -X POST "http://localhost:5000/api/v1/nlp/index/answer/101" \
  -H "Content-Type: application/json" \
  -d '{"text": "What are the payment terms?", "limit": 5}'
```

**Total Time:** ~30-60 seconds for a typical document

---

### Workflow 2: Add Document to Existing Project

```bash
# Step 1: Upload new document
curl -X POST "http://localhost:5000/api/v1/data/upload/101" \
  -F "file=@new_contract.pdf"
# Response: {"file_id": "xyz789_new_contract.pdf"}

# Step 2: Process only new file (do_reset=0 to keep existing chunks)
curl -X POST "http://localhost:5000/api/v1/data/process/101" \
  -H "Content-Type: application/json" \
  -d '{
    "file_id": "xyz789_new_contract.pdf",
    "chunk_size": 1000,
    "overlap_size": 200,
    "do_reset": 0
  }'

# Step 3: Index new chunks (do_reset=0 to append)
curl -X POST "http://localhost:5000/api/v1/nlp/index/push/101" \
  -H "Content-Type: application/json" \
  -d '{"do_reset": 0}'
```

---

### Workflow 3: Reprocess with Different Parameters

```bash
# Step 1: Reprocess all files with new chunk size
curl -X POST "http://localhost:5000/api/v1/data/process/101" \
  -H "Content-Type: application/json" \
  -d '{
    "chunk_size": 1500,
    "overlap_size": 300,
    "do_reset": 1
  }'

# Step 2: Reindex everything
curl -X POST "http://localhost:5000/api/v1/nlp/index/push/101" \
  -H "Content-Type: application/json" \
  -d '{"do_reset": 1}'
```

---

### Workflow 4: Search vs Answer

```bash
# Option A: Get raw search results (for custom processing)
curl -X POST "http://localhost:5000/api/v1/nlp/index/search/101" \
  -H "Content-Type: application/json" \
  -d '{"text": "payment terms", "limit": 5}'
# Returns: Relevant chunks with scores

# Option B: Get AI-generated answer (for end users)
curl -X POST "http://localhost:5000/api/v1/nlp/index/answer/101" \
  -H "Content-Type: application/json" \
  -d '{"text": "What are the payment terms?", "limit": 5}'
# Returns: Natural language answer
```

---

## Troubleshooting

### Issue: "file_upload_failed"
**Check:**
- Disk space available
- File permissions on `src/assets/files/`
- File size < 10MB

---

### Issue: "processing_failed"
**Check:**
- File is valid PDF/TXT (not corrupted)
- File contains extractable text (not scanned images)
- MongoDB connection is active

---

### Issue: "insert_into_vectordb_error"
**Check:**
- API keys are valid (COHERE_API_KEY or OPENAI_API_KEY)
- Network connectivity to embedding API
- Qdrant database path is writable
- API rate limits not exceeded

---

### Issue: "vectordb_search_error"
**Check:**
- Collection is indexed (check `/nlp/index/info/{project_id}`)
- `points_count > 0` in collection info
- Embedding API is accessible

---

### Issue: inserted_items_count ≠ points_count
**Cause:** Bug in pagination (fixed in latest version)
**Solution:** Re-index with `do_reset=1`

---

### Issue: "rag_answer_error"
**Check:**
- Collection has vectors (`points_count > 0`)
- LLM API key is valid
- Template parser is configured (known limitation)
- Query is not empty

