# NLP Endpoint: Index Search (Semantic Vector Search)

## Overview
This endpoint performs semantic search on a project's vector collection. It converts the user's query text into a vector embedding and retrieves the most similar document chunks from the Qdrant database. This is the retrieval component of the RAG pipeline, finding relevant context before generating an answer.

## Endpoint Details

### HTTP Method & Path
```
POST /api/v1/nlp/index/search/{project_id}
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
| `project_id` | string | Yes | Unique identifier for the project to search within |

### Query Parameters
None

### Request Headers

| Header | Value | Required |
|--------|-------|----------|
| `Content-Type` | `application/json` | Yes |

### Request Body (JSON)

```json
{
  "text": "What are the payment terms in the contract?",
  "limit": 5
}
```

#### Request Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `text` | string | Yes | - | The search query text. Will be converted to a vector for semantic search. |
| `limit` | integer | No | 5 | Maximum number of results to return. Typical range: 3-10. |

#### Parameter Details

**text**
- Natural language query
- Can be a question, statement, or keywords
- Truncated to max character limit (default: 1024 chars)
- Converted to vector using the same embedding model as indexing
- Examples:
  - "What are the termination clauses?"
  - "liability limitations"
  - "How is payment calculated?"

**limit**
- Controls number of results returned
- Higher values: More context but potential noise
- Lower values: More focused but may miss relevant info
- Recommended: 5-10 for most use cases
- Maximum: No hard limit, but consider token limits for downstream LLM

## Response

### Success Response (200 OK)

#### Response Body
```json
{
  "signal": "vectordb_search_successfully",
  "results": [
    {
      "id": 42,
      "version": 0,
      "score": 0.8756,
      "payload": {
        "text": "Article 5: Payment Terms. The Client shall pay the Service Provider within 30 days of invoice date. Late payments will incur a 2% monthly interest charge.",
        "metadata": {
          "source": "/path/to/contract.pdf",
          "page": 5,
          "file_path": "/path/to/contract.pdf"
        }
      },
      "vector": null
    },
    {
      "id": 43,
      "version": 0,
      "score": 0.8234,
      "payload": {
        "text": "Payment shall be made via wire transfer to the account specified in Appendix A. All payments are non-refundable.",
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

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `signal` | string | Status indicator: `"vectordb_search_successfully"` |
| `results` | array | List of search results, ordered by relevance (highest score first) |

#### Result Object Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Unique identifier of the chunk in the vector database |
| `version` | integer | Version number of the record (internal Qdrant field) |
| `score` | float | Similarity score (0.0 to 1.0 for cosine, higher = more similar) |
| `payload` | object | Contains the chunk text and metadata |
| `payload.text` | string | The actual text content of the chunk |
| `payload.metadata` | object | Original document metadata (source file, page number, etc.) |
| `vector` | null | Vector embedding (not returned by default to reduce response size) |

#### Score Interpretation (Cosine Similarity)
- **0.9 - 1.0**: Extremely similar (near-duplicate or exact match)
- **0.8 - 0.9**: Highly relevant (strong semantic match)
- **0.7 - 0.8**: Relevant (good semantic match)
- **0.6 - 0.7**: Moderately relevant (some semantic overlap)
- **< 0.6**: Weakly relevant (may not be useful)

### Error Responses

#### 400 Bad Request - Search Failed
```json
{
  "signal": "vectordb_search_error"
}
```
**Causes**:
- Collection doesn't exist (not indexed yet)
- Embedding generation failed (API error)
- Vector database error
- Empty query text

## Implementation Details

### Source Code Locations
- **Route**: `src/routes/nlp.py` - `search_index()`
- **Controller**: `src/controllers/nlp_controller.py` - `NLPController.search_vector_db_collection()`
- **LLM Provider**: `src/stores/llm/providers/CoHereProvider.py` or `OpenAIProvider.py`
- **VectorDB Provider**: `src/stores/vectordb/providers/QdrantDBProvider.py`

### Code Flow

#### 1. Project Validation
```python
project = await ProjectModel.get_project_from_db_or_insert_one(project_id)
```

#### 2. Initialize NLP Controller
```python
nlp_controller = NLPController(
    vectordb_client=request.app.vectordb_client,
    generation_client=request.app.generation_client,
    embedding_client=request.app.embedding_client,
)
```

#### 3. Search Execution
```python
results = nlp_controller.search_vector_db_collection(
    project=project,
    text=search_request.text,
    limit=search_request.limit
)
```

#### 4. Search Process (in NLPController)

**Step 4a: Create Collection Name**
```python
collection_name = f"collection_{project.project_id}"
```

**Step 4b: Generate Query Embedding**
```python
vector = embedding_client.embed_text(
    text=text,
    document_type="query"  # Different from "document" used during indexing
)
```

**Key Difference**: 
- **Indexing**: `document_type="document"` (for storing)
- **Searching**: `document_type="query"` (for retrieving)
- Some models (like Cohere) optimize embeddings differently based on this

**Step 4c: Vector Search**
```python
results = vectordb_client.search_by_vector(
    collection_name=collection_name,
    vector=vector,
    limit=limit
)
```

**Qdrant Search Process**:
1. Receives query vector (384 or 1536 dimensions)
2. Uses HNSW (Hierarchical Navigable Small World) algorithm
3. Computes cosine similarity with all indexed vectors
4. Returns top-K most similar results
5. Results sorted by score (descending)

#### 5. Return Results
```python
return {
    "signal": "vectordb_search_successfully",
    "results": [result.dict() for result in results]
}
```

### Search Algorithm Details

#### HNSW (Hierarchical Navigable Small World)
- **Type**: Approximate nearest neighbor search
- **Complexity**: O(log N) average case
- **Accuracy**: ~99% recall with default parameters
- **Speed**: Milliseconds for millions of vectors

#### Cosine Similarity Calculation
```
similarity = (A · B) / (||A|| × ||B||)

Where:
- A = query vector
- B = document vector
- · = dot product
- ||x|| = vector magnitude
```

**Properties**:
- Range: -1 to 1 (normalized vectors: 0 to 1)
- Measures angle between vectors
- Ignores magnitude (only direction matters)
- Perfect for semantic similarity

## Usage Examples

### cURL
```bash
curl -X POST "http://localhost:5000/api/v1/nlp/index/search/101" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "What are the payment terms?",
    "limit": 5
  }'
```

### Python (requests) - Basic Search
```python
import requests

def search_documents(project_id, query, limit=5):
    response = requests.post(
        f"http://localhost:5000/api/v1/nlp/index/search/{project_id}",
        json={
            "text": query,
            "limit": limit
        }
    )
    
    result = response.json()
    
    if result["signal"] == "vectordb_search_successfully":
        for i, item in enumerate(result["results"], 1):
            print(f"\n--- Result {i} (Score: {item['score']:.4f}) ---")
            print(f"Text: {item['payload']['text'][:200]}...")
            print(f"Source: {item['payload']['metadata'].get('source', 'N/A')}")
            print(f"Page: {item['payload']['metadata'].get('page', 'N/A')}")
    
    return result

# Usage
results = search_documents("101", "What are the termination clauses?")
```

### Python - Filter by Score Threshold
```python
def search_with_threshold(project_id, query, min_score=0.7, limit=10):
    """Search and filter results by minimum score"""
    response = requests.post(
        f"http://localhost:5000/api/v1/nlp/index/search/{project_id}",
        json={
            "text": query,
            "limit": limit
        }
    )
    
    result = response.json()
    
    if result["signal"] == "vectordb_search_successfully":
        # Filter by score
        filtered_results = [
            r for r in result["results"]
            if r["score"] >= min_score
        ]
        
        print(f"Found {len(filtered_results)} results above {min_score}")
        return filtered_results
    
    return []

# Usage
high_quality_results = search_with_threshold("101", "liability clauses", min_score=0.75)
```

### Python - Extract Unique Sources
```python
def get_relevant_documents(project_id, query, limit=10):
    """Get list of unique source documents containing relevant info"""
    response = requests.post(
        f"http://localhost:5000/api/v1/nlp/index/search/{project_id}",
        json={
            "text": query,
            "limit": limit
        }
    )
    
    result = response.json()
    
    if result["signal"] == "vectordb_search_successfully":
        # Extract unique sources
        sources = set()
        for item in result["results"]:
            source = item["payload"]["metadata"].get("source")
            if source:
                sources.add(source)
        
        return list(sources)
    
    return []

# Usage
docs = get_relevant_documents("101", "confidentiality agreement")
print(f"Relevant documents: {docs}")
```

### Python - Multi-Query Search
```python
def multi_query_search(project_id, queries, limit=5):
    """Search multiple queries and aggregate results"""
    all_results = {}
    
    for query in queries:
        response = requests.post(
            f"http://localhost:5000/api/v1/nlp/index/search/{project_id}",
            json={
                "text": query,
                "limit": limit
            }
        )
        
        result = response.json()
        if result["signal"] == "vectordb_search_successfully":
            all_results[query] = result["results"]
    
    return all_results

# Usage
queries = [
    "payment terms",
    "termination clauses",
    "liability limitations"
]
results = multi_query_search("101", queries)

for query, items in results.items():
    print(f"\n{query}: {len(items)} results")
```

### JavaScript (fetch)
```javascript
async function searchDocuments(projectId, query, limit = 5) {
  const response = await fetch(
    `http://localhost:5000/api/v1/nlp/index/search/${projectId}`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        text: query,
        limit: limit
      })
    }
  );
  
  const result = await response.json();
  
  if (result.signal === 'vectordb_search_successfully') {
    result.results.forEach((item, index) => {
      console.log(`\nResult ${index + 1} (Score: ${item.score.toFixed(4)})`);
      console.log(`Text: ${item.payload.text.substring(0, 200)}...`);
      console.log(`Page: ${item.payload.metadata.page}`);
    });
  }
  
  return result;
}

