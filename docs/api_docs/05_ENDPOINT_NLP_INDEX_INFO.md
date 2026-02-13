# NLP Endpoint: Index Info (Collection Statistics)

## Overview
This endpoint retrieves detailed information about a project's vector collection in Qdrant. It provides statistics about the indexed vectors, including collection size, configuration, and status. This is useful for monitoring, debugging, and verifying that indexing completed successfully.

## Endpoint Details

### HTTP Method & Path
```
GET /api/v1/nlp/index/info/{project_id}
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
| `project_id` | string | Yes | Unique identifier for the project whose collection info to retrieve |

### Query Parameters
None

### Request Headers
None required

### Request Body
None (GET request)

## Response

### Success Response (200 OK)

#### Response Body
```json
{
  "signal": "vectordb_collection_retrieved_successfully",
  "collection_info": {
    "status": "green",
    "optimizer_status": "ok",
    "vectors_count": 245,
    "indexed_vectors_count": 245,
    "points_count": 245,
    "segments_count": 1,
    "config": {
      "params": {
        "vectors": {
          "size": 384,
          "distance": "Cosine"
        },
        "shard_number": 1,
        "replication_factor": 1,
        "write_consistency_factor": 1,
        "on_disk_payload": false
      },
      "hnsw_config": {
        "m": 16,
        "ef_construct": 100,
        "full_scan_threshold": 10000,
        "max_indexing_threads": 0,
        "on_disk": false
      },
      "optimizer_config": {
        "deleted_threshold": 0.2,
        "vacuum_min_vector_number": 1000,
        "default_segment_number": 0,
        "max_segment_size": null,
        "memmap_threshold": null,
        "indexing_threshold": 20000,
        "flush_interval_sec": 5,
        "max_optimization_threads": 1
      },
      "wal_config": {
        "wal_capacity_mb": 32,
        "wal_segments_ahead": 0
      }
    },
    "payload_schema": {}
  }
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `signal` | string | Status indicator: `"vectordb_collection_retrieved_successfully"` |
| `collection_info` | object | Detailed collection information from Qdrant |

#### Collection Info Object

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Collection health status: `"green"` (healthy), `"yellow"` (degraded), `"red"` (error) |
| `optimizer_status` | string | Optimizer status: `"ok"` or error message |
| `vectors_count` | integer | Total number of vectors in the collection |
| `indexed_vectors_count` | integer | Number of vectors that have been indexed (should equal vectors_count) |
| `points_count` | integer | Total number of points (same as vectors_count) |
| `segments_count` | integer | Number of segments in the collection (internal Qdrant structure) |
| `config` | object | Collection configuration details |

#### Config Object Details

**params** - Vector configuration:
- `vectors.size`: Dimension of vectors (e.g., 384 for Cohere, 1536 for OpenAI)
- `vectors.distance`: Distance metric used (`"Cosine"`, `"Dot"`, `"Euclid"`)
- `shard_number`: Number of shards (1 for local deployment)
- `replication_factor`: Number of replicas (1 for local deployment)
- `write_consistency_factor`: Write consistency level
- `on_disk_payload`: Whether payloads are stored on disk

**hnsw_config** - HNSW index configuration:
- `m`: Number of edges per node in the graph (higher = better recall, more memory)
- `ef_construct`: Size of dynamic candidate list during construction (higher = better quality, slower indexing)
- `full_scan_threshold`: Point count below which full scan is used instead of index
- `max_indexing_threads`: Maximum threads for indexing (0 = auto)
- `on_disk`: Whether index is stored on disk

**optimizer_config** - Optimization settings:
- `deleted_threshold`: Threshold for triggering vacuum (0.2 = 20% deleted)
- `vacuum_min_vector_number`: Minimum vectors before vacuum runs
- `indexing_threshold`: Vectors count to trigger indexing
- `flush_interval_sec`: How often to flush to disk
- `max_optimization_threads`: Maximum threads for optimization

**wal_config** - Write-Ahead Log configuration:
- `wal_capacity_mb`: WAL size in megabytes
- `wal_segments_ahead`: Number of segments to keep ahead

### Error Responses

This endpoint typically doesn't return explicit error responses. If the collection doesn't exist, it will return information indicating 0 vectors.

## Implementation Details

### Source Code Locations
- **Route**: `src/routes/nlp.py` - `get_project_index_info()`
- **Controller**: `src/controllers/nlp_controller.py` - `NLPController.get_vector_db_collection_info()`
- **Model**: `src/models/project_model.py` - `ProjectModel`
- **VectorDB Provider**: `src/stores/vectordb/providers/QdrantDBProvider.py`

### Code Flow

#### 1. Project Retrieval
```python
project = await ProjectModel.get_project_from_db_or_insert_one(project_id)
```
- Retrieves project from MongoDB
- Auto-creates if doesn't exist

#### 2. Initialize NLP Controller
```python
nlp_controller = NLPController(
    vectordb_client=request.app.vectordb_client,
    generation_client=request.app.generation_client,
    embedding_client=request.app.embedding_client,
)
```

#### 3. Get Collection Info
```python
# Create collection name
collection_name = f"collection_{project.project_id}"

# Retrieve info from Qdrant
collection_info = vectordb_client.get_collection_info(collection_name)
```

#### 4. Serialize and Return
```python
# Convert Qdrant objects to JSON-serializable format
collection_info_json = json.loads(
    json.dumps(collection_info, default=lambda x: x.__dict__)
)

return {
    "signal": "vectordb_collection_retrieved_successfully",
    "collection_info": collection_info_json
}
```

### Qdrant API Call

The underlying Qdrant operation:
```python
client.get_collection(collection_name="collection_101")
```

Returns a `CollectionInfo` object with all metadata about the collection.

## Usage Examples

### cURL
```bash
curl -X GET "http://localhost:5000/api/v1/nlp/index/info/101"
```

### Python (requests)
```python
import requests

def get_collection_info(project_id):
    response = requests.get(
        f"http://localhost:5000/api/v1/nlp/index/info/{project_id}"
    )
    
    result = response.json()
    info = result["collection_info"]
    
    print(f"Status: {info['status']}")
    print(f"Vectors: {info['vectors_count']}")
    print(f"Indexed: {info['indexed_vectors_count']}")
    print(f"Vector Size: {info['config']['params']['vectors']['size']}")
    print(f"Distance: {info['config']['params']['vectors']['distance']}")
    
    return result

# Usage
info = get_collection_info("101")
```

### Python - Verify Indexing Complete
```python
def verify_indexing_complete(project_id, expected_count):
    """Verify that all chunks were successfully indexed"""
    response = requests.get(
        f"http://localhost:5000/api/v1/nlp/index/info/{project_id}"
    )
    
    info = response.json()["collection_info"]
    
    vectors_count = info["vectors_count"]
    indexed_count = info["indexed_vectors_count"]
    
    if vectors_count != indexed_count:
        print(f"Warning: Not all vectors indexed ({indexed_count}/{vectors_count})")
        return False
    
    if vectors_count != expected_count:
        print(f"Warning: Vector count mismatch (expected {expected_count}, got {vectors_count})")
        return False
    
    print(f"✓ Indexing complete: {vectors_count} vectors")
    return True
```

### Python - Monitor Collection Health
```python
def check_collection_health(project_id):
    """Check if collection is healthy and ready for queries"""
    response = requests.get(
        f"http://localhost:5000/api/v1/nlp/index/info/{project_id}"
    )
    
    info = response.json()["collection_info"]
    
    status = info["status"]
    optimizer_status = info["optimizer_status"]
    
    if status == "green" and optimizer_status == "ok":
        print(f"✓ Collection is healthy")
        return True
    else:
        print(f"✗ Collection has issues:")
        print(f"  Status: {status}")
        print(f"  Optimizer: {optimizer_status}")
        return False
```

### JavaScript (fetch)
```javascript
async function getCollectionInfo(projectId) {
  const response = await fetch(
    `http://localhost:5000/api/v1/nlp/index/info/${projectId}`
  );
  
  const result = await response.json();
  const info = result.collection_info;
  
  console.log(`Status: ${info.status}`);
  console.log(`Vectors: ${info.vectors_count}`);
  console.log(`Vector Size: ${info.config.params.vectors.size}`);
  
  return result;
}

