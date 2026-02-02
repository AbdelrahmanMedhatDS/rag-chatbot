# Data Endpoint: Process Documents

## Overview
This endpoint processes uploaded documents by extracting their text content and splitting it into smaller, manageable chunks. These chunks are then stored in MongoDB and are ready for embedding and indexing in the vector database. This is a critical step in the RAG pipeline that transforms raw documents into searchable units.

## Endpoint Details

### HTTP Method & Path
```
POST /api/v1/data/process/{project_id}
```

### Tags
- `api_v1`
- `data`

### Authentication
None (to be implemented in production)

## Request

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_id` | string | Yes | Unique identifier for the project containing the files to process |

### Query Parameters
None

### Request Headers

| Header | Value | Required |
|--------|-------|----------|
| `Content-Type` | `application/json` | Yes |

### Request Body (JSON)

```json
{
  "file_id": "ko1wbnsq2m2o_AIBackendspecifications.pdf",
  "chunk_size": 1000,
  "overlap_size": 200,
  "do_reset": 0
}
```

#### Request Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `file_id` | string | No | null | Specific file to process. If null, processes all files in the project |
| `chunk_size` | integer | No | 100 | Maximum number of characters per chunk |
| `overlap_size` | integer | No | 20 | Number of characters to overlap between consecutive chunks |
| `do_reset` | integer | No | 0 | If 1, deletes all existing chunks for the project before processing |

#### Parameter Details

**chunk_size**
- Controls the granularity of text segmentation
- Smaller values (100-500): More precise retrieval, more chunks
- Larger values (1000-2000): More context per chunk, fewer chunks
- Recommended: 500-1500 for legal documents

**overlap_size**
- Prevents information loss at chunk boundaries
- Typical ratio: 10-20% of chunk_size
- Example: chunk_size=1000, overlap_size=200 (20% overlap)
- Ensures continuity when a concept spans chunk boundaries

**do_reset**
- `0`: Append new chunks to existing ones (incremental processing)
- `1`: Delete all existing chunks first (full reprocessing)
- Use case for reset: Changed chunking parameters, corrupted data

## Response

### Success Response (200 OK)

#### Response Body
```json
{
  "signal": "processing_completed",
  "inserted_chunks": 245,
  "processed_files": 3
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `signal` | string | Status indicator: `"processing_completed"` |
| `inserted_chunks` | integer | Total number of chunks created and stored in MongoDB |
| `processed_files` | integer | Number of files successfully processed |

### Error Responses

#### 400 Bad Request - File Not Found
```json
{
  "signal": "no_file_found_with_this_id"
}
```
**Cause**: The specified `file_id` doesn't exist in the project

#### 400 Bad Request - No Files in Project
```json
{
  "signal": "not_found_files"
}
```
**Cause**: The project has no uploaded files to process

#### 400 Bad Request - Processing Failed
```json
{
  "signal": "processing_failed"
}
```
**Cause**: Error during text extraction or chunking (corrupted file, unsupported format, etc.)

## Implementation Details

### Source Code Locations
- **Route**: `src/routes/data.py` - `process_endpoint()`
- **Controller**: `src/controllers/process_controller.py` - `ProcessController`
- **Model**: `src/models/chunk_model.py` - `ChunkModel`
- **Model**: `src/models/asset_model.py` - `AssetModel`
- **Model**: `src/models/project_model.py` - `ProjectModel`

### Code Flow

#### 1. Project and Asset Validation
```python
# Retrieve project from database
project = await ProjectModel.get_project_from_db_or_insert_one(project_id)

# Determine which files to process
if file_id:
    # Process single file
    asset_record = await AssetModel.get_asset_record_from_db(
        asset_project_id=project.id,
        asset_name=file_id
    )
    project_files_ids = {asset_record.id: asset_record.asset_name}
else:
    # Process all files in project
    project_files = await AssetModel.get_all_project_assets_from_db(
        asset_project_id=project.id,
        asset_type="file"
    )
    project_files_ids = {record.id: record.asset_name for record in project_files}
```

#### 2. Optional Reset
```python
if do_reset == 1:
    deleted_count = await ChunkModel.delete_chunks_from_db_by_project_id(
        project_id=project.id
    )
```

#### 3. File Processing Loop
For each file in `project_files_ids`:

**Step 3a: Load File Content**
```python
# Determine file type and create appropriate loader
file_extension = os.path.splitext(file_id)[-1]

if file_extension == ".txt":
    loader = TextLoader(file_path, encoding="utf-8")
elif file_extension == ".pdf":
    loader = PyMuPDFLoader(file_path)

# Load and parse document
docs = loader.load()  # Returns list of Document objects
```

**Document Object Structure**:
```python
Document(
    page_content="The text content of the page...",
    metadata={
        "source": "/path/to/file.pdf",
        "page": 0,  # For PDFs
        "file_path": "/path/to/file.pdf"
    }
)
```

**Step 3b: Split into Chunks**
```python
# Initialize text splitter
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=chunk_size,
    chunk_overlap=overlap_size,
    length_function=len,
)

# Extract text and metadata from documents
file_content_texts = [doc.page_content for doc in docs]
file_content_metadata = [doc.metadata for doc in docs]

# Create chunks while preserving metadata
chunks = text_splitter.create_documents(
    file_content_texts,
    metadatas=file_content_metadata
)
```

**Chunk Object Structure**:
```python
Document(
    page_content="A smaller segment of text...",
    metadata={
        "source": "/path/to/file.pdf",
        "page": 0
    }
)
```

**Step 3c: Create Chunk Records**
```python
file_chunks_records = [
    ChunkSchema(
        chunk_text=chunk.page_content,
        chunk_metadata=chunk.metadata,
        chunk_order=idx + 1,  # Sequential numbering
        chunk_project_id=project.id,
        chunk_asset_id=asset_id
    )
    for idx, chunk in enumerate(file_chunks)
]
```

**Step 3d: Batch Insert to MongoDB**
```python
# Insert in batches of 100
number_of_inserted = await ChunkModel.insert_many_chunks_in_db(
    chunks=file_chunks_records
)
```

#### 4. Return Summary
```python
return {
    "signal": "processing_completed",
    "inserted_chunks": total_inserted_chunks,
    "processed_files": number_of_processed_files
}
```

### Database Operations

#### MongoDB Collections Used

**Chunks Collection**
```javascript
{
  "_id": ObjectId("..."),
  "chunk_text": "This is the text content of the chunk...",
  "chunk_metadata": {
    "source": "/path/to/file.pdf",
    "page": 5,
    "file_path": "/path/to/file.pdf"
  },
  "chunk_order": 12,
  "chunk_project_id": ObjectId("..."),  // References project._id
  "chunk_asset_id": ObjectId("...")     // References asset._id
}
```

#### Indexes
- `chunk_project_id_index_1`: Non-unique index on `chunk_project_id` (for efficient project-wide queries)

### Text Splitting Algorithm

The system uses LangChain's `RecursiveCharacterTextSplitter`, which:

1. **Tries to split on natural boundaries** (in order of preference):
   - Double newlines (`\n\n`) - paragraph breaks
   - Single newlines (`\n`) - line breaks
   - Spaces (` `) - word boundaries
   - Characters - last resort

2. **Maintains chunk_size limit**: Ensures no chunk exceeds the specified size

3. **Applies overlap**: Includes the last `overlap_size` characters from the previous chunk

**Example**:
```
Original text: "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
chunk_size: 10
overlap_size: 3

Chunk 1: "ABCDEFGHIJ"
Chunk 2: "HIJKLMNOPQ"  (HIJ is overlap)
Chunk 3: "OPQRSTUVWX"  (OPQ is overlap)
Chunk 4: "VWXYZ"       (VWX is overlap)
```

### Configuration

Environment variables in `.env`:
```env
MONGODB_URL="mongodb://localhost:27010/"
MONGODB_DATABASE="legal-rag-chatbot"
```

## Usage Examples

### cURL - Process Single File
```bash
curl -X POST "http://localhost:5000/api/v1/data/process/101" \
  -H "Content-Type: application/json" \
  -d '{
    "file_id": "ko1wbnsq2m2o_AIBackendspecifications.pdf",
    "chunk_size": 1000,
    "overlap_size": 200,
    "do_reset": 0
  }'
```

### cURL - Process All Files in Project
```bash
curl -X POST "http://localhost:5000/api/v1/data/process/101" \
  -H "Content-Type: application/json" \
  -d '{
    "chunk_size": 1500,
    "overlap_size": 300,
    "do_reset": 0
  }'
```

### Python (requests) - Process with Reset
```python
import requests

project_id = "101"
payload = {
    "file_id": None,  # Process all files
    "chunk_size": 1000,
    "overlap_size": 200,
    "do_reset": 1  # Clear existing chunks first
}

response = requests.post(
    f"http://localhost:5000/api/v1/data/process/{project_id}",
    json=payload
)

result = response.json()
print(f"Processed {result['processed_files']} files")
print(f"Created {result['inserted_chunks']} chunks")
```

### JavaScript (fetch)
```javascript
const projectId = "101";
const payload = {
  file_id: "abc123_document.pdf",
  chunk_size: 1200,
  overlap_size: 240,
  do_reset: 0
};

fetch(`http://localhost:5000/api/v1/data/process/${projectId}`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(payload)
})
  .then(response => response.json())
  .then(data => console.log(data));
