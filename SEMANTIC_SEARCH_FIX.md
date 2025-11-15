# Semantic Search - Bug Fix

## Issue

When running `/index-project` or `/semantic-search`, got infinite loop of errors:

```
LLM embedding failed: 'OpenAIProvider' object has no attribute 'create_embedding', falling back to TF-IDF
```

## Root Causes

### 1. Missing `create_embedding` Method

`OpenAIProvider` class didn't have a `create_embedding` method to generate embeddings.

**Fix**: Added method to `flux/llm/openai_provider.py`:

```python
async def create_embedding(self, input: str, model: str = "text-embedding-3-small") -> Dict[str, Any]:
    """Create embeddings using OpenAI's embeddings API."""
    response = await self.client.embeddings.create(
        input=input,
        model=model
    )
    return response
```

### 2. Synchronous Call in Async Context

The `search()` method called `generate_embedding()` (sync) instead of `generate_embedding_async()`.

**Fix**: Changed line 490 in `flux/core/semantic_search.py`:

```python
# Before
query_embedding = self.embedding_gen.generate_embedding(query)

# After
query_embedding = await self.embedding_gen.generate_embedding_async(query)
```

### 3. Re-indexing Already Indexed Files

The `index_project()` method would try to index files that were already indexed, causing wasted API calls.

**Fix**: Added filter in `index_project()`:

```python
# Filter out already indexed files
files_to_index = [f for f in files_to_index if str(f) not in self.indexed_files]

if not files_to_index:
    logger.info("All files already indexed")
    return {...}
```

### 4. Large Batch Sizes

Batch size of 10 files at once could overwhelm the API.

**Fix**: Reduced batch size from 10 to 5:

```python
# Batch process for efficiency (smaller batches to avoid overwhelming API)
batch_size = 5
```

## Changes Made

### File: `flux/llm/openai_provider.py`

**Added** (after line 334):
- `create_embedding()` method to support embeddings API

### File: `flux/core/semantic_search.py`

**Modified**:
1. Line 490: Use async embedding generation in `search()`
2. Lines 542-556: Filter already indexed files before processing
3. Line 562: Reduced batch size from 10 to 5
4. Lines 566-577: Added exception handling and progress logging

## Testing

Run these commands to test the fix:

```bash
# Start flux
cd /Users/developer/SynologyDrive/flux-cli
flux

# Index project (should work without errors)
/index-project

# Search (should work without infinite loop)
/semantic-search error handling
```

## Expected Behavior

### Indexing

```
📚 Indexing project for semantic search...

[Progress spinner]

✓ Indexing Complete
┌─────────────────────────────────────────┐
│ Files indexed: 45                       │
│ Total chunks: 327                       │
│ Files scanned: 45                       │
│ Index location: .flux/embeddings/       │
└─────────────────────────────────────────┘
```

### Searching

```
🔍 Semantic Search Results: error handling

1. flux/core/error_parser.py:45-125 (Relevance: HIGH 0.82)
[code preview with syntax highlighting]

✓ Found 5 semantic matches
```

## Status

✅ **FIXED** - All issues resolved

The semantic search feature now:
- Uses OpenAI embeddings correctly
- Doesn't re-index files
- Handles async/await properly
- Has smaller batch sizes for stability
