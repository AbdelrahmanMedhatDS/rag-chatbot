# Vector Inspection Endpoints (Qdrant)

## Overview

These endpoints allow you to inspect vectors in a Qdrant collection, detect duplicate payload texts, and list all collections with statistics.

## Base Path

```
/api/v1/vectors
```

---

## 1. Inspect Vectors in a Collection

### HTTP Method & Path

```
POST /api/v1/vectors/inspect/{collection_name}
```

### Request Body (JSON)

```json
{
  "limit": 50,
  "offset": 0,
  "include_vectors": true
}
```

#### Request Fields

| Field             | Type            | Required | Default | Description                                       |
| ----------------- | --------------- | -------- | ------- | ------------------------------------------------- |
| `limit`           | integer         | No       | 50      | Max number of vectors to return (clamped to 1000) |
| `offset`          | string\|integer | No       | 0       | Cursor id from previous response (`next_offset`)  |
| `include_vectors` | boolean         | No       | true    | If true, includes `vector_sample` for each record |

### Success Response (200 OK)

```json
{
  "signal": "vectordb_collection_inspected_successfully",
  "collection_name": "collection_1",
  "total_vectors": 1260,
  "returned_vectors": 50,
  "offset": 0,
  "next_offset": "50",
  "limit": 50,
  "vectors": [
    {
      "id": "0",
      "text": "Example text",
      "text_length": 12,
      "metadata": {
        "source": "/path/to/file.pdf",
        "page": 0
      },
      "vector_sample": [0.01, -0.02, 0.03, 0.04, -0.01],
      "vector_length": 384
    }
  ]
}
```

---

## 2. Detect Duplicate Texts

### HTTP Method & Path

```
POST /api/v1/vectors/duplicates/{collection_name}
```

### Request Body (JSON)

```json
{
  "limit": 5000,
  "offset": 0,
  "min_count": 2,
  "max_groups": 100
}
```

#### Request Fields

| Field        | Type            | Required | Default | Description                                      |
| ------------ | --------------- | -------- | ------- | ------------------------------------------------ |
| `limit`      | integer         | No       | 5000    | Max number of points to scan for duplicates      |
| `offset`     | string\|integer | No       | 0       | Cursor id from previous response (`next_offset`) |
| `min_count`  | integer         | No       | 2       | Minimum occurrences to be considered a duplicate |
| `max_groups` | integer         | No       | 100     | Max number of duplicate groups to return         |

### Success Response (200 OK)

```json
{
  "signal": "vectordb_duplicates_detected_successfully",
  "collection_name": "collection_1",
  "total_vectors": 1260,
  "scanned_vectors": 1000,
  "returned_duplicates": 2,
  "offset": 0,
  "next_offset": "1000",
  "limit": 5000,
  "min_count": 2,
  "duplicates": [
    {
      "text": "Duplicate text example",
      "count": 3,
      "ids": ["10", "42", "87"]
    }
  ]
}
```

---

## 3. List Collections with Stats

### HTTP Method & Path

```
GET /api/v1/vectors/collections
```

### Success Response (200 OK)

```json
{
  "signal": "vectordb_collections_list_successfully",
  "count": 2,
  "collections": [
    {
      "collection_name": "collection_1",
      "status": "green",
      "points_count": 1260,
      "vectors_count": 1260,
      "indexed_vectors_count": 1260,
      "segments_count": 1,
      "vector_size": 384
    }
  ]
}
```