// Usage
searchDocuments("101", "What are the payment terms?");
```

### Postman
1. Create a new POST request
2. Enter URL: `http://localhost:5000/api/v1/nlp/index/search/101`
3. Go to "Headers" tab, add: `Content-Type: application/json`
4. Go to "Body" tab, select "raw" and "JSON"
5. Enter JSON payload:
```json
{
  "text": "What are the payment terms?",
  "limit": 5
}
```
6. Click "Send"

## Use Cases

### 1. Document Discovery
```python
def find_relevant_sections(project_id, topic):
    """Find all sections related to a topic"""
    response = requests.post(
        f"http://localhost:5000/api/v1/nlp/index/search/{project_id}",
        json={
            "text": topic,
            "limit": 10
        }
    )
    
    results = response.json()["results"]
    
    # Group by source document
    by_document = {}
    for result in results:
        source = result["payload"]["metadata"]["source"]
        if source not in by_document:
            by_document[source] = []
        by_document[source].append({
            "page": result["payload"]["metadata"]["page"],
            "text": result["payload"]["text"],
            "score": result["score"]
        })
    
    return by_document
```

### 2. Fact Verification
```python
def verify_claim(project_id, claim):
    """Find evidence for or against a claim"""
    response = requests.post(
        f"http://localhost:5000/api/v1/nlp/index/search/{project_id}",
        json={
            "text": claim,
            "limit": 3
        }
    )
    
    results = response.json()["results"]
    
    if results and results[0]["score"] > 0.8:
        print(f"Strong evidence found (score: {results[0]['score']:.4f})")
        print(f"Text: {results[0]['payload']['text']}")
        return True
    else:
        print("No strong evidence found")
        return False
```