// Usage
getCollectionInfo("101");
```

### Postman
1. Create a new GET request
2. Enter URL: `http://localhost:5000/api/v1/nlp/index/info/101`
3. Click "Send"
4. View the detailed JSON response

## Use Cases

### 1. Verify Indexing Completion
```python
def wait_for_indexing(project_id, expected_count, timeout=300):
    """Wait for indexing to complete"""
    import time
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        response = requests.get(
            f"http://localhost:5000/api/v1/nlp/index/info/{project_id}"
        )
        
        info = response.json()["collection_info"]
        
        if info["vectors_count"] >= expected_count:
            if info["indexed_vectors_count"] == info["vectors_count"]:
                print(f"✓ Indexing complete: {info['vectors_count']} vectors")
                return True
        
        print(f"Waiting... ({info['indexed_vectors_count']}/{expected_count})")
        time.sleep(5)
    
    print("✗ Timeout waiting for indexing")
    return False
```

### 2. Compare Collections
```python
def compare_collections(project_id1, project_id2):
    """Compare two project collections"""
    info1 = requests.get(
        f"http://localhost:5000/api/v1/nlp/index/info/{project_id1}"
    ).json()["collection_info"]
    
    info2 = requests.get(
        f"http://localhost:5000/api/v1/nlp/index/info/{project_id2}"
    ).json()["collection_info"]
    
    print(f"Project {project_id1}: {info1['vectors_count']} vectors")
    print(f"Project {project_id2}: {info2['vectors_count']} vectors")
    
    if info1['config']['params']['vectors']['size'] != info2['config']['params']['vectors']['size']:
        print("⚠ Warning: Different vector dimensions!")
```

