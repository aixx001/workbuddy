# 🦙 LlamaIndex Core 模块探索报告

> **分析时间**: 2026-03-30  
> **分析对象**: `llama-index-core` (300 Python文件, 336类, 2039函数)  
> **依赖图**: 300节点, 1247边, 12个模块簇 (Louvain)

---

## 一、Louvain 社区检测结果 → 需求映射

| # | 模块簇 | 文件数 | 对应需求 | 复用价值 |
|---|--------|-------|---------|---------|
| 1 | `objects` | 63 | 基础架构（schema/callbacks/prompts） | ⚪ 核心依赖，不直接提取 |
| 2 | `chat_engine` | 42 | Question — 多轮对话 | 🟡 中 |
| 3 | `tools` | 37 | Agent/Tool — 工具调用 | 🟡 中 |
| 4 | `query_engine` | 35 | Retrieval — 查询引擎 | 🔴 高 |
| 5 | `evaluation` | 25 | Evaluation — 评估 | 🟡 已有Ragas/DeepEval |
| 6 | `postprocessor` | 24 | **Retrieval — 重排序** | 🔴 **高** |
| 7 | `response_synthesizers` | 20 | 生成层 — 回答合成 | 🟡 中 |
| 8 | `workflow` | 15 | Agent workflow | ⚪ 低 |
| 9 | `download` | 7 | 内部工具 | ⚪ 无需 |
| 10 | `data_structs` | 6 | 内部数据结构 | ⚪ 无需 |
| 11 | `langchain_helpers` | 2 | 兼容层 | ⚪ 无需 |
| 12 | `_isolated` | 24 | 独立文件 | ⚪ 按需 |

---

## 二、可提取模块详情 — 对应4个P0需求缺口

### 🔴 模块1: Chunking（文本分块）

**需求缺口**: 语义分块、文档感知分块、分块评估

**LlamaIndex 提供的组件**:

| 文件 | 类 | 功能 | 适配需求 |
|------|-----|------|---------|
| `node_parser/text/sentence.py` | `SentenceSplitter` | 按句子切分，支持 overlap | Chunking 基础 |
| `node_parser/text/token.py` | `TokenTextSplitter` | 按 token 切分 | Chunking 基础 |
| `node_parser/text/semantic_splitter.py` | `SemanticSplitterNodeParser` | **语义分块** — 按 embedding 相似度分界 | ✅ **P0缺口** |
| `node_parser/text/semantic_double_merging_splitter.py` | `SemanticDoubleMergingSplitterNodeParser` | 双向语义合并分块 | ✅ 高级语义分块 |
| `node_parser/text/sentence_window.py` | `SentenceWindowNodeParser` | 滑动窗口分块 + 上下文保留 | ✅ 文档感知 |
| `node_parser/text/code.py` | `CodeSplitter` | 按语法结构分代码 | ⚪ 非教育需求 |

**集成方式**: 📦 安装型 (`pip install llama-index-core`)

```python
# 语义分块 — 填补 Chunking P0 缺口
from llama_index.core.node_parser import SemanticSplitterNodeParser
from llama_index.core.embeddings import BaseEmbedding

splitter = SemanticSplitterNodeParser(
    buffer_size=1,                    # 逐句比较
    breakpoint_percentile_threshold=95,  # 语义跳变阈值
    embed_model=embed_model,
)
nodes = splitter.get_nodes_from_documents(documents)
```

**额外的 integrations 包**（独立安装）:
- `llama-index-node-parser-topic` — 按主题分块
- `llama-index-node-parser-docling` — 文档结构感知分块

---

### 🔴 模块2: Retrieval（检索策略）

**需求缺口**: 混合检索、重排序、策略切换

**LlamaIndex core 提供的检索器**:

