# NLP Endpoint: Index Push (Embedding & Vector Storage)

## Overview
This endpoint converts processed text chunks into vector embeddings and stores them in the Qdrant vector database. This is the critical step that enables semantic search in the RAG pipeline. Each chunk's text is transformed into a high-dimensional vector representation that captures its semantic meaning, allowing for similarity-based retrieval.

## Endpoint Details

### HTTP Method & Path
```
POST /api/v1/nlp/index/push/{project_id}
```

### Tags
- `api_v1`
- `nlp`

### Authentication
None (to be implemented in production)

## Request

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_id` | string | Yes | Unique identifier for the project whose chunks should be indexed |

### Query Parameters
None

### Request Headers

| Header | Value | Required |
|--------|-------|----------|
| `Content-Type` | `application/json` | Yes |

### Request Body (JSON)

```json
{
  "do_reset": 0
}
```

#### Request Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `do_reset` | integer | No | 0 | If 1, deletes the existing vector collection before indexing. If 0, appends to existing collection. |

#### Parameter Details

**do_reset**
- `0`: Incremental indexing - adds new vectors to existing collection
- `1`: Full reindexing - deletes collection and recreates from scratch
- Use cases for reset:
  - Changed embedding model
  - Corrupted vector data
  - Want to remove old vectors
  - Testing different configurations

## Response

### Success Response (200 OK)

#### Response Body
```json
{
  "signal": "inserted_into_vectordb_successfully",
  "inserted_items_count": 245
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `signal` | string | Status indicator: `"inserted_into_vectordb_successfully"` |
| `inserted_items_count` | integer | Total number of chunks successfully embedded and indexed |

### Error Responses

#### 400 Bad Request - Project Not Found
```json
{
  "signal": "project_not_found"
}
```
**Cause**: The specified project_id doesn't exist in the database

#### 400 Bad Request - Insert Failed
```json
{
  "signal": "insert_into_vectordb_error"
}
```
**Cause**: Error during embedding generation or vector insertion (API failure, network issue, etc.)

## Implementation Details

### Source Code Locations
- **Route**: `src/routes/nlp.py` - `index_project()`
- **Controller**: `src/controllers/nlp_controller.py` - `NLPController`
- **Model**: `src/models/chunk_model.py` - `ChunkModel`
- **Model**: `src/models/project_model.py` - `ProjectModel`
- **LLM Provider**: `src/stores/llm/providers/CoHereProvider.py` or `OpenAIProvider.py`
- **VectorDB Provider**: `src/stores/vectordb/providers/QdrantDBProvider.py`

### Code Flow

#### 1. Project Validation
```python
project = await ProjectModel.get_project_from_db_or_insert_one(project_id)

if not project:
    return {"signal": "project_not_found"}
```

#### 2. Initialize NLP Controller
```python
nlp_controller = NLPController(
    vectordb_client=request.app.vectordb_client,  # Qdrant client
    generation_client=request.app.generation_client,  # Not used in this endpoint
    embedding_client=request.app.embedding_client,  # Cohere or OpenAI
)
```

#### 3. Paginated Chunk Retrieval and Indexing
The system processes chunks in pages to manage memory efficiently:

```python
has_records = True
page_no = 1
inserted_items_count = 0
idx = 0  # Global chunk ID counter

while has_records:
    # Retrieve page of chunks (50 chunks per page)
    page_chunks = await ChunkModel.get_poject_chunks(
        project_id=project.id,
        page_no=page_no
    )
    
    if not page_chunks or len(page_chunks) == 0:
        has_records = False
        break
    
    # Generate sequential IDs for this page
    chunks_ids = list(range(idx, idx + len(page_chunks)))
    idx += len(page_chunks)
    
    # Index this page of chunks
    is_inserted = nlp_controller.index_into_vector_db(
        project=project,
        chunks=page_chunks,
        do_reset=push_request.do_reset,
        chunks_ids=chunks_ids
    )
    
    if not is_inserted:
        return {"signal": "insert_into_vectordb_error"}
    
    inserted_items_count += len(page_chunks)
    page_no += 1
```

#### 4. Vector Indexing Process (in NLPController)

**Step 4a: Create Collection Name**
```python
collection_name = f"collection_{project.project_id}"
# Example: "collection_101"
```

**Step 4b: Prepare Data for Embedding**
```python
# Extract text from chunks
texts = [chunk.chunk_text for chunk in chunks]

# Extract metadata
metadata = [chunk.chunk_metadata for chunk in chunks]

# Generate embeddings for all texts
vectors = [
    embedding_client.embed_text(
        text=text,
        document_type="document"  # vs "query" for search
    )
    for text in texts
]
```

**Embedding Process Details**:
- **Cohere**: Uses `embed-multilingual-light-v3.0` (384 dimensions)
  - `input_type="search_document"` for indexing
  - Supports 100+ languages
  - Optimized for semantic search
- **OpenAI**: Uses specified model (e.g., `text-embedding-ada-002`)
  - Returns 1536-dimensional vectors
  - English-optimized

**Step 4c: Create or Reset Collection**
```python
vectordb_client.create_collection(
    collection_name=collection_name,
    embedding_size=embedding_client.embedding_size,  # 384 for Cohere
    do_reset=do_reset,
)
```

**Collection Configuration**:
- **Vector Size**: Matches embedding model output (384 or 1536)
- **Distance Metric**: Cosine similarity (default)
  - Measures angle between vectors
  - Range: -1 (opposite) to 1 (identical)
  - Normalized for vector length
- **Storage**: Local file system (`src/assets/database/qdrant_db/`)

**Step 4d: Batch Insert Vectors**
```python
vectordb_client.insert_many(
    collection_name=collection_name,
    texts=texts,
    metadata=metadata,
    vectors=vectors,
    record_ids=chunks_ids,
)
```

**Batch Processing**:
- Inserts in batches of 50 records
- Each record contains:
  - **ID**: Sequential integer
  - **Vector**: Embedding array
  - **Payload**: 
    - `text`: Original chunk text
    - `metadata`: Document metadata (page, source, etc.)

### Database Operations

#### MongoDB Query
```javascript
// Retrieve chunks for project (paginated)
db.chunks.find({
  "chunk_project_id": ObjectId("...")
})
.skip((page_no - 1) * 50)
.limit(50)
```

#### Qdrant Vector Storage

**Collection Structure**:
```
collection_101/
├── vectors: [384-dimensional arrays]
├── payloads: [
│     {
│       "text": "This is the chunk text...",
│       "metadata": {
│         "source": "/path/to/file.pdf",
│         "page": 5
│       }
│     },
│     ...
│   ]
└── ids: [0, 1, 2, 3, ...]
```

**Example Record**:
```python
Record(
    id=42,
    vector=[0.023, -0.145, 0.089, ...],  # 384 values
    payload={
        "text": "Article 5: The parties agree to...",
        "metadata": {
            "source": "/path/to/contract.pdf",
            "page": 5,
            "file_path": "/path/to/contract.pdf"
        }
    }
)
```

### Configuration

Environment variables in `.env`:
```env
# Embedding configuration
EMBEDDING_BACKEND="COHERE"
EMBEDDING_MODEL_ID="embed-multilingual-light-v3.0"
EMBEDDING_MODEL_SIZE=384
COHERE_API_KEY="your_cohere_api_key"

# Vector database configuration
VECTOR_DB_BACKEND="QDRANT"
VECTOR_DB_PATH="qdrant_db"
VECTOR_DB_DISTANCE_METHOD="cosine"
```

## Usage Examples

### cURL - Initial Indexing
```bash
curl -X POST "http://localhost:5000/api/v1/nlp/index/push/101" \
  -H "Content-Type: application/json" \
  -d '{
    "do_reset": 0
  }'
```

### cURL - Full Reindexing
```bash
curl -X POST "http://localhost:5000/api/v1/nlp/index/push/101" \
  -H "Content-Type: application/json" \
  -d '{
    "do_reset": 1
  }'
```

### Python (requests) - Complete Pipeline
```python
import requests

def complete_document_pipeline(project_id, file_path):
    base_url = "http://localhost:5000/api/v1"
    
    # Step 1: Upload
    with open(file_path, 'rb') as f:
        upload_resp = requests.post(
            f"{base_url}/data/upload/{project_id}",
            files={'file': f}
        )
    print(f"Upload: {upload_resp.json()['signal']}")
    
    # Step 2: Process
    process_resp = requests.post(
        f"{base_url}/data/process/{project_id}",
        json={
            "chunk_size": 1000,
            "overlap_size": 200
        }
    )
    print(f"Process: {process_resp.json()['inserted_chunks']} chunks")
    
    # Step 3: Index
    index_resp = requests.post(
        f"{base_url}/nlp/index/push/{project_id}",
        json={"do_reset": 0}
    )
    print(f"Index: {index_resp.json()['inserted_items_count']} vectors")
    
    return index_resp.json()

# Usage
result = complete_document_pipeline("101", "/path/to/contract.pdf")
```

### Python - Incremental Indexing
```python
def add_document_to_existing_index(project_id, file_path):
    """Add a new document without reindexing existing ones"""
    base_url = "http://localhost:5000/api/v1"
    
    # Upload new file
    with open(file_path, 'rb') as f:
        upload_resp = requests.post(
            f"{base_url}/data/upload/{project_id}",
            files={'file': f}
        )
    file_id = upload_resp.json()["file_id"]
    
    # Process only the new file
    process_resp = requests.post(
        f"{base_url}/data/process/{project_id}",
        json={
            "file_id": file_id,
            "chunk_size": 1000,
            "overlap_size": 200,
            "do_reset": 0  # Keep existing chunks
        }
    )
    
    # Index with do_reset=0 to append to existing vectors
    index_resp = requests.post(
        f"{base_url}/nlp/index/push/{project_id}",
        json={"do_reset": 0}  # Append mode
    )
    
    return index_resp.json()
```

### Python - Full Reindexing
```python
def reindex_project(project_id):
    """Completely rebuild the vector index"""
    response = requests.post(
        f"http://localhost:5000/api/v1/nlp/index/push/{project_id}",
        json={"do_reset": 1}  # Full reset
    )
    
    result = response.json()
    if result["signal"] == "inserted_into_vectordb_successfully":
        print(f"Reindexed {result['inserted_items_count']} chunks")
    else:
        print(f"Reindexing failed: {result['signal']}")
    
    return result
```

### JavaScript (fetch)
```javascript
async function indexProject(projectId, doReset = false) {
  const response = await fetch(
    `http://localhost:5000/api/v1/nlp/index/push/${projectId}`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        do_reset: doReset ? 1 : 0
      })
    }
  );
  
  const result = await response.json();
  console.log(`Indexed ${result.inserted_items_count} items`);
  return result;
}

