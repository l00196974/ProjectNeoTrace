1. 系统目标 (The Mission)
实现一个无需广告主回传、基于 OS 级浅层数据（App 序列、LBS、传感器）识别“汽车线索留资（Lead Generation）”高意向用户的闭环系统。利用 Log-to-Text 降维和 Supervised Contrastive Learning (SupCon) 解决数据重叠与标签缺失问题。

2. 模块拆解与开发任务 (Module Breakdown)
模块 A：数据采集与切片引擎 (Data Ingestion & Slicing)
技术栈： Flink (Java/Python) 或 Go。

任务： 1.  实现基于 device_id 的状态机，识别 Sub-session 边界。
2.  切断规则： 息屏 > 10min、LBS 地标跨越、应用一级类目（如从“社交”切到“汽车资讯”）跳变。
3.  特征聚合： 统计单 Session 内 App 切换频率、特定页面（配置页、金融页）停留时长、时间张力（对数分桶处理）。


模块 B：语义特征工厂 (Feature Factory & Agent)技术栈： Python + LangChain + PySpark。任务： 1.  Log-to-Text 转换器： 编写映射逻辑。将 pkg_name 映射到汽车事理图谱（例：com.autohome -> 汽车垂直门户-深度对比）。2.  LLM 意图打标： 封装调用接口，Prompt 需强制输出包含 urgency_score 和 stage (如 Pre_Lead_Action) 的结构化 JSON。3.  双路向量融合： * 路径 1：原始 Text -> BGE-m3 Embedding ($V_{text}$)。* 路径 2：LLM Intent JSON -> Embedding ($V_{intent}$)。* 操作：Output = Concat(V_text, V_intent)。


模块 C：弱监督标签挖掘 (Proxy Label Miner)
技术栈： SQL / Spark。

任务： 1.  Label 3 (正样本) 逻辑： 窗口期内检测到关键词为“验证码/预约/试驾”的系统短消息，或与 4S 店黄页号码有通话记录。
2.  Label 1/2 (负样本/中性) 逻辑： 资讯活跃但无通讯记录，且 LBS 未偏离住宅区。


模块 D：对比学习训练算子 (Contrastive Learning Core)
技术栈： PyTorch。

任务： 1.  实现 SupConLoss 类（参考下方算法实现）。
2.  构建 Projection Head：一个简单的 3 层 MLP，将 256 维融合向量映射至 128 维空间。
3.  拉扯逻辑： 强制同 Label 样本（如都是 Label 3）在空间聚类，异类（Label 3 与 Label 1）强行推开。

3. 核心数据契约 (Data Contracts)
输入：OSEventLog (Protobuf/JSON)
{
  "device_id": "string",
  "timestamp": "int64",
  "app_pkg": "string",
  "action": "touch_scroll|app_foreground",
  "payload": {"dwell_time": 450, "lbs_poi": "auto_market"}
}

训练样本：Training_Triple (Parquet)
{
  "device_id": "string",
  "combined_vector": "float[256]",
  "proxy_label": "int (0:Noise, 1:Fans, 2:Consider, 3:Leads)"
}

4. 核心算法逻辑 (Algorithm Reference)
Claude Code 请严格按此逻辑实现 SupConLoss 以处理向量重叠：
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


5. 开发步骤建议 (Claude Code Execution Plan)
Step 1: 创建 schema/ 目录，定义全链路数据 Protobuf 与 JSON Schema。

Step 2: 开发 ingestion/ 模块，实现行为切片逻辑与时间分桶函数。

Step 3: 开发 agent/ 模块，实现 Log-to-Text 翻译模板与 LLM 打标 Client。

Step 4: 开发 model/ 模块，实现 SupConLoss 与投影网络训练脚本。

Step 5: 开发 serving/ 模块，实现 Redis 高性能加载与 gRPC 查表接口。

注意事项：

严禁上报明文短信/通话内容，必须在特征提取层即刻转化为 Label_ID。

在线查询 P99 必须低于 5ms。

LLM 解析失败必须有 Default_Intent 兜底。