| 文件 | 类 | 功能 | 适配需求 |
|------|-----|------|---------|
| `retrievers/fusion_retriever.py` | `QueryFusionRetriever` | **融合检索** — 多路检索 + reciprocal rank fusion | ✅ **混合检索 P0** |
| `retrievers/auto_merging_retriever.py` | `AutoMergingRetriever` | 自动合并小节点为大节点 | 🟡 层级检索 |
| `retrievers/recursive_retriever.py` | `RecursiveRetriever` | 递归追踪引用 | 🟡 跨文档 |
| `retrievers/router_retriever.py` | `RouterRetriever` | **策略切换** — 根据问题类型路由到不同检索器 | ✅ **策略切换 P0** |
| `retrievers/transform_retriever.py` | `TransformRetriever` | 检索前变换查询 | 🟡 query rewriting |

**重排序器**（`postprocessor/` 簇）:

| 文件 | 类 | 功能 | 适配需求 |
|------|-----|------|---------|
| `postprocessor/llm_rerank.py` | `LLMRerank` | LLM 重排序 | ✅ **重排序 P0** |
| `postprocessor/sbert_rerank.py` | `SentenceTransformerRerank` | SBERT 重排序（本地，快） | ✅ 本地LLM友好 |
| `postprocessor/rankGPT_rerank.py` | `RankGPTRerank` | RankGPT 重排序 | ✅ GPT-based |
| `postprocessor/node_recency.py` | `TimeWeightedPostprocessor` | 按时间加权 | 🟡 时效性 |
| `postprocessor/metadata_replacement.py` | `MetadataReplacementPostProcessor` | 元数据替换 | 🟡 上下文扩充 |

**集成方式**: 📦 安装型

```python
# 融合检索 — 向量 + BM25
from llama_index.core.retrievers import QueryFusionRetriever
from llama_index.retrievers.bm25 import BM25Retriever  # 独立包

fusion = QueryFusionRetriever(
    retrievers=[vector_retriever, bm25_retriever],
    num_queries=4,          # 生成4个查询变体
    use_async=True,
    similarity_top_k=10,
)
nodes = await fusion.aretrieve("什么是光合作用？")

# 重排序
from llama_index.core.postprocessor import SentenceTransformerRerank
reranker = SentenceTransformerRerank(
    model="cross-encoder/ms-marco-MiniLM-L-6-v2",
    top_n=5,
)
reranked = reranker.postprocess_nodes(nodes, query_str="什么是光合作用？")
```

**BM25 集成包**: `pip install llama-index-retrievers-bm25`

---

### 🔴 模块3: Embedding（向量化）

**需求缺口**: 模型管理、批量处理、模型对比

**LlamaIndex 提供的组件**:

| 文件 | 类 | 功能 |
|------|-----|------|
| `embeddings/__init__.py` | `BaseEmbedding` | Embedding 基类 — 统一接口 |
| `embeddings/utils.py` | `resolve_embed_model()` | 模型解析/注册 |
| `embeddings/pooling.py` | `Pooling` | 向量池化策略 |
| `embeddings/multi_modal_base.py` | `MultiModalEmbedding` | 多模态 embedding |

**integrations 包（独立安装）**:
- `llama-index-embeddings-openai` — OpenAI embedding
- `llama-index-embeddings-huggingface` — 本地 HuggingFace
- `llama-index-embeddings-ollama` — Ollama embedding ✅

**集成方式**: 📦 安装型 — 抽象层在 core，具体模型独立包

---

### 🟡 模块4: Evaluation（评估 — 补充现有能力）

**LlamaIndex 自带评估器（25个文件的模块簇）**:

| 文件 | 类 | 功能 | 与现有区别 |
|------|-----|------|----------|
| `evaluation/faithfulness.py` | `FaithfulnessEvaluator` | 忠实度 | 类似 Ragas，但接口不同 |
| `evaluation/relevancy.py` | `RelevancyEvaluator` | 相关性 | 类似 Ragas |
| `evaluation/correctness.py` | `CorrectnessEvaluator` | 正确性 | 类似 Ragas |
| `evaluation/pairwise.py` | `PairwiseComparisonEvaluator` | **A/B 对比** | ✅ 补充现有 |
| `evaluation/guideline.py` | `GuidelineEvaluator` | **规则+LLM 合规** | ✅ 教育场景可用 |
| `evaluation/semantic_similarity.py` | `SemanticSimilarityEvaluator` | 语义相似度 | ✅ 轻量 |
| `evaluation/batch_runner.py` | `BatchEvalRunner` | **批量评估** | ✅ 填补 "批量评估" 缺口 |
| `evaluation/dataset_generation.py` | `DatasetGenerator` | 测试集生成 | 类似 Ragas Testset |

