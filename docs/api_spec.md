# API 规范文档

## 概述

ProjectNeoTrace 提供 RESTful API 接口，用于在线推理汽车留资意向识别。所有接口均返回 JSON 格式数据。

## 基础信息

- **Base URL**: `http://localhost:5000`
- **Content-Type**: `application/json`
- **超时时间**: 30 秒

## 接口列表

### 1. 健康检查

检查服务是否正常运行。

**端点**: `GET /health`

**请求示例**:
```bash
curl http://localhost:5000/health
```

**响应格式**:
```json
{
  "status": "ok",
  "timestamp": 1709251200
}
```

**响应字段**:
- `status` (string): 服务状态，"ok" 表示正常
- `timestamp` (int): Unix 时间戳

**状态码**:
- `200`: 服务正常

---

### 2. 单次预测

对单个 Session 进行意图识别和留资评分。

**端点**: `POST /predict`

**请求格式**:
```json
{
  "session": {
    "device_id": "device_000001",
    "app_switch_freq": 5,
    "config_page_dwell": 180,
    "finance_page_dwell": 60,
    "time_tension_bucket": 2,
    "session_duration": 300,
    "event_count": 20,
    "lbs_poi_list": ["home", "auto_market"],
    "app_pkg_list": ["com.autohome", "com.yiche"]
  }
}
```

**请求字段说明**:
- `session` (object): Session 数据对象
  - `device_id` (string): 设备唯一标识
  - `app_switch_freq` (int): 应用切换频率
  - `config_page_dwell` (int): 配置页停留时长（秒）
  - `finance_page_dwell` (int): 金融页停留时长（秒）
  - `time_tension_bucket` (int): 时间张力分桶（0-5）
  - `session_duration` (int): Session 总时长（秒）
  - `event_count` (int): 事件总数
  - `lbs_poi_list` (array): 地标列表
  - `app_pkg_list` (array): 应用包名列表

**请求示例**:
```bash
curl -X POST http://localhost:5000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "session": {
      "device_id": "device_000001",
      "app_switch_freq": 5,
      "config_page_dwell": 180,
      "finance_page_dwell": 60,
      "time_tension_bucket": 2,
      "session_duration": 300,
      "event_count": 20,
      "lbs_poi_list": ["home", "auto_market"],
      "app_pkg_list": ["com.autohome", "com.yiche"]
    }
  }'
```

**响应格式**:
```json
{
  "device_id": "device_000001",
  "lead_score": 0.75,
  "intent_probs": [0.05, 0.12, 0.68, 0.03, 0.02, 0.01, 0.04, 0.02, 0.01, 0.01, 0.01],
  "timestamp": 1709251200
}
```

**响应字段说明**:
- `device_id` (string): 设备唯一标识
- `lead_score` (float): 留资意向评分，范围 [0, 1]，越高表示意向越强
- `intent_probs` (array): 11 个意图类别的概率分布
  - 索引 0: 购车意图
  - 索引 1: 金融意图
  - 索引 2: 外卖意图
  - 索引 3: 出行意图
  - 索引 4: 娱乐意图
  - 索引 5: 社交意图
  - 索引 6: 购物意图
  - 索引 7: 新闻意图
  - 索引 8: 工具意图
  - 索引 9: 教育意图
  - 索引 10: 其他意图
- `timestamp` (int): 预测时间戳

**状态码**:
- `200`: 预测成功
- `400`: 请求参数错误
- `500`: 服务器内部错误

---

### 3. 批量预测

对多个 Session 进行批量意图识别和留资评分。

**端点**: `POST /batch_predict`

**请求格式**:
```json
{
  "sessions": [
    {
      "device_id": "device_000001",
      "app_switch_freq": 5,
      "config_page_dwell": 180,
      "finance_page_dwell": 60,
      "time_tension_bucket": 2,
      "session_duration": 300,
      "event_count": 20,
      "lbs_poi_list": ["home", "auto_market"],
      "app_pkg_list": ["com.autohome", "com.yiche"]
    },
    {
      "device_id": "device_000002",
      "app_switch_freq": 3,
      "config_page_dwell": 120,
      "finance_page_dwell": 30,
      "time_tension_bucket": 1,
      "session_duration": 200,
      "event_count": 15,
      "lbs_poi_list": ["home"],
      "app_pkg_list": ["com.autohome"]
    }
  ]
}
```

**请求字段说明**:
- `sessions` (array): Session 数据对象数组，每个对象格式同 `/predict` 接口

