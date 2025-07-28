# Vector Index Optimization Guide

## Overview

The Memory Agent now includes intelligent vector index optimization that automatically adjusts indexing strategies based on data characteristics. This optimization considers:

- Dataset size and growth patterns
- User distribution (light vs power users)
- Memory type distribution
- Query patterns and performance requirements

## Key Features

### 1. Automatic Index Selection

The optimizer automatically chooses the best index type based on data size:

| Row Count | Index Type | Strategy |
|-----------|------------|----------|
| < 1,000 | None | Sequential scan (faster for small datasets) |
| 1K - 10K | IVFFlat Basic | Simple clustering with few lists |
| 10K - 100K | IVFFlat Optimized | Tuned based on user patterns |
| 100K - 500K | Partitioned IVFFlat | User-based partitioning |
| > 500K | HNSW | High accuracy for large datasets |

### 2. User-Aware Optimization

The optimizer analyzes user patterns:

```python
# User Classifications
- Light users: < 10 memories
- Medium users: 10-100 memories  
- Heavy users: 100-1000 memories
- Power users: > 1000 memories
```

When power users represent > 20% of the user base, the optimizer:
- Increases search accuracy (more probes)
- Adds composite indexes for user-based queries
- Optimizes for frequent access patterns

### 3. Dynamic Search Optimization

Search queries are optimized based on context:

```python
# Optimization Modes
- "speed": Fast results, may sacrifice some accuracy
- "balanced": Good trade-off between speed and accuracy
- "accuracy": Best results, may be slower

# Automatic Selection
- Conversations → accuracy (context matters)
- High importance (≥8) → accuracy
- Large result sets (>20) → speed
- Default → balanced
```

## Using the Optimization Tools

### 1. Manual Optimization

```python
# Optimize index (usually automatic)
result = await optimize_vector_index(
    table_name="user_memories",
    force=True  # Force even if recently optimized
)
```

### 2. Get Performance Stats

```python
# Check current performance
stats = await get_index_performance_stats()

# Get detailed table statistics
details = await get_memory_table_stats()
```

### 3. Benchmark Performance

```python
# Compare different optimization strategies
benchmarks = await benchmark_vector_search(
    sample_size=10,
    test_queries=5
)
```

### 4. Manual Tuning

```python
# Fine-tune search parameters
await set_vector_search_params(
    probes=20,  # IVFFlat accuracy (1-1000)
    ef_search=100  # HNSW accuracy (10-500)
)
```

## Optimization Strategies

### Small Datasets (<1K rows)
- No index needed
- Sequential scan is faster
- Focuses on query optimization

### Medium Datasets (1K-100K rows)
- IVFFlat with dynamic list calculation
- Lists = rows/500 to rows/1000
- Probes adjusted based on user patterns

### Large Datasets (>100K rows)
- Consider user distribution:
  - Few users → Partition by user_id
  - Many users → HNSW for best accuracy
- Composite indexes for common filters

## Performance Tuning

### IVFFlat Parameters

```python
# Lists (clustering)
- More lists = Better search accuracy, slower build
- Fewer lists = Faster search, lower accuracy
- Formula: lists = max(row_count / 1000, 30)

# Probes (search accuracy)  
- More probes = Higher accuracy, slower search
- Fewer probes = Faster search, lower accuracy
- Range: 1-100 (typically 5-50)
```

### HNSW Parameters

```python
# M (connections per node)
- Higher M = Better accuracy, more memory
- Lower M = Less memory, faster build
- Range: 4-64 (typically 16-32)

# ef_construction (build quality)
- Higher = Better index quality, slower build
- Range: 64-500 (typically 200)

# ef_search (search quality)
- Higher = Better accuracy, slower search
- Range: 10-500 (typically 100)
```

## Best Practices

1. **Let it Auto-Optimize**: The system automatically optimizes during table creation and periodically based on growth.

2. **Monitor Performance**: Use `get_index_performance_stats()` to track query performance over time.

3. **Benchmark Changes**: Before manual tuning, use `benchmark_vector_search()` to compare strategies.

4. **Consider User Patterns**: Heavy users may need different optimization than many light users.

5. **Balance Trade-offs**: 
   - Accuracy vs Speed
   - Memory usage vs Performance
   - Build time vs Query time

## Example Optimization Flow

```python
# 1. Check current state
stats = await get_memory_table_stats()
print(f"Total rows: {stats['statistics']['row_count']}")
print(f"Unique users: {stats['statistics']['unique_users']}")
print(f"Recommended: {stats['recommended_strategy']['type']}")

# 2. Run optimization if needed
if stats['recommended_strategy']['type'] != current_index_type:
    result = await optimize_vector_index(force=True)
    print(f"Optimization: {result['result']['action']}")

# 3. Benchmark performance
bench = await benchmark_vector_search()
for b in bench['benchmarks']:
    print(f"{b['optimization']}: {b['avg_duration_ms']}ms")

# 4. Fine-tune if needed
if bench['benchmarks'][0]['avg_duration_ms'] > 100:
    # Too slow, reduce accuracy for speed
    await set_vector_search_params(probes=10)
```

## Monitoring and Alerts

The optimizer tracks:
- Index usage statistics
- Query performance metrics
- Table growth patterns
- User distribution changes

Optimization is triggered when:
- Table grows by >50% since last optimization
- Query performance degrades by >30%
- User distribution changes significantly
- Manual force flag is set

## Integration with DB-MCP

The Memory Agent optimizer works alongside DB-MCP's existing IVFFlat implementation:

1. **Complementary**: Memory Agent optimizes specifically for memory storage patterns
2. **Compatible**: Uses standard pgvector indexes that DB-MCP understands
3. **Enhanced**: Adds user-aware and memory-type-aware optimizations
4. **Automatic**: Handles optimization without manual intervention

## Troubleshooting

### Slow Searches
1. Check current optimization: `get_memory_table_stats()`
2. Try accuracy/speed trade-off: Use "speed" mode
3. Reduce result set size: Lower limit parameter
4. Re-optimize: `optimize_vector_index(force=True)`

### High Memory Usage
1. Check index type: HNSW uses more memory
2. Consider IVFFlat for large datasets
3. Monitor with `get_index_performance_stats()`

### Poor Accuracy
1. Increase probes: `set_vector_search_params(probes=50)`
2. Use "accuracy" optimization mode
3. Consider HNSW for critical queries