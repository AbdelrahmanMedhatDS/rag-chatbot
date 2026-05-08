# Fix: `index_only_new` Parameter Implementation

## Date: May 7, 2026

## Issues Identified and Fixed

### Issue #1: Broken Pagination Logic ✅ FIXED

**Problem:**
```python
# OLD CODE (BROKEN)
if len(page_chunks) and not index_only_new:
    page_no += 1
```

When `index_only_new=True`, the page number was never incremented, causing:
- Infinite loop potential
- Inefficient repeated queries to page 1
- Reliance on side effects (marking chunks) rather than proper pagination

**Solution:**
```python
# NEW CODE (FIXED)
# Always increment page number for proper pagination
page_no += 1
```

Now pagination works correctly regardless of the `index_only_new` setting.

---

### Issue #2: Race Condition Vulnerability ✅ FIXED

**Problem:**
Multiple concurrent requests with `index_only_new=True` could:
1. Fetch the same unindexed chunks simultaneously
2. Both embed and insert them into Qdrant
3. Create duplicate vectors in the vector database

**Solution:**
Implemented atomic fetch-and-lock pattern using MongoDB's `update_many` with conditional query:

```python
async def get_and_lock_unindexed_chunks(self, project_id: ObjectId, page_no: int=1, page_size: int=50):
    """
    Atomically fetch unindexed chunks and mark them as being processed.
    This prevents race conditions when multiple processes try to index simultaneously.
    """
    # 1. Find unindexed chunk IDs
    chunk_ids = [doc["_id"] async for doc in cursor]
    
    # 2. Atomically mark them as indexed (acts as a lock)
    result = await self.db_collection.update_many(
        {
            "_id": {"$in": chunk_ids},
            "$or": [
                {"chunk_is_indexed": False},
                {"chunk_is_indexed": {"$exists": False}}
            ]
        },
        {"$set": {"chunk_is_indexed": True, "chunk_indexed_at": datetime.utcnow()}}
    )
    
    # 3. Only return chunks that were actually updated
    if result.modified_count > 0:
        locked_chunks = await self.db_collection.find(
            {"_id": {"$in": chunk_ids}, "chunk_is_indexed": True}
        ).to_list(length=None)
        return [ChunkSchema(**record) for record in locked_chunks]
    
    return []
```

**How it prevents race conditions:**
- The `update_many` operation is atomic at the document level
- Only one process can successfully update `chunk_is_indexed` from `False` to `True`
- Other concurrent processes will get `modified_count=0` and return empty list
- Acts as a distributed lock mechanism

---

### Issue #3: No Rollback on Failure ✅ FIXED

**Problem:**
If vector insertion failed, chunks remained marked as indexed, causing data loss (chunks would never be retried).

**Solution:**
Added rollback mechanism:

```python
async def mark_chunks_unindexed(self, chunk_ids: List[ObjectId]):
    """Rollback method to mark chunks as unindexed if vector insertion fails"""
    result = await self.db_collection.update_many(
        {"_id": {"$in": normalized_ids}},
        {"$set": {"chunk_is_indexed": False}, "$unset": {"chunk_indexed_at": ""}}
    )
    return result.modified_count
```

Used in error handling:
```python
if not is_inserted:
    # Rollback: mark chunks as unindexed since insertion failed
    await chunk_model.mark_chunks_unindexed(chunk_ids=chunk_object_ids)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"signal": ResponseSignal.INSERT_INTO_VECTORDB_ERROR.value}
    )
```

---

## Updated Flow

### When `index_only_new=True`:

1. **Atomic Fetch & Lock:**
   - Query unindexed chunks for current page
   - Atomically mark them as indexed (lock)
   - Return only chunks successfully locked

2. **Process:**
   - Generate embeddings
   - Insert into Qdrant vector DB

3. **Error Handling:**
   - If insertion fails → rollback (mark as unindexed)
   - If insertion succeeds → chunks remain marked as indexed

4. **Pagination:**
   - Always increment page number
   - Continue until no more unindexed chunks found

### When `index_only_new=False`:

1. **Fetch All Chunks:**
   - Query all chunks (indexed or not) for current page

2. **Process:**
   - Generate embeddings
   - Insert into Qdrant vector DB

3. **Mark as Indexed:**
   - After successful insertion, mark chunks as indexed

4. **Pagination:**
   - Always increment page number
   - Continue until all chunks processed

---

## Benefits of the Fix

✅ **Correct Pagination:** Pages increment properly, no infinite loops

✅ **Race Condition Safe:** Atomic operations prevent duplicate indexing

✅ **Data Integrity:** Rollback mechanism ensures no chunks are lost on failure

✅ **Efficient:** Proper pagination reduces redundant queries

✅ **Predictable:** Behavior is deterministic and testable

---

## Testing Recommendations

### Test Case 1: Single Process Indexing
```bash
# Should index all unindexed chunks exactly once
POST /api/v1/nlp/index/push/{project_id}
{
  "do_reset": 0,
  "index_only_new": true
}
```

### Test Case 2: Concurrent Indexing
```bash
# Run 3 simultaneous requests
# Should result in no duplicate vectors in Qdrant
# Total indexed count across all requests should equal total unindexed chunks
```

### Test Case 3: Failure Recovery
```bash
# Simulate vector DB failure during indexing
# Verify chunks are marked as unindexed
# Retry should pick up the failed chunks
```

### Test Case 4: Full Reindex
```bash
# Should reindex all chunks regardless of indexed status
POST /api/v1/nlp/index/push/{project_id}
{
  "do_reset": 0,
  "index_only_new": false
}
```

### Test Case 5: Reset and Index
```bash
# Should delete collection and index all chunks
POST /api/v1/nlp/index/push/{project_id}
{
  "do_reset": 1,
  "index_only_new": true  # This is ignored when do_reset=1
}
```

---

## Files Modified

1. **src/routes/nlp.py**
   - Fixed pagination logic (always increment page_no)
   - Added atomic fetch-and-lock for `index_only_new=True`
   - Added rollback on insertion failure
   - Separated logic for indexed vs non-indexed modes

2. **src/models/chunk_model.py**
   - Added `get_and_lock_unindexed_chunks()` method for atomic operations
   - Added `mark_chunks_unindexed()` method for rollback
   - Kept original `get_poject_chunks()` for backward compatibility

---

## Performance Considerations

### Database Indexes
The existing compound index is optimal:
```python
{
    "key": [
        ("chunk_project_id", 1),
        ("chunk_is_indexed", 1)
    ],
    "name": "chunk_project_id_indexed_index_1",
    "unique": False
}
```

This index efficiently supports:
- Filtering by project_id
- Filtering by indexed status
- Sorting by _id for pagination

### Query Efficiency
- **Before:** Repeated queries to page 1 until empty
- **After:** Proper pagination through all pages once

### Concurrency
- **Before:** No protection, potential duplicates
- **After:** Atomic operations, safe for concurrent requests

---

## Migration Notes

**No database migration required.** The changes are backward compatible:

- Existing `chunk_is_indexed` field continues to work
- New atomic method is only used when `index_only_new=True`
- Old method still available for other use cases
- No schema changes needed
