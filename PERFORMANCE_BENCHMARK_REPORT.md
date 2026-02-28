# ProjectNeoTrace 性能基准报告

**测试时间**: 2026-02-28 22:52:42

## Session 切片

- event_count: 10000
- elapsed_seconds: 0.1003
- throughput_events_per_sec: 99685.3979

## Log-to-Text 转换

- session_count: 1000
- elapsed_seconds: 0.0000
- avg_latency_ms: 0.0000
- throughput_sessions_per_sec: 27764671.1005

## LLM 意图打标

- text_count: 100
- avg_latency_ms: 50.2216
- p50_latency_ms: 50.1949
- p95_latency_ms: 50.4148
- p99_latency_ms: 50.4810

## 向量生成

- sample_count: 1000
- avg_latency_ms: 0.0516
- throughput_vectors_per_sec: 19386.9442

## SupCon 训练

- batch_size: 32
- num_batches: 100
- avg_batch_time_sec: 0.0104
- samples_per_sec: 3088.0308

## Student Model 推理

- sample_count: 10000
- avg_latency_ms: 0.8910
- p50_latency_ms: 0.7169
- p95_latency_ms: 1.6237
- p99_latency_ms: 2.1299
- max_latency_ms: 12.6526

## API 吞吐量

- request_count: 10000
- total_time_sec: 12.4115
- throughput_qps: 805.7070
- avg_latency_ms: 1.2353
- p99_latency_ms: 1.4670

