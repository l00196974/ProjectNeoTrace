# 部署指南

## 概述

本文档提供 ProjectNeoTrace 系统的部署指南，包括本地开发环境、Spark 离线批处理环境和 Flink 实时流处理环境的部署方法。

## 环境要求

### 硬件要求

**最低配置**:
- CPU: 4 核
- 内存: 8GB RAM
- 磁盘: 20GB 可用空间

**推荐配置**:
- CPU: 8 核
- 内存: 16GB RAM
- 磁盘: 50GB 可用空间

### 软件要求

**必需软件**:
- Python 3.9+
- pip 21.0+
- Git

**可选软件** (根据部署模式):
- Docker 20.10+ (容器化部署)
- Apache Spark 3.3+ (离线批处理)
- Apache Flink 1.15+ (实时流处理)
- Java 11+ (Spark/Flink 运行时)

## 部署模式

ProjectNeoTrace 支持三种部署模式：

1. **Local 模式**: 本地开发和功能验证
2. **Spark 模式**: 离线批处理，用于历史数据处理和模型训练
3. **Flink 模式**: 实时流处理，用于生产环境实时推理

---

## 模式 1: Local 本地部署

### 1.1 克隆代码仓库

```bash
git clone https://github.com/your-org/ProjectNeoTrace.git
cd ProjectNeoTrace
```

### 1.2 创建虚拟环境

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Linux/Mac:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```

### 1.3 安装依赖

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 验证安装
python -c "import torch; import flask; print('Dependencies installed successfully')"
```

### 1.4 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件
nano .env
```

**必需的环境变量**:
```bash
# LLM API 配置
OPENAI_API_KEY=your_openai_api_key_here
# 或
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# 推理服务配置
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_DEBUG=False

# 模型路径
STUDENT_MODEL_PATH=data/models/intent_student_model.pth
SUPCON_MODEL_PATH=data/models/supcon_model.pth
```

### 1.5 生成模拟数据

```bash
# 生成模拟数据用于测试
python scripts/generate_mock_data.py

# 验证数据生成
ls -lh data/raw/
```

### 1.6 运行训练流程

```bash
# 运行完整训练流程
python scripts/offline_training_pipeline.py

# 训练完成后，检查模型文件
ls -lh data/models/
```

### 1.7 启动推理服务

```bash
# 启动 Flask API
python src/serving/api.py

# 服务将在 http://localhost:5000 启动
```

### 1.8 测试 API

```bash
# 健康检查
curl http://localhost:5000/health

# 单次预测
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

---

## 模式 2: Spark 离线批处理部署

### 2.1 安装 Spark

```bash
# 下载 Spark
wget https://archive.apache.org/dist/spark/spark-3.3.2/spark-3.3.2-bin-hadoop3.tgz

# 解压
tar -xzf spark-3.3.2-bin-hadoop3.tgz
mv spark-3.3.2-bin-hadoop3 /opt/spark

# 配置环境变量
echo 'export SPARK_HOME=/opt/spark' >> ~/.bashrc
echo 'export PATH=$PATH:$SPARK_HOME/bin' >> ~/.bashrc
source ~/.bashrc

# 验证安装
spark-submit --version
```

### 2.2 配置 Spark

创建 Spark 配置文件 `conf/spark-defaults.conf`:

```properties
spark.master                     local[*]
spark.driver.memory              4g
spark.executor.memory            4g
spark.executor.cores             2
spark.sql.shuffle.partitions     200
spark.default.parallelism        8
```

### 2.3 准备历史数据

```bash
# 将历史数据放入 HDFS 或本地文件系统
# 假设数据在 data/raw/historical_events.json

# 验证数据格式
head -n 5 data/raw/historical_events.json
```

### 2.4 运行 Spark 任务

```bash
# Session 切片任务
spark-submit \
  --master local[*] \
  --driver-memory 4g \
  --executor-memory 4g \
  scripts/spark/session_slicing.py \
  --input data/raw/historical_events.json \
  --output data/processed/sessions/

# Log-to-Text 转换任务
spark-submit \
  --master local[*] \
  --driver-memory 4g \
  --executor-memory 4g \
  scripts/spark/log_to_text.py \
  --input data/processed/sessions/ \
  --output data/processed/session_texts/

# 向量生成任务
spark-submit \
  --master local[*] \
  --driver-memory 4g \
  --executor-memory 4g \
  scripts/spark/vector_generation.py \
  --input data/processed/session_texts/ \
  --output data/processed/vectors/
```

