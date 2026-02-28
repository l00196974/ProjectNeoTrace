# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ProjectNeoTrace - 
实现基于 OS 级浅层数据（App 序列、LBS、传感器）识别“汽车线索留资（Lead Generation）”高意向用户的闭环系统。利用 Log-to-Text 降维和 Supervised Contrastive Learning (SupCon) 解决数据重叠与标签缺失问题。

## Development Commands

### Building
```bash
# Add build command here
```

### Testing
```bash
# Run all tests
[command]

# Run a single test file
[command]

# Run tests in watch mode
[command]
```

### Linting
```bash
# Run linter
[command]

# Auto-fix linting issues
[command]
```

### Running the Application
```bash
# Development mode
[command]

# Production mode
[command]
```

## Architecture

### High-Level Structure
1 基于设备厂商数据优势，根据用户的全量行为序列进行清洗完成session切片，
2 再对个用户各session进行log-to-text语义化，和意图打标，再生成向量
3 构建正负样本数据标签，可以按照车型价格区间分布打样本标签
4 训练损失函数重新优化向量，让接近正样本的用户向正样本向量聚积，其他向负样本聚积，

需要注意的是这个系统全过程要满足可追溯，即记录用户的原始行为序列和session切片的映射关系，还有session切片和 语义化后内容，意图标签，以及用户的原始行为向量，和其样本标签，

### Key Components
* 模块 A：数据采集与切片引擎 (Data Ingestion & Slicing)  

基于用用户原始行为序列和行为事件完成session切片，安装位置，时间，应用等上下文，将用户的原始序列切割成一段段的session切片
技术栈： Flink (Java) 。Spark(Java)(用来做上线前的方案验证，先用历史数据进行原型验证，实际生产数据用flink实现实时切片分割)

任务：
1.  实现基于 did 的状态机，识别 Sub-session 边界。
2.  切断规则： 息屏 > 10min、LBS 地标跨越、应用一级类目（如从“社交”切到“汽车资讯”）跳变。
3.  特征聚合： 统计单 Session 内 App 切换频率、特定页面（配置页、金融页）停留时长、时间张力（对数分桶处理）。



* 模块 B：语义特征工厂 (Feature Factory & Agent)

将一个个session切片 完成log-to-Text转化，提取语义特征

技术栈： PySpark。
任务：
 1.  Log-to-Text 转换器： 编写映射逻辑。将 pkg_name 等内部标识，通过广告本体知识库映射到语义表达（例：com.autohome 长时间使用 -> 汽车垂直门户-深度对比）。


 2.  LLM 意图打标： 封装调用接口，Prompt 需强制输出包含 urgency_score 和 stage (如 Pre_Lead_Action) 的结构化 JSON。
 3.  双路向量融合：
   * 路径 1：原始 Text -> BGE-m3 Embedding ($V_{text}$)。
   * 路径 2：LLM Intent JSON -> Embedding ($V_{intent}$)。* 操作：Output = Concat(V_text, V_intent)。


模块 C：弱监督标签挖掘 (Proxy Label Miner)
技术栈： SQL / Spark。

任务： 
1.  Label 3 (正样本) 逻辑： 全渠道线索留资数据
2.  Label 1/2 (负样本/中性) 逻辑： 资讯活跃但非点击，留资用户 


模块 D：对比学习训练算子 (Contrastive Learning Core)
技术栈： PyTorch。

任务： 
1.  实现 SupConLoss 类（参考下方算法实现）。
~~~
import torch
import torch.nn as nn
import torch.nn.functional as F

class SupConLoss(nn.Module):
    def __init__(self, temperature=0.07):
        super(SupConLoss, self).__init__()
        self.temperature = temperature

    def forward(self, features, labels):
        # 1. L2 Normalize
        features = F.normalize(features, p=2, dim=1)
        # 2. Compute Similarity Matrix
        logits = torch.div(torch.matmul(features, features.T), self.temperature)
        # 3. Create Label Mask (Find same label pairs)
        labels = labels.view(-1, 1)
        mask = torch.eq(labels, labels.T).float().to(features.device)
        # 4. Remove self-contrast
        logits_mask = torch.ones_like(mask) - torch.eye(features.shape[0]).to(features.device)
        mask = mask * logits_mask
        # 5. Compute Log Probability with Hard Negative Mining
        exp_logits = torch.exp(logits) * logits_mask
        log_prob = logits - torch.log(exp_logits.sum(1, keepdim=True))
        # 6. Mean Log Prob of Positive Pairs
        loss = -(mask * log_prob).sum(1) / mask.sum(1)
        return loss.mean()
~~~
2.  构建 Projection Head：一个简单的 3 层 MLP，将 256 维融合向量映射至 128 维空间。
3.  拉扯逻辑： 强制同 Label 样本（如都是 Label 3）在空间聚类，异类（Label 3 与 Label 1）强行推开。

### Data Flow
实时链路（生产方案）
端侧采用用户行为数据上报-》flink 数据清洗完成session切片-》再通过flink完成log_to_text以及原始向量生成-》原始向量通过新的损失函数进行纠偏，让正负样本分别聚积-》传递用户意图特征向量给推荐引擎

离线链路（生产方案）
现有已经采集的用户历史行为数据-》spark 数据清洗完成session切片-》再通过spark 完成log_to_text以及原始向量生成-》 原始向量通过新的损失函数进行纠偏，让正负样本分别聚积生成纠偏后意图向量 --》引擎模型训练引入该向量，评估向量效果


### Important Patterns
用户原始行为数据，不通的action对应不通的payload属性
{
  "oaid": "string",
  "timestamp": "int64",
  "app_pkg": "string",
  "action": "touch_scroll|app_foreground|.....",
  "payload": {"dwell_time": 450, "lbs_poi": "auto_market"}
}


## Configuration
需要提供三个部署方式 1 local基于本地数据功能验证模式 2 spark模式需要分段实现对应的spark任务（注意和local模式核心代码逻辑一样，只不过运行环境有区分） 3 flink模式生产下实时计算方案（优先级低，可先不实现） 

## Dependencies

[Note any critical dependencies or version requirements]
