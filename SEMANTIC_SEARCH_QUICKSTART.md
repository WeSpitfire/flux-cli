# Semantic Search - Quick Start

## What It Does

Search your codebase using **natural language** instead of exact text patterns.

```bash
# Traditional grep (exact text)
grep -r "def.*error" .

# Semantic search (meaning-based)
/semantic-search error handling logic
```

## Two Commands

### 1. Index Your Project (one-time)

```bash
/index-project
```

Takes ~2 minutes for 200 files. Creates `.flux/embeddings/` directory.

### 2. Search Your Code

```bash
/semantic-search <your query>
```

Examples:
- `/semantic-search authentication middleware`
- `/semantic-search database connection pooling`
- `/semantic-search parallel execution and concurrency`
- `/semantic-search error handling with retry logic`

## How It Works

1. **Indexing**: Breaks code into 80-line chunks, generates OpenAI embeddings
2. **Search**: Converts your query to embedding, finds similar code chunks
3. **Results**: Shows top 5 matches with relevance scores (HIGH/MEDIUM/LOW)

## When to Use

| Use Semantic Search | Use grep |
|---------------------|----------|
| Finding concepts | Finding exact symbols |
| Discovering patterns | Known function names |
| Understanding architecture | String literals |
| Onboarding new code | Variable references |

## Examples

**Query**: "Where do we validate user input?"  
**Finds**: All validation logic, even if not named "validate"

**Query**: "How do we handle database errors?"  
**Finds**: Error handling code for database operations

**Query**: "Show me authentication middleware"  
**Finds**: Auth middleware even if named differently

## Cost

- **Indexing**: ~$0.01 per 1000 files (one-time)
- **Searching**: ~$0.000001 per search (negligible)

## AI Integration

Flux AI can automatically use semantic search:

```
User: "Show me where we handle file uploads"
AI: [automatically uses semantic_search tool]
```

## Limitations

- Must re-index after major code changes
- Only indexes common file types (.py, .js, .ts, .go, etc.)
- Max 1000 files by default (use `/index-project 5000` for more)

## Full Documentation

See [SEMANTIC_SEARCH.md](./SEMANTIC_SEARCH.md) for complete details.

---

**Status**: ✅ Ready to use  
**Commands**: `/index-project` + `/semantic-search <query>`
