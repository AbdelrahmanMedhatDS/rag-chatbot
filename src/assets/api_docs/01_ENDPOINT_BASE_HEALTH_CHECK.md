# Base Endpoint: Health Check

## Overview
This endpoint provides a simple health check mechanism to verify that the API is running and to retrieve basic application information.

## Endpoint Details

### HTTP Method & Path
```
GET /api/v1/
```

### Tags
- `api_v1`

### Authentication
None required (public endpoint)

## Request

### Path Parameters
None

### Query Parameters
None

### Request Headers
None required

### Request Body
None

## Response

### Success Response (200 OK)

#### Response Body
```json
{
  "app name": "legal-rag-chatbot",
  "app version": "0.1"
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `app name` | string | The name of the application as configured in environment variables |
| `app version` | string | The current version of the application |

### Error Responses
This endpoint does not return error responses under normal circumstances. If the API is down, you will receive a connection error.

## Implementation Details

### Source Code Location
- **Route**: `src/routes/base.py`
- **Function**: `read_root()`

### Dependencies
- **Settings**: Injected via `Depends(get_settings)`
  - Retrieves `APP_NAME` from environment
  - Retrieves `APP_VERSION` from environment

### Code Flow

1. **Dependency Injection**: FastAPI injects the application settings
2. **Data Retrieval**: Extracts `APP_NAME` and `APP_VERSION` from settings
3. **Response Construction**: Returns a simple JSON object with app information

### Configuration

The values returned by this endpoint are configured in the `.env` file:

```env
APP_NAME="legal-rag-chatbot"
APP_VERSION="0.1"
```

## Usage Examples

### cURL
```bash
curl -X GET "http://localhost:5000/api/v1/"
```

### Python (requests)
```python
import requests

response = requests.get("http://localhost:5000/api/v1/")
print(response.json())
# Output: {'app name': 'legal-rag-chatbot', 'app version': '0.1'}
```

### JavaScript (fetch)
```javascript
fetch('http://localhost:5000/api/v1/')
  .then(response => response.json())
  .then(data => console.log(data));
// Output: {app name: "legal-rag-chatbot", app version: "0.1"}
```

### Postman
1. Create a new GET request
2. Enter URL: `http://localhost:5000/api/v1/`
3. Click "Send"
4. View the JSON response in the response body

## Use Cases

### 1. Health Monitoring
Use this endpoint in monitoring systems to verify the API is responsive:
```bash
# Simple health check script
if curl -f http://localhost:5000/api/v1/ > /dev/null 2>&1; then
    echo "API is healthy"
else
    echo "API is down"
fi
```

### 2. Version Verification
Check the deployed version before running integration tests:
```python
def verify_api_version(expected_version):
    response = requests.get("http://localhost:5000/api/v1/")
    actual_version = response.json()["app version"]
    assert actual_version == expected_version, f"Version mismatch: {actual_version}"
```

### 3. Load Balancer Health Check
Configure your load balancer to ping this endpoint to determine if an instance is healthy.

## Performance Characteristics

- **Response Time**: < 10ms (no database queries)
- **Resource Usage**: Minimal (only reads from memory)
- **Concurrency**: Supports unlimited concurrent requests
- **Caching**: Response can be cached (values don't change during runtime)

## Related Endpoints
None - this is a standalone utility endpoint

## Notes

- This endpoint is intentionally simple and fast
- It does not verify database connectivity or external service availability
- For comprehensive health checks, consider adding a dedicated `/health` endpoint that tests:
  - MongoDB connection
  - Vector database connection
  - LLM API availability
  - Disk space
  - Memory usage

## Troubleshooting

### Issue: Endpoint returns 404
**Cause**: API server is not running or wrong URL
**Solution**: 
1. Verify the server is running: `ps aux | grep uvicorn`
2. Check the correct port (default: 5000)
3. Ensure the URL includes `/api/v1/`

### Issue: Connection refused
**Cause**: Server is not running or firewall blocking
**Solution**:
1. Start the server: `uvicorn main:app --reload --host 0.0.0.0 --port 5000`
2. Check firewall rules
3. Verify the host and port configuration

### Issue: Wrong app name or version
**Cause**: Environment variables not loaded
**Solution**:
1. Verify `.env` file exists in `src/` directory
2. Check `APP_NAME` and `APP_VERSION` are set correctly
3. Restart the server to reload environment variables