```

### Postman
1. Create a new POST request
2. Enter URL: `http://localhost:5000/api/v1/data/process/101`
3. Go to "Headers" tab, add: `Content-Type: application/json`
4. Go to "Body" tab, select "raw" and "JSON"
5. Enter JSON payload:
```json
{
  "file_id": "ko1wbnsq2m2o_AIBackendspecifications.pdf",
  "chunk_size": 1000,
  "overlap_size": 200,
  "do_reset": 0
}
```
6. Click "Send"

## Use Cases

### 1. Initial Processing After Upload
```python
def upload_and_process(project_id, file_path):
    # Step 1: Upload file
    with open(file_path, 'rb') as f:
        upload_response = requests.post(
            f"http://localhost:5000/api/v1/data/upload/{project_id}",
            files={'file': f}
        )
    
    file_id = upload_response.json()["file_id"]
    
    # Step 2: Process file
    process_response = requests.post(
        f"http://localhost:5000/api/v1/data/process/{project_id}",
        json={
            "file_id": file_id,
            "chunk_size": 1000,
            "overlap_size": 200
        }
    )
    
    return process_response.json()
```

### 2. Batch Processing All Files
```python
def process_all_project_files(project_id, chunk_size=1000):
    response = requests.post(
        f"http://localhost:5000/api/v1/data/process/{project_id}",
        json={
            "chunk_size": chunk_size,
            "overlap_size": int(chunk_size * 0.2)  # 20% overlap
        }
    )
    return response.json()
```