### 2.5 模型训练

```bash
# 使用 Spark 生成的向量进行模型训练
python scripts/offline_training_pipeline.py \
  --input data/processed/vectors/ \
  --output data/models/
```

---

## 模式 3: Flink 实时流处理部署

### 3.1 安装 Flink

```bash
# 下载 Flink
wget https://archive.apache.org/dist/flink/flink-1.15.4/flink-1.15.4-bin-scala_2.12.tgz

# 解压
tar -xzf flink-1.15.4-bin-scala_2.12.tgz
mv flink-1.15.4 /opt/flink

# 配置环境变量
echo 'export FLINK_HOME=/opt/flink' >> ~/.bashrc
echo 'export PATH=$PATH:$FLINK_HOME/bin' >> ~/.bashrc
source ~/.bashrc

# 验证安装
flink --version
```

### 3.2 配置 Flink

编辑 `$FLINK_HOME/conf/flink-conf.yaml`:

```yaml
jobmanager.memory.process.size: 2048m
taskmanager.memory.process.size: 4096m
taskmanager.numberOfTaskSlots: 4
parallelism.default: 4
```

### 3.3 启动 Flink 集群

```bash
# 启动 Flink 集群
$FLINK_HOME/bin/start-cluster.sh

# 验证集群状态
curl http://localhost:8081

# 查看 Flink Web UI
# 访问 http://localhost:8081
```

### 3.4 部署 Flink 任务

```bash
# 编译 Flink 任务 (Java)
cd flink-jobs/
mvn clean package

# 提交 Session 切片任务
flink run \
  -c com.neotrace.SessionSlicingJob \
  target/neotrace-flink-jobs-1.0.jar \
  --kafka.bootstrap.servers localhost:9092 \
  --kafka.input.topic raw-events \
  --kafka.output.topic sessions

# 提交 Log-to-Text 转换任务
flink run \
  -c com.neotrace.LogToTextJob \
  target/neotrace-flink-jobs-1.0.jar \
  --kafka.bootstrap.servers localhost:9092 \
  --kafka.input.topic sessions \
  --kafka.output.topic session-texts

# 提交向量生成任务
flink run \
  -c com.neotrace.VectorGenerationJob \
  target/neotrace-flink-jobs-1.0.jar \
  --kafka.bootstrap.servers localhost:9092 \
  --kafka.input.topic session-texts \
  --kafka.output.topic vectors
```

### 3.5 配置 Kafka

```bash
# 启动 Kafka (假设已安装)
kafka-server-start.sh config/server.properties

# 创建 Kafka Topics
kafka-topics.sh --create \
  --bootstrap-server localhost:9092 \
  --topic raw-events \
  --partitions 4 \
  --replication-factor 1

kafka-topics.sh --create \
  --bootstrap-server localhost:9092 \
  --topic sessions \
  --partitions 4 \
  --replication-factor 1

kafka-topics.sh --create \
  --bootstrap-server localhost:9092 \
  --topic session-texts \
  --partitions 4 \
  --replication-factor 1

kafka-topics.sh --create \
  --bootstrap-server localhost:9092 \
  --topic vectors \
  --partitions 4 \
  --replication-factor 1
```

---

## Docker 容器化部署

### 4.1 构建 Docker 镜像

```bash
# 构建推理服务镜像
docker build -t neotrace-api:latest -f docker/Dockerfile.api .

# 构建训练服务镜像
docker build -t neotrace-training:latest -f docker/Dockerfile.training .
```

### 4.2 使用 Docker Compose

```bash
# 启动推理服务
docker-compose up neotrace-api

# 启动训练流程
docker-compose --profile training up neotrace-training

# 停止服务
docker-compose down
```

**docker-compose.yml 示例**:
```yaml
version: '3.8'

services:
  neotrace-api:
    image: neotrace-api:latest
    ports:
      - "5000:5000"
    environment:
      - FLASK_HOST=0.0.0.0
      - FLASK_PORT=5000
      - FLASK_DEBUG=false
    volumes:
      - ./data/models:/app/data/models
    restart: unless-stopped

  neotrace-training:
    image: neotrace-training:latest
    profiles:
      - training
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./data:/app/data
```

---

## 监控和日志

### 5.1 日志配置

**日志目录结构**:
```
logs/
├── api.log              # API 请求日志
├── inference.log        # 推理日志
├── training.log         # 训练日志
└── error.log            # 错误日志
```

**配置日志级别**:
```bash
# 在 .env 文件中配置
LOG_LEVEL=INFO
LOG_FILE=logs/api.log
```

