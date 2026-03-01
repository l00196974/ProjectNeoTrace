# ProjectNeoTrace 安装部署指南

## 目录
- [系统要求](#系统要求)
- [本地开发环境安装](#本地开发环境安装)
- [Docker 部署](#docker-部署)
- [生产环境部署](#生产环境部署)
- [常见问题](#常见问题)

---

## 系统要求

### 硬件要求
- **CPU**: 4 核及以上（推荐 8 核）
- **内存**: 8GB 及以上（推荐 16GB）
- **磁盘**: 20GB 可用空间
- **GPU**: 不需要（CPU 训练和推理）

### 软件要求
- **操作系统**: Linux / macOS / Windows (WSL2)
- **Python**: 3.9 或更高版本
- **Git**: 2.0 或更高版本
- **Docker**: 20.10 或更高版本（可选）

---

## 本地开发环境安装

### 步骤 1: 克隆仓库

```bash
git clone https://github.com/l00196974/ProjectNeoTrace.git
cd ProjectNeoTrace
```

### 步骤 2: 创建虚拟环境

**Linux/macOS**:
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows**:
```bash
python -m venv venv
venv\Scripts\activate
```

### 步骤 3: 安装依赖

```bash
# 升级 pip
pip install --upgrade pip

# 安装项目依赖
pip install -r requirements.txt
```

**注意**: 如果遇到 PyTorch 安装问题，请访问 [PyTorch 官网](https://pytorch.org/) 选择适合你系统的安装命令。

### 步骤 4: 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件
nano .env  # 或使用你喜欢的编辑器
```

**必填配置**:
```bash
# LLM API 配置（至少配置一个）
OPENAI_API_KEY=sk-your-openai-api-key-here
# 或
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# 选择 LLM 提供商
LLM_PROVIDER=openai  # 或 anthropic
```

**可选配置**:
```bash
# 模型配置
LLM_MODEL=gpt-3.5-turbo
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=500

# 训练配置
STUDENT_MODEL_EPOCHS=30
SUPCON_EPOCHS=30
```

### 步骤 5: 验证安装

```bash
# 运行测试
python -m pytest tests/ -v

# 生成模拟数据
python scripts/generate_mock_data.py

# 检查数据是否生成成功
ls -lh data/raw/events.json
```

### 步骤 6: 运行完整训练流程

```bash
# 运行离线训练流程（约 2-3 小时）
python scripts/offline_training_pipeline.py
```

**预期输出**:
```
[Step 1/5] Session 切片...
  ✓ 切片完成，共 1000 个 Session

[Step 2/5] LLM 批量标注（Teacher Model）...
  进度: 100/1000
  ✓ 标注完成，共 1000 个样本

[Step 3/5] 训练 Student Model（CPU）...
  Epoch 30/30, Loss: 0.0234
  ✓ Student Model 训练完成

[Step 4/5] 生成融合向量...
  ✓ 融合向量生成完成，共 1000 个样本

[Step 5/5] 训练 SupCon 模型（CPU）...
  Epoch 30/30, Avg Loss: 0.1234
  ✓ SupCon 模型训练完成

训练流程完成！
```

### 步骤 7: 启动推理服务

```bash
# 启动 Flask API
python src/serving/api.py
```

**预期输出**:
```
 * Running on http://0.0.0.0:5000
 * Press CTRL+C to quit
```

### 步骤 8: 测试 API

**使用 curl**:
```bash
curl -X POST http://localhost:5000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "session_text": "用户在汽车之家浏览了 5 款 SUV，停留 10 分钟",
    "session_features": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
  }'
```

**预期响应**:
```json
{
  "device_id": "test_device",
  "lead_score": 0.75,
  "timestamp": 1709136000
}
```

**使用 Python**:
```python
import requests

response = requests.post(
    'http://localhost:5000/predict',
    json={
        'session_text': '用户在汽车之家浏览了 5 款 SUV',
        'session_features': [0.1] * 8
    }
)

print(response.json())
```

---

## Docker 部署

### 步骤 1: 构建 Docker 镜像

```bash
# 构建镜像
docker-compose build

# 查看镜像
docker images | grep neotrace
```

### 步骤 2: 配置环境变量

```bash
# 确保 .env 文件已配置
cat .env
```

### 步骤 3: 启动推理服务

```bash
# 启动 API 服务
docker-compose up -d neotrace-api

# 查看日志
docker-compose logs -f neotrace-api

# 检查服务状态
docker-compose ps
```

### 步骤 4: 运行训练流程（可选）

```bash
# 运行训练
docker-compose --profile training up neotrace-training

# 查看训练日志
docker-compose logs -f neotrace-training
```

### 步骤 5: 测试 Docker 部署

```bash
curl -X POST http://localhost:5000/predict \
  -H "Content-Type: application/json" \
  -d '{"session_text": "测试", "session_features": [0.1, 0.2, 0.3]}'
```

### 步骤 6: 停止服务

```bash
# 停止服务
docker-compose down

# 停止并删除数据卷
docker-compose down -v
```

---

## 生产环境部署

### 方案 1: 云服务器部署（推荐）

#### 1.1 准备云服务器

**推荐配置**:
- **云平台**: AWS / 阿里云 / 腾讯云
- **实例类型**: 4 核 8GB（如 AWS t3.xlarge）
- **操作系统**: Ubuntu 20.04 LTS
- **存储**: 50GB SSD

#### 1.2 安装 Docker 和 Docker Compose

```bash
# 更新系统
sudo apt-get update
sudo apt-get upgrade -y

# 安装 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 验证安装
docker --version
docker-compose --version
```

#### 1.3 部署应用

```bash
# 克隆仓库
git clone https://github.com/l00196974/ProjectNeoTrace.git
cd ProjectNeoTrace

# 配置环境变量
cp .env.example .env
nano .env  # 填入生产环境配置

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

#### 1.4 配置反向代理（Nginx）

```bash
# 安装 Nginx
sudo apt-get install nginx -y

# 创建配置文件
sudo nano /etc/nginx/sites-available/neotrace
```

**Nginx 配置**:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# 启用配置
sudo ln -s /etc/nginx/sites-available/neotrace /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### 1.5 配置 HTTPS（Let's Encrypt）

```bash
# 安装 Certbot
sudo apt-get install certbot python3-certbot-nginx -y

# 获取 SSL 证书
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo certbot renew --dry-run
```

### 方案 2: Kubernetes 部署

#### 2.1 创建 Kubernetes 配置

**deployment.yaml**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: neotrace-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: neotrace-api
  template:
    metadata:
      labels:
        app: neotrace-api
    spec:
      containers:
      - name: neotrace-api
        image: your-registry/neotrace:latest
        ports:
        - containerPort: 5000
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: neotrace-secrets
              key: openai-api-key
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
---
apiVersion: v1
kind: Service
metadata:
  name: neotrace-api-service
spec:
  selector:
    app: neotrace-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 5000
  type: LoadBalancer
```

#### 2.2 部署到 Kubernetes

```bash
# 创建 Secret
kubectl create secret generic neotrace-secrets \
  --from-literal=openai-api-key=your-api-key

# 部署应用
kubectl apply -f deployment.yaml

# 查看状态
kubectl get pods
kubectl get services
```

---

## 常见问题

### Q1: PyTorch 安装失败

**问题**: `ERROR: Could not find a version that satisfies the requirement torch==2.0.0+cpu`

**解决方案**:
```bash
# 使用正确的 PyTorch 索引
pip install torch==2.0.0 --index-url https://download.pytorch.org/whl/cpu
```

### Q2: LLM API 调用失败

**问题**: `LLM 调用失败: Connection timeout`

**解决方案**:
1. 检查 API Key 是否正确
2. 检查网络连接
3. 使用 Mock LLM 进行测试:
```bash
# 在 .env 中设置
LLM_PROVIDER=mock
```

### Q3: 内存不足

**问题**: `MemoryError: Unable to allocate array`

**解决方案**:
1. 减小 batch size:
```bash
# 在 .env 中设置
STUDENT_MODEL_BATCH_SIZE=16
SUPCON_BATCH_SIZE=8
```

2. 减少训练数据量:
```python
# 在 generate_mock_data.py 中修改
NUM_DEVICES = 100  # 从 1000 减少到 100
```

### Q4: Docker 容器无法启动

**问题**: `Error: Cannot start service neotrace-api`

**解决方案**:
```bash
# 查看详细日志
docker-compose logs neotrace-api

# 检查端口占用
sudo lsof -i :5000

# 重新构建镜像
docker-compose build --no-cache
docker-compose up -d
```

### Q5: API 响应慢

**问题**: API P99 延迟 > 100ms

**解决方案**:
1. 检查模型是否正确加载
2. 使用模型量化:
```python
# 在 inference.py 中添加
import torch.quantization as quantization
model = quantization.quantize_dynamic(model, {nn.Linear}, dtype=torch.qint8)
```

3. 启用批量推理

### Q6: 训练过程中断

**问题**: 训练到一半进程被杀死

**解决方案**:
1. 检查系统内存
2. 使用 checkpoint 机制:
```python
# 在训练脚本中添加
if epoch % 5 == 0:
    torch.save(model.state_dict(), f'checkpoint_epoch_{epoch}.pth')
```

### Q7: 无法连接到 GitHub

**问题**: `fatal: unable to access 'https://github.com/...'`

**解决方案**:
```bash
# 使用 SSH 替代 HTTPS
git remote set-url origin git@github.com:l00196974/ProjectNeoTrace.git

# 或配置全局规则
git config --global url."git@github.com:".insteadOf "https://github.com/"
```

---

## 性能优化建议

### 1. 模型量化

```python
import torch.quantization as quantization

# 动态量化（推理速度提升 2-3x）
quantized_model = quantization.quantize_dynamic(
    model,
    {nn.Linear},
    dtype=torch.qint8
)
```

### 2. 批量推理

```python
# 批量处理请求
batch_size = 32
for i in range(0, len(requests), batch_size):
    batch = requests[i:i+batch_size]
    results = model(batch)
```

### 3. 缓存优化

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_text_embedding(text):
    return text_encoder.encode(text)
```

---

## 监控和日志

### 查看日志

```bash
# 本地部署
tail -f logs/app.log

# Docker 部署
docker-compose logs -f neotrace-api

# Kubernetes 部署
kubectl logs -f deployment/neotrace-api
```

### 性能监控

```bash
# 查看 API 性能
curl http://localhost:5000/health

# 查看系统资源
htop
```

---

## 下一步

- [API 文档](docs/api_spec.md)
- [架构设计](docs/architecture.md)
- [开发指南](CLAUDE.md)
- [性能优化](PERFORMANCE_BENCHMARK_REPORT.md)

---

## 技术支持

如有问题，请：
1. 查看 [常见问题](#常见问题)
2. 提交 [GitHub Issue](https://github.com/l00196974/ProjectNeoTrace/issues)
3. 联系项目团队

---

**最后更新**: 2026-03-01