### 3. Comparative Analysis
```python
def compare_documents(project_id1, project_id2, query):
    """Compare how two projects address a topic"""
    results1 = requests.post(
        f"http://localhost:5000/api/v1/nlp/index/search/{project_id1}",
        json={"text": query, "limit": 3}
    ).json()["results"]
    
    results2 = requests.post(
        f"http://localhost:5000/api/v1/nlp/index/search/{project_id2}",
        json={"text": query, "limit": 3}
    ).json()["results"]
    
    print(f"Project {project_id1}:")
    for r in results1:
        print(f"  Score: {r['score']:.4f} - {r['payload']['text'][:100]}...")
    
    print(f"\nProject {project_id2}:")
    for r in results2:
        print(f"  Score: {r['score']:.4f} - {r['payload']['text'][:100]}...")
```

### 4. Citation Extraction
```python
def get_citations(project_id, query, min_score=0.75):
    """Get properly formatted citations for relevant passages"""
    response = requests.post(
        f"http://localhost:5000/api/v1/nlp/index/search/{project_id}",
        json={
            "text": query,
            "limit": 5
        }
    )
    
    results = response.json()["results"]
    
    citations = []
    for result in results:
        if result["score"] >= min_score:
            metadata = result["payload"]["metadata"]
            citation = {
                "text": result["payload"]["text"],
                "source": metadata.get("source", "Unknown"),
                "page": metadata.get("page", "N/A"),
                "score": result["score"]
            }
            citations.append(citation)
    
    return citations
```