// Usage
indexProject("101", false);  // Incremental
indexProject("101", true);   // Full reindex
```

### Postman
1. Create a new POST request
2. Enter URL: `http://localhost:5000/api/v1/nlp/index/push/101`
3. Go to "Headers" tab, add: `Content-Type: application/json`
4. Go to "Body" tab, select "raw" and "JSON"
5. Enter JSON payload:
```json
{
  "do_reset": 0
}
```
6. Click "Send"

## Use Cases

### 1. Initial Project Setup
```python
def setup_new_project(project_id, document_paths):
    """Complete setup for a new project"""
    for doc_path in document_paths:
        # Upload
        with open(doc_path, 'rb') as f:
            requests.post(
                f"http://localhost:5000/api/v1/data/upload/{project_id}",
                files={'file': f}
            )
    
    # Process all files
    requests.post(
        f"http://localhost:5000/api/v1/data/process/{project_id}",
        json={"chunk_size": 1000, "overlap_size": 200}
    )
    
    # Index everything
    result = requests.post(
        f"http://localhost:5000/api/v1/nlp/index/push/{project_id}",
        json={"do_reset": 0}
    )
    
    return result.json()
```

### 2. Adding Documents to Existing Project
```python
def add_documents(project_id, new_document_paths):
    """Add new documents without affecting existing index"""
    for doc_path in new_document_paths:
        # Upload
        with open(doc_path, 'rb') as f:
            upload_resp = requests.post(
                f"http://localhost:5000/api/v1/data/upload/{project_id}",
                files={'file': f}
            )
        
        file_id = upload_resp.json()["file_id"]
        
        # Process just this file
        requests.post(
            f"http://localhost:5000/api/v1/data/process/{project_id}",
            json={
                "file_id": file_id,
                "chunk_size": 1000,
                "overlap_size": 200,
                "do_reset": 0
            }
        )
    
    # Index new chunks (incremental)
    result = requests.post(
        f"http://localhost:5000/api/v1/nlp/index/push/{project_id}",
        json={"do_reset": 0}
    )
    
    return result.json()
```