### 3. Reprocessing with Different Parameters
```python
def reprocess_with_new_params(project_id, new_chunk_size):
    # Reset and reprocess with new chunking parameters
    response = requests.post(
        f"http://localhost:5000/api/v1/data/process/{project_id}",
        json={
            "chunk_size": new_chunk_size,
            "overlap_size": int(new_chunk_size * 0.15),
            "do_reset": 1  # Clear old chunks
        }
    )
    return response.json()
```

### 4. Incremental Processing
```python
def add_and_process_new_file(project_id, new_file_path):
    # Upload new file
    with open(new_file_path, 'rb') as f:
        upload_resp = requests.post(
            f"http://localhost:5000/api/v1/data/upload/{project_id}",
            files={'file': f}
        )
    
    file_id = upload_resp.json()["file_id"]
    
    # Process only the new file (do_reset=0 keeps existing chunks)
    process_resp = requests.post(
        f"http://localhost:5000/api/v1/data/process/{project_id}",
        json={
            "file_id": file_id,
            "chunk_size": 1000,
            "overlap_size": 200,
            "do_reset": 0  # Keep existing chunks
        }
    )
    
    return process_resp.json()
```

## Performance Characteristics

- **Processing Speed**: 
  - TXT files: ~1-2 seconds per MB
  - PDF files: ~3-5 seconds per MB (depends on complexity)
- **Database Operations**: 
  - Batch inserts (100 chunks per batch)
  - Efficient for large documents
- **Memory Usage**: Loads entire file into memory (consider for very large files)
- **Concurrent Processing**: Supported (async operations)

## Chunking Strategy Recommendations

### For Legal Documents

**Short Contracts (< 10 pages)**
```json
{
  "chunk_size": 800,
  "overlap_size": 160
}
```

**Medium Documents (10-50 pages)**
```json
{
  "chunk_size": 1200,
  "overlap_size": 240
}
```

**Large Documents (> 50 pages)**
```json
{
  "chunk_size": 1500,
  "overlap_size": 300
}
```

### Considerations
- **Smaller chunks**: Better for precise fact retrieval
- **Larger chunks**: Better for understanding context and relationships
- **Overlap**: Essential for legal text where clauses may span boundaries

## Related Endpoints
- **Previous Step**: `POST /api/v1/data/upload/{project_id}` - Upload files first
- **Next Step**: `POST /api/v1/nlp/index/push/{project_id}` - Index chunks for search

## Troubleshooting

### Issue: "no_file_found_with_this_id"
**Cause**: Invalid file_id or file not in this project
**Solution**: 
- Verify file_id from upload response
- Check project_id matches upload project
- List project assets to confirm file exists

### Issue: "not_found_files"
**Cause**: No files uploaded to project
**Solution**: Upload files first using `/data/upload/{project_id}`

### Issue: "processing_failed"
**Cause**: File parsing error
**Solution**:
- Verify file is not corrupted
- Check file format is truly PDF or TXT
- Review server logs for detailed error
- Try re-uploading the file

### Issue: Very few chunks created
**Cause**: chunk_size too large or file has little text
**Solution**:
- Reduce chunk_size parameter
- Verify file contains extractable text (not scanned images)
- For PDFs, ensure text is not embedded as images

### Issue: Too many chunks created
**Cause**: chunk_size too small
**Solution**:
- Increase chunk_size parameter
- Consider impact on retrieval quality
- Balance between precision and context

### Issue: Processing takes very long
**Cause**: Large file or complex PDF
**Solution**:
- Check file size and complexity
- Consider splitting large documents
- Monitor server resources (CPU, memory)
- Process files individually rather than all at once

### Issue: Chunks missing context
**Cause**: overlap_size too small
**Solution**:
- Increase overlap_size (typically 15-25% of chunk_size)
- Test retrieval quality after adjustment