**请求示例**:
```bash
curl -X POST http://localhost:5000/batch_predict \
  -H "Content-Type: application/json" \
  -d '{
    "sessions": [
      {
        "device_id": "device_000001",
        "app_switch_freq": 5,
        "config_page_dwell": 180,
        "finance_page_dwell": 60,
        "time_tension_bucket": 2,
        "session_duration": 300,
        "event_count": 20,
        "lbs_poi_list": ["home", "auto_market"],
        "app_pkg_list": ["com.autohome", "com.yiche"]
      }
    ]
  }'
```

**响应格式**:
```json
{
  "results": [
    {
      "device_id": "device_000001",
      "lead_score": 0.75,
      "intent_probs": [0.05, 0.12, 0.68, 0.03, 0.02, 0.01, 0.04, 0.02, 0.01, 0.01, 0.01]
    },
    {
      "device_id": "device_000002",
      "lead_score": 0.62,
      "intent_probs": [0.08, 0.15, 0.55, 0.04, 0.03, 0.02, 0.05, 0.03, 0.02, 0.02, 0.01]
    }
  ],
  "timestamp": 1709251200
}
```

**响应字段说明**:
- `results` (array): 预测结果数组，每个对象格式同 `/predict` 接口响应
- `timestamp` (int): 批量预测完成时间戳

**状态码**:
- `200`: 预测成功
- `400`: 请求参数错误
- `500`: 服务器内部错误

---

## 错误响应格式

所有错误响应均遵循以下格式：

```json
{
  "error": "错误描述信息"
}
```

**常见错误码**:
- `400 Bad Request`: 请求参数缺失或格式错误
- `500 Internal Server Error`: 服务器内部错误（模型加载失败、推理异常等）

**错误示例**:
```json
{
  "error": "Missing session data"
}
```

---

## 使用示例

### Python 客户端

```python
import requests
import json

# 服务地址
API_URL = "http://localhost:5000"

# 单次预测
def predict_single(session_data):
    response = requests.post(
        f"{API_URL}/predict",
        json={"session": session_data},
        headers={"Content-Type": "application/json"}
    )
    return response.json()

# 批量预测
def predict_batch(sessions_data):
    response = requests.post(
        f"{API_URL}/batch_predict",
        json={"sessions": sessions_data},
        headers={"Content-Type": "application/json"}
    )
    return response.json()

# 示例使用
session = {
    "device_id": "device_000001",
    "app_switch_freq": 5,
    "config_page_dwell": 180,
    "finance_page_dwell": 60,
    "time_tension_bucket": 2,
    "session_duration": 300,
    "event_count": 20,
    "lbs_poi_list": ["home", "auto_market"],
    "app_pkg_list": ["com.autohome", "com.yiche"]
}

result = predict_single(session)
print(f"Lead Score: {result['lead_score']:.2f}")
```

### JavaScript 客户端

```javascript
const API_URL = "http://localhost:5000";

// 单次预测
async function predictSingle(sessionData) {
  const response = await fetch(`${API_URL}/predict`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ session: sessionData }),
  });
  return await response.json();
}

// 批量预测
async function predictBatch(sessionsData) {
  const response = await fetch(`${API_URL}/batch_predict`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ sessions: sessionsData }),
  });
  return await response.json();
}

// 示例使用
const session = {
  device_id: "device_000001",
  app_switch_freq: 5,
  config_page_dwell: 180,
  finance_page_dwell: 60,
  time_tension_bucket: 2,
  session_duration: 300,
  event_count: 20,
  lbs_poi_list: ["home", "auto_market"],
  app_pkg_list: ["com.autohome", "com.yiche"],
};

predictSingle(session).then((result) => {
  console.log(`Lead Score: ${result.lead_score.toFixed(2)}`);
});
```

---

## 性能指标

- **单次预测延迟**: P50 < 5ms, P99 < 10ms
- **批量预测吞吐**: 100 sessions/秒
- **并发支持**: 最多 10 个并发请求

---

## 注意事项

1. **特征维度**: Session 特征会被自动填充到 256 维，前 6 维为实际特征，后 250 维填充 0
2. **文本生成**: 系统会自动将 Session 数据转换为语义化文本描述
3. **模型加载**: 首次请求会触发模型加载，可能需要 1-2 秒
4. **超时处理**: 如果推理超过 30 秒，请求会超时返回 500 错误
5. **数据隐私**: 所有请求数据仅用于推理，不会被持久化存储