### 3. Switching Embedding Models
```python
def switch_embedding_model(project_id):
    """Reindex with a new embedding model"""
    # Update .env with new EMBEDDING_MODEL_ID
    # Restart the server
    
    # Full reindex with new model
    result = requests.post(
        f"http://localhost:5000/api/v1/nlp/index/push/{project_id}",
        json={"do_reset": 1}  # Must reset for new embeddings
    )
    
    return result.json()
```

## Performance Characteristics

### Timing Estimates
- **Embedding Generation**: 
  - Cohere: ~50-100 chunks/second
  - OpenAI: ~30-50 chunks/second
  - Depends on API rate limits and network latency
- **Vector Insertion**: 
  - Qdrant (local): ~1000-2000 vectors/second
  - Batched in groups of 50
- **Total Time**: 
  - 100 chunks: ~5-10 seconds
  - 1000 chunks: ~30-60 seconds
  - 10000 chunks: ~5-10 minutes

### Resource Usage
- **Memory**: Loads 50 chunks at a time (paginated)
- **Disk**: Vector storage ~4KB per chunk (384-dim floats)
- **Network**: API calls for each chunk embedding
- **CPU**: Minimal (embedding done by external API)

### Optimization Tips
1. **Batch Processing**: Already implemented (50 chunks/batch)
2. **Pagination**: Prevents memory overflow on large projects
3. **Async Operations**: MongoDB queries are async
4. **Rate Limiting**: Consider API rate limits for embedding services

