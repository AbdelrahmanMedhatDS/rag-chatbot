# Data Endpoint: Upload File

## Overview
This endpoint allows users to upload documents (PDF or TXT files) to a specific project. The file is validated, stored on the server, and its metadata is recorded in the database for later processing.

## Endpoint Details

### HTTP Method & Path
```
POST /api/v1/data/upload/{project_id}
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
| `project_id` | string | Yes | Unique identifier for the project. Must be alphanumeric. If the project doesn't exist, it will be created automatically. |

### Query Parameters
None

### Request Headers

| Header | Value | Required | Description |
|--------|-------|----------|-------------|
| `Content-Type` | `multipart/form-data` | Yes | Required for file upload |

### Request Body (Form Data)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | File | Yes | The document file to upload. Must be PDF or TXT format. |

#### File Constraints
- **Allowed MIME Types**: 
  - `text/plain` (TXT files)
  - `application/pdf` (PDF files)
- **Maximum Size**: 10 MB (configurable via `FILE_MAX_SIZE` in `.env`)
- **Filename**: Will be sanitized (special characters removed, spaces replaced with underscores)

## Response

### Success Response (200 OK)

#### Response Body
```json
{
  "signal": "file_upload_success",
  "file_id": "ko1wbnsq2m2o_AIBackendspecifications.pdf",
  "asset's refrence": "ko1wbnsq2m2o_AIBackendspecifications.pdf"
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `signal` | string | Status indicator: `"file_upload_success"` |
| `file_id` | string | Unique identifier for the uploaded file (random_key + cleaned filename) |
| `asset's refrence` | string | Reference name stored in the database (same as file_id) |

### Error Responses

#### 400 Bad Request - Invalid File Type
```json
{
  "signal": "file_type_not_supported"
}
```
**Cause**: File MIME type is not in the allowed list

#### 400 Bad Request - File Too Large
```json
{
  "signal": "file_size_exceeded"
}
```
**Cause**: File size exceeds the configured maximum (default: 10 MB)

#### 400 Bad Request - Upload Failed
```json
{
  "signal": "file_upload_failed"
}
```
**Cause**: Error occurred during file writing to disk (permissions, disk space, etc.)

## Implementation Details

### Source Code Locations
- **Route**: `src/routes/data.py` - `upload_data()`
- **Controller**: `src/controllers/data_controller.py` - `DataController`
- **Model**: `src/models/project_model.py` - `ProjectModel`
- **Model**: `src/models/asset_model.py` - `AssetModel`

### Code Flow

1. **Project Initialization**
   - Retrieves or creates project record in MongoDB
   - Uses `ProjectModel.get_project_from_db_or_insert_one()`

2. **File Validation**
   - Checks MIME type against allowed types
   - Verifies file size is within limits
   - Uses `DataController.validate_uploaded_file()`

3. **File Path Generation**
   - Generates random 12-character key (lowercase letters + digits)
   - Cleans original filename (removes special chars, replaces spaces)
   - Creates unique path: `src/assets/files/{project_id}/{random_key}_{cleaned_filename}`
   - Ensures no collision with existing files
   - Uses `DataController.generate_unique_filepath()`

4. **File Storage**
   - Writes file to disk in chunks (default: 512 KB chunks)
   - Uses async file I/O (`aiofiles`) for non-blocking operations
   - Creates project directory if it doesn't exist

5. **Asset Record Creation**
   - Creates `AssetSchema` object with metadata:
     - `asset_project_id`: Reference to parent project
     - `asset_type`: "file" (from `AssetTypeEnum.FILE`)
     - `asset_name`: The file_id (random_key + filename)
     - `asset_size`: File size in bytes
     - `asset_pushed_at`: Current UTC timestamp
   - Inserts record into MongoDB `assets` collection
   - Uses `AssetModel.insert_asset_in_db()`

### Database Operations

#### MongoDB Collections Used

**Projects Collection**
```javascript
{
  "_id": ObjectId("..."),
  "project_id": "101"
}
```

**Assets Collection**
```javascript
{
  "_id": ObjectId("..."),
  "asset_project_id": ObjectId("..."),  // References project._id
  "asset_type": "file",
  "asset_name": "ko1wbnsq2m2o_AIBackendspecifications.pdf",
  "asset_size": 2458624,  // bytes
  "asset_config": null,
  "asset_pushed_at": ISODate("2026-02-02T10:30:00Z")
}
```

#### Indexes
- `asset_project_id_index_1`: Non-unique index on `asset_project_id`
- `asset_project_id_name_index_1`: Unique compound index on `(asset_project_id, asset_name)`

### File System Structure
```
src/assets/files/
└── {project_id}/
    ├── {random_key1}_{filename1}.pdf
    ├── {random_key2}_{filename2}.txt
    └── {random_key3}_{filename3}.pdf
```

### Configuration

Environment variables in `.env`:
```env
FILE_VALIDE_TYPES=["text/plain", "application/pdf"]
FILE_MAX_SIZE=10  # MB
MAX_CHUNK_SIZE=512000  # 512 KB (for streaming upload)
```

## Usage Examples

### cURL
```bash
curl -X POST "http://localhost:5000/api/v1/data/upload/101" \
  -F "file=@/path/to/document.pdf"
```

### Python (requests)
```python
import requests

project_id = "101"
file_path = "/path/to/document.pdf"

with open(file_path, 'rb') as f:
    files = {'file': f}
    response = requests.post(
        f"http://localhost:5000/api/v1/data/upload/{project_id}",
        files=files
    )

print(response.json())
# Output: {
#   "signal": "file_upload_success",
#   "file_id": "abc123xyz456_document.pdf",
#   "asset's refrence": "abc123xyz456_document.pdf"
# }
```

### JavaScript (FormData)
```javascript
const projectId = "101";
const fileInput = document.querySelector('input[type="file"]');
const formData = new FormData();
formData.append('file', fileInput.files[0]);

fetch(`http://localhost:5000/api/v1/data/upload/${projectId}`, {
  method: 'POST',
  body: formData
})
  .then(response => response.json())
  .then(data => console.log(data));