### 5.2 监控指标

**推荐监控指标**:
- API 请求量和延迟 (P50, P95, P99)
- 模型推理时间
- 错误率和异常
- CPU 和内存使用率
- 磁盘 I/O

**使用 Prometheus + Grafana**:
```bash
# 启动 Prometheus
docker run -d -p 9090:9090 \
  -v $(pwd)/prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus

# 启动 Grafana
docker run -d -p 3000:3000 grafana/grafana
```

---

## 故障排查

### 6.1 常见问题

**问题 1: 模型加载失败**
```
错误: FileNotFoundError: [Errno 2] No such file or directory: 'data/models/intent_student_model.pth'
```
**解决方案**:
```bash
# 检查模型文件是否存在
ls -lh data/models/

# 如果不存在，运行训练流程
python scripts/offline_training_pipeline.py
```

**问题 2: API 启动失败**
```
错误: Address already in use
```
**解决方案**:
```bash
# 查找占用端口的进程
lsof -i :5000

# 杀死进程
kill -9 <PID>

# 或更改端口
export FLASK_PORT=5001
python src/serving/api.py
```

**问题 3: 内存不足**
```
错误: RuntimeError: [enforce fail at alloc_cpu.cpp:114] . DefaultCPUAllocator: can't allocate memory
```
**解决方案**:
```bash
# 减少批处理大小
# 在 config.py 中修改
BATCH_SIZE = 16  # 从 32 减少到 16

# 或增加系统内存
```

### 6.2 日志查看

```bash
# 查看 API 日志
tail -f logs/api.log

# 查看错误日志
tail -f logs/error.log

# 搜索特定错误
grep "ERROR" logs/api.log
```

---

## 性能优化

### 7.1 CPU 优化

```bash
# 设置 PyTorch 线程数
export OMP_NUM_THREADS=4
export MKL_NUM_THREADS=4

# 启动服务
python src/serving/api.py
```

### 7.2 批处理优化

```python
# 在 src/serving/api.py 中配置
BATCH_SIZE = 32  # 根据内存调整
MAX_BATCH_WAIT_TIME = 100  # 毫秒
```

### 7.3 模型优化

```bash
# 使用量化模型 (可选)
python scripts/quantize_model.py \
  --input data/models/supcon_model.pth \
  --output data/models/supcon_model_quantized.pth
```

---

## 安全配置

### 8.1 API 认证

```python
# 在 src/serving/api.py 中添加认证
from flask import request

@app.before_request
def authenticate():
    api_key = request.headers.get('X-API-Key')
    if api_key != os.getenv('API_KEY'):
        return jsonify({"error": "Unauthorized"}), 401
```

### 8.2 HTTPS 配置

```bash
# 生成自签名证书 (开发环境)
openssl req -x509 -newkey rsa:4096 -nodes \
  -out cert.pem -keyout key.pem -days 365

# 启动 HTTPS 服务
python src/serving/api.py --cert cert.pem --key key.pem
```

### 8.3 防火墙配置

```bash
# 仅允许特定 IP 访问
sudo ufw allow from 192.168.1.0/24 to any port 5000

# 启用防火墙
sudo ufw enable
```

---

## 备份和恢复

### 9.1 数据备份

```bash
# 备份模型文件
tar -czf models_backup_$(date +%Y%m%d).tar.gz data/models/

# 备份数据文件
tar -czf data_backup_$(date +%Y%m%d).tar.gz data/processed/
```

### 9.2 数据恢复

```bash
# 恢复模型文件
tar -xzf models_backup_20260301.tar.gz -C data/

# 恢复数据文件
tar -xzf data_backup_20260301.tar.gz -C data/
```

---

## 升级和维护

### 10.1 版本升级

```bash
# 拉取最新代码
git pull origin main

# 更新依赖
pip install -r requirements.txt --upgrade

# 重新训练模型 (如果需要)
python scripts/offline_training_pipeline.py

# 重启服务
pkill -f "python src/serving/api.py"
python src/serving/api.py
```

### 10.2 定期维护

```bash
# 清理旧日志 (保留最近 7 天)
find logs/ -name "*.log" -mtime +7 -delete

# 清理临时文件
rm -rf data/tmp/*

# 检查磁盘空间
df -h
```

---

## 联系支持

如遇到部署问题，请联系：
- Email: support@neotrace.com
- GitHub Issues: https://github.com/your-org/ProjectNeoTrace/issues