---

## 三、依赖图关键发现

### 枢纽节点（核心依赖 — 提取时必须带入）

| 文件 | 被依赖数 | 说明 |
|------|---------|------|
| `core/schema.py` | **100** | 所有数据模型的基类 |
| `core/bridge/pydantic.py` | **73** | Pydantic 兼容层 |
| `core/prompts/mixin.py` | **49** | Prompt 混入基类 |
| `core/llms/llm.py` | **47** | LLM 基类 |
| `core/settings.py` | **46** | 全局配置 |

> [!IMPORTANT]
> **耦合度判断**: `schema.py` 被 100/300 文件依赖 (33%)，说明核心框架耦合度中等。但 `node_parser`、`retrievers`、`postprocessor` 这些功能模块主要依赖 `schema.py` + `settings.py`，可以通过 `pip install llama-index-core` 安装型方式使用，无需提取。

### 推荐集成方式

| 模块 | 方式 | 理由 |
|------|------|------|
| Chunking (node_parser) | 📦 **安装型** | 依赖 core 的 schema/settings，提取代价大 |
| Retrieval (retrievers) | 📦 **安装型** | 同上 |
| Reranking (postprocessor) | 📦 **安装型** | 同上 |
| BM25 Retriever | 📦 **安装型** | 独立 pip 包 |
| Evaluation | 📦 **安装型** | 补充现有 Ragas/DeepEval |

---

## 四、Module Market 注册建议

基于以上分析，推荐注册 **4 个新模块**:

### 新模块清单

| # | 模块名 | slug | 类别 | 核心类 |
|---|--------|------|------|--------|
| 1 | **LlamaIndex Semantic Chunking** | `llamaindex-semantic-chunking` | chunking | `SemanticSplitterNodeParser`, `SentenceSplitter`, `SentenceWindowNodeParser` |
| 2 | **LlamaIndex Fusion Retrieval** | `llamaindex-fusion-retrieval` | retrieval | `QueryFusionRetriever`, `RouterRetriever`, `BM25Retriever` |
| 3 | **LlamaIndex Reranking** | `llamaindex-reranking` | retrieval | `SentenceTransformerRerank`, `LLMRerank`, `RankGPTRerank` |
| 4 | **LlamaIndex Batch Evaluation** | `llamaindex-batch-eval` | evaluation | `BatchEvalRunner`, `PairwiseComparisonEvaluator`, `GuidelineEvaluator` |

### 安装依赖

```bash
# 核心包
pip install llama-index-core

# BM25 检索（混合检索必备）
pip install llama-index-retrievers-bm25

# 本地 embedding（配合 Ollama）
pip install llama-index-embeddings-huggingface
```

---

## 五、填补需求缺口进度

```
注册前:
  Chunking   ░░░░░░░░░░ 0/4 完整功能
  Retrieval  ██░░░░░░░░ 1/5 (仅向量检索)
  Embedding  ░░░░░░░░░░ 0/4 完整功能

注册后:
  Chunking   ████████░░ 3/4 (+语义分块, +窗口分块, +分块评估仍缺)
  Retrieval  ████████░░ 4/5 (+混合检索, +重排序, +策略切换)
  Embedding  ████░░░░░░ 2/4 (+模型管理, +Batch处理)
```

> [!TIP]
> **下一步**: 在 `seed-modules.ts` 中添加这 4 个新模块的条目，然后运行 seed 脚本注册到 Module Market。