```

### Postman
1. Create a new POST request
2. Enter URL: `http://localhost:5000/api/v1/data/upload/101`
3. Go to "Body" tab
4. Select "form-data"
5. Add key: `file`, change type to "File"
6. Select your PDF or TXT file
7. Click "Send"

## Use Cases

### 1. Single Document Upload
Upload one legal document to a project:
```python
def upload_legal_document(project_id, file_path):
    with open(file_path, 'rb') as f:
        response = requests.post(
            f"http://localhost:5000/api/v1/data/upload/{project_id}",
            files={'file': f}
        )
    
    if response.json()["signal"] == "file_upload_success":
        return response.json()["file_id"]
    else:
        raise Exception(f"Upload failed: {response.json()['signal']}")
```

### 2. Batch Upload
Upload multiple documents to the same project:
```python
def batch_upload(project_id, file_paths):
    file_ids = []
    for file_path in file_paths:
        file_id = upload_legal_document(project_id, file_path)
        file_ids.append(file_id)
        print(f"Uploaded: {file_path} -> {file_id}")
    return file_ids
```

### 3. Upload with Validation
```python
import os

def safe_upload(project_id, file_path):
    # Pre-validate before upload
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    
    if file_size_mb > 10:
        raise ValueError(f"File too large: {file_size_mb:.2f} MB")
    
    if not file_path.endswith(('.pdf', '.txt')):
        raise ValueError("Only PDF and TXT files are supported")
    
    return upload_legal_document(project_id, file_path)
```

## Performance Characteristics

- **Upload Speed**: Depends on file size and network bandwidth
- **Chunked Upload**: Files are read and written in 512 KB chunks (non-blocking)
- **Concurrent Uploads**: Supported (async operations)
- **Database Operations**: 2 queries (1 project lookup/insert, 1 asset insert)

## Security Considerations

### Current Implementation
- Filename sanitization (removes special characters)
- File type validation (MIME type check)
- File size limits
- Random key prefix prevents filename guessing

### Production Recommendations
1. **Add Authentication**: Verify user has permission to upload to project
2. **Virus Scanning**: Scan uploaded files for malware
3. **Rate Limiting**: Prevent abuse (e.g., 10 uploads per minute per user)
4. **Quota Management**: Limit total storage per project/user
5. **Content Validation**: Verify file content matches MIME type
6. **Encryption**: Encrypt files at rest
7. **Audit Logging**: Log all upload activities with user information

## Related Endpoints
- **Next Step**: `POST /api/v1/data/process/{project_id}` - Process uploaded files into chunks
- **Query**: `POST /api/v1/nlp/index/push/{project_id}` - Index processed chunks for search

## Troubleshooting

### Issue: "file_type_not_supported"
**Cause**: File MIME type not allowed
**Solution**: 
- Ensure file is PDF or TXT
- Check file extension matches content
- Verify `FILE_VALIDE_TYPES` in `.env`

### Issue: "file_size_exceeded"
**Cause**: File larger than 10 MB
**Solution**:
- Compress or split the file
- Increase `FILE_MAX_SIZE` in `.env` (requires restart)

### Issue: "file_upload_failed"
**Cause**: Disk write error
**Solution**:
- Check disk space: `df -h`
- Verify directory permissions
- Check server logs for detailed error

### Issue: Duplicate file_id
**Cause**: Extremely rare collision in random key generation
**Solution**: The system automatically retries with a new random key

### Issue: Project not found in subsequent operations
**Cause**: Project was created but database connection lost
**Solution**: Verify MongoDB connection is stable