## Performance Characteristics

### Response Time
- **Embedding Generation**: 50-200ms (API call)
- **Vector Search**: 10-100ms (depends on collection size)
  - < 10k vectors: ~10ms
  - 10k-100k vectors: ~20-50ms
  - > 100k vectors: ~50-100ms
- **Total**: 100-300ms typical

### Accuracy
- **HNSW Recall**: ~99% (finds 99% of true nearest neighbors)
- **Semantic Quality**: Depends on embedding model
  - Cohere multilingual: Excellent for 100+ languages
  - OpenAI: Excellent for English

### Scalability
- **Collection Size**: Tested up to millions of vectors
- **Concurrent Queries**: Hundreds per second
- **Memory**: ~4KB per vector (384-dim) in RAM

## Search Quality Tips

### Query Formulation
**Good Queries**:
- "What are the payment terms and conditions?"
- "liability limitations for damages"
- "How can the contract be terminated?"

**Poor Queries**:
- "payment" (too vague)
- "asdfasdf" (nonsense)
- Very long queries (> 1000 chars, gets truncated)

### Optimal Limit Values
- **Precise fact-finding**: limit=3-5
- **Comprehensive research**: limit=10-15
- **RAG context**: limit=5-10 (balance context vs token limits)

### Improving Results
1. **Rephrase query**: Try different wordings
2. **Increase limit**: Get more results to choose from
3. **Use specific terms**: Include domain-specific keywords
4. **Check scores**: Filter low-scoring results
5. **Reindex**: If results are poor, try different chunk_size

## Related Endpoints
- **Previous Step**: `POST /api/v1/nlp/index/push/{project_id}` - Index documents first
- **Next Step**: `POST /api/v1/nlp/index/answer/{project_id}` - Get AI-generated answers (uses search internally)
- **Info**: `GET /api/v1/nlp/index/info/{project_id}` - Check collection status

## Troubleshooting

### Issue: "vectordb_search_error"
**Causes & Solutions**:
1. **Collection not indexed**
   - Run: `POST /api/v1/nlp/index/push/{project_id}`
   - Verify: `GET /api/v1/nlp/index/info/{project_id}`

2. **Embedding API failure**
   - Check API keys in `.env`
   - Verify network connectivity
   - Check API rate limits

3. **Empty query**
   - Ensure `text` field is not empty
   - Check for whitespace-only queries

### Issue: No results returned
**Causes**:
- Collection is empty (not indexed)
- Query is too specific or uses wrong terminology
- Embedding model mismatch

**Solutions**:
- Verify collection has vectors: `GET /api/v1/nlp/index/info/{project_id}`
- Try broader queries
- Increase limit parameter
- Check if documents contain relevant content

### Issue: Low relevance scores (all < 0.6)
**Causes**:
- Query doesn't match document content
- Wrong embedding model
- Poor quality documents

**Solutions**:
- Rephrase query to match document language
- Verify embedding model is appropriate for content
- Check document quality and relevance

### Issue: Results not in expected order
**Cause**: Semantic similarity doesn't match expected relevance
**Solution**:
- This is normal - semantic search ranks by meaning, not keywords
- Consider hybrid search (semantic + keyword) for production
- Adjust query to be more specific

### Issue: Slow search performance
**Causes**:
- Very large collection (> 1M vectors)
- High limit value
- Network latency to embedding API

**Solutions**:
- Optimize HNSW parameters (requires code changes)
- Reduce limit value
- Use local embedding models
- Add caching for common queries

### Issue: Inconsistent results for same query
**Cause**: Embedding API returns slightly different vectors
**Solution**:
- This is rare with deterministic models (Cohere)
- OpenAI embeddings should be consistent
- Check if model version changed