## Related Endpoints
- **Previous Step**: `POST /api/v1/data/process/{project_id}` - Process documents into chunks
- **Next Step**: `POST /api/v1/nlp/index/search/{project_id}` - Search the vector index
- **Next Step**: `POST /api/v1/nlp/index/answer/{project_id}` - RAG question answering
- **Info**: `GET /api/v1/nlp/index/info/{project_id}` - Get collection statistics

## Troubleshooting

### Issue: "project_not_found"
**Cause**: Invalid project_id
**Solution**: 
- Verify project_id is correct
- Ensure project was created (upload at least one file)
- Check MongoDB for project record

### Issue: "insert_into_vectordb_error"
**Cause**: Embedding API failure or vector insertion error
**Solution**:
- Check API keys in `.env` (COHERE_API_KEY or OPENAI_API_KEY)
- Verify network connectivity to API endpoints
- Check API rate limits and quotas
- Review server logs for detailed error messages
- Verify Qdrant database path is writable

### Issue: Indexing takes very long
**Cause**: Large number of chunks or slow API responses
**Solution**:
- Check chunk count: `GET /api/v1/nlp/index/info/{project_id}`
- Monitor API response times
- Consider upgrading API plan for higher rate limits
- Process in smaller batches (adjust page_size in code)

### Issue: Out of memory during indexing
**Cause**: Too many chunks loaded at once
**Solution**:
- Reduce page_size in `ChunkModel.get_poject_chunks()` (default: 50)
- Increase server memory
- Process project in multiple sessions

### Issue: Vectors not searchable after indexing
**Cause**: Collection not properly created or wrong embedding size
**Solution**:
- Verify collection exists: `GET /api/v1/nlp/index/info/{project_id}`
- Check embedding_size matches model output
- Try reindexing with do_reset=1
- Verify Qdrant database files are not corrupted

### Issue: Different results after reindexing
**Cause**: Embedding model produces slightly different vectors
**Solution**:
- This is normal for some models (especially with temperature)
- Cohere embeddings should be deterministic
- Verify same model and version is being used

### Issue: API rate limit exceeded
**Cause**: Too many embedding requests too quickly
**Solution**:
- Add rate limiting/throttling in code
- Upgrade API plan
- Process in smaller batches with delays
- Use local embedding models (e.g., sentence-transformers)