### 3. Monitoring Dashboard
```python
def get_all_projects_stats(project_ids):
    """Get statistics for multiple projects"""
    stats = []
    
    for project_id in project_ids:
        response = requests.get(
            f"http://localhost:5000/api/v1/nlp/index/info/{project_id}"
        )
        
        info = response.json()["collection_info"]
        
        stats.append({
            "project_id": project_id,
            "status": info["status"],
            "vectors": info["vectors_count"],
            "indexed": info["indexed_vectors_count"],
            "segments": info["segments_count"]
        })
    
    return stats

# Usage
projects = ["101", "102", "103"]
stats = get_all_projects_stats(projects)

for stat in stats:
    print(f"{stat['project_id']}: {stat['vectors']} vectors ({stat['status']})")
```

### 4. Debugging Indexing Issues
```python
def diagnose_collection(project_id):
    """Diagnose potential issues with a collection"""
    response = requests.get(
        f"http://localhost:5000/api/v1/nlp/index/info/{project_id}"
    )
    
    info = response.json()["collection_info"]
    
    issues = []
    
    # Check status
    if info["status"] != "green":
        issues.append(f"Collection status is {info['status']}")
    
    # Check optimizer
    if info["optimizer_status"] != "ok":
        issues.append(f"Optimizer status: {info['optimizer_status']}")
    
    # Check indexing completion
    if info["vectors_count"] != info["indexed_vectors_count"]:
        issues.append(
            f"Indexing incomplete: {info['indexed_vectors_count']}/{info['vectors_count']}"
        )
    
    # Check if empty
    if info["vectors_count"] == 0:
        issues.append("Collection is empty")
    
    if issues:
        print("Issues found:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("✓ No issues found")
    
    return issues
```

## Performance Characteristics

- **Response Time**: < 100ms (local Qdrant query)
- **Resource Usage**: Minimal (metadata query only)
- **Concurrency**: Supports unlimited concurrent requests
- **Caching**: Can be cached (info changes only during indexing)

## Understanding the Response

### Status Values
- **green**: Collection is healthy and ready for queries
- **yellow**: Collection has warnings but is operational
- **red**: Collection has errors and may not work correctly

### Vector Counts
- `vectors_count`: Total vectors stored
- `indexed_vectors_count`: Vectors that have been indexed for search
- These should be equal when indexing is complete
- If `indexed_vectors_count` < `vectors_count`, indexing is still in progress

### Segments
- Qdrant organizes data into segments
- More segments = more memory overhead
- Qdrant automatically optimizes segment count
- Typical: 1 segment for small collections (< 100k vectors)

### Distance Metrics
- **Cosine**: Measures angle between vectors (normalized)
  - Best for: Semantic similarity, text embeddings
  - Range: -1 to 1 (higher = more similar)
- **Dot**: Dot product (not normalized)
  - Best for: When vector magnitude matters
- **Euclid**: Euclidean distance
  - Best for: Spatial data, when absolute distance matters

### HNSW Parameters
- **m=16**: Good balance of speed and accuracy
- **ef_construct=100**: Standard quality level
- Higher values = better search quality but slower indexing

## Related Endpoints
- **Previous Step**: `POST /api/v1/nlp/index/push/{project_id}` - Index chunks
- **Related**: `POST /api/v1/nlp/index/search/{project_id}` - Search the collection
- **Related**: `POST /api/v1/nlp/index/answer/{project_id}` - RAG queries

## Troubleshooting

### Issue: vectors_count is 0
**Cause**: Collection not indexed yet or indexing failed
**Solution**:
- Run `POST /api/v1/nlp/index/push/{project_id}`
- Verify chunks exist in MongoDB
- Check server logs for indexing errors

### Issue: indexed_vectors_count < vectors_count
**Cause**: Indexing still in progress
**Solution**:
- Wait for indexing to complete
- Check optimizer_status for errors
- If stuck, try reindexing with do_reset=1

### Issue: status is "yellow" or "red"
**Cause**: Collection has issues
**Solution**:
- Check optimizer_status for details
- Review Qdrant logs
- Try reindexing with do_reset=1
- Verify disk space and permissions

### Issue: Collection not found error
**Cause**: Collection was never created
**Solution**:
- Run indexing first: `POST /api/v1/nlp/index/push/{project_id}`
- Verify project_id is correct

### Issue: Wrong vector size
**Cause**: Embedding model changed after indexing
**Solution**:
- Reindex with do_reset=1 using new model
- Verify EMBEDDING_MODEL_SIZE in .env matches model output

### Issue: segments_count is very high
**Cause**: Many small indexing operations
**Solution**:
- This is normal and Qdrant will optimize automatically
- Can manually trigger optimization (not exposed in current API)
- Consider batch indexing instead of incremental
