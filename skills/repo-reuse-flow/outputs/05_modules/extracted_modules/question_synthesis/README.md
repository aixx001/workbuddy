# question_synthesis

> Automatic test question generation from documents using knowledge graphs

**提取时间**: 2026-03-29 12:20
**文件数量**: 105
**外部依赖**: PIL, appdirs, atexit, binascii, datasets, diskcache, dspy, git, google, google_auth_oauthlib, googleapiclient, haystack, huggingface_hub, instructor, langchain_community, langchain_core, langchain_openai, llama_index, nest_asyncio, networkx, numpy, oci, openai, pandas, pydantic, pydantic_core, ragas, ragas_experimental, rapidfuzz, requests, rich, sentence_transformers, sknetwork, tenacity, tiktoken, torch, tqdm, transformers, vertexai

## ⚠️ 未解析的 import

以下 import 可能需要手动处理：

- `__init__.py: from ._version import version`

## 文件列表

| 文件 | 说明 |
|------|------|
| `__init__.py` | from `__init__.py` |
| `_analytics.py` | from `_analytics.py` |
| `async_utils.py` | from `async_utils.py` |
| `backends\__init__.py` | from `backends\__init__.py` |
| `backends\base.py` | from `backends\base.py` |
| `backends\gdrive_backend.py` | from `backends\gdrive_backend.py` |
| `backends\inmemory.py` | from `backends\inmemory.py` |
| `backends\local_csv.py` | from `backends\local_csv.py` |
| `backends\local_jsonl.py` | from `backends\local_jsonl.py` |
| `backends\registry.py` | from `backends\registry.py` |
| `cache.py` | from `cache.py` |
| `callbacks.py` | from `callbacks.py` |
| `config.py` | from `config.py` |
| `cost.py` | from `cost.py` |
| `dataset.py` | from `dataset.py` |
| `dataset_schema.py` | from `dataset_schema.py` |
| `embeddings\__init__.py` | from `embeddings\__init__.py` |
| `embeddings\base.py` | from `embeddings\base.py` |
| `embeddings\google_provider.py` | from `embeddings\google_provider.py` |
| `embeddings\haystack_wrapper.py` | from `embeddings\haystack_wrapper.py` |
| `embeddings\huggingface_provider.py` | from `embeddings\huggingface_provider.py` |
| `embeddings\litellm_provider.py` | from `embeddings\litellm_provider.py` |
| `embeddings\openai_provider.py` | from `embeddings\openai_provider.py` |
| `embeddings\utils.py` | from `embeddings\utils.py` |
| `evaluation.py` | from `evaluation.py` |
| `exceptions.py` | from `exceptions.py` |
| `executor.py` | from `executor.py` |
| `experiment.py` | from `experiment.py` |
| `integrations\helicone.py` | from `integrations\helicone.py` |
| `llms\__init__.py` | from `llms\__init__.py` |
| `llms\adapters\__init__.py` | from `llms\adapters\__init__.py` |
| `llms\adapters\base.py` | from `llms\adapters\base.py` |
| `llms\adapters\instructor.py` | from `llms\adapters\instructor.py` |
| `llms\adapters\litellm.py` | from `llms\adapters\litellm.py` |
| `llms\base.py` | from `llms\base.py` |
| `llms\haystack_wrapper.py` | from `llms\haystack_wrapper.py` |
| `llms\litellm_llm.py` | from `llms\litellm_llm.py` |
| `llms\oci_genai_wrapper.py` | from `llms\oci_genai_wrapper.py` |
| `losses.py` | from `losses.py` |
| `messages.py` | from `messages.py` |
| `metrics\_answer_correctness.py` | from `metrics\_answer_correctness.py` |
| `metrics\_answer_relevance.py` | from `metrics\_answer_relevance.py` |
| `metrics\_answer_similarity.py` | from `metrics\_answer_similarity.py` |
| `metrics\_aspect_critic.py` | from `metrics\_aspect_critic.py` |
| `metrics\_context_precision.py` | from `metrics\_context_precision.py` |
| `metrics\_context_recall.py` | from `metrics\_context_recall.py` |
| `metrics\_faithfulness.py` | from `metrics\_faithfulness.py` |
| `metrics\_string.py` | from `metrics\_string.py` |
| `metrics\base.py` | from `metrics\base.py` |
| `metrics\result.py` | from `metrics\result.py` |
| `metrics\utils.py` | from `metrics\utils.py` |
| `metrics\validators.py` | from `metrics\validators.py` |
| `optimizers\__init__.py` | from `optimizers\__init__.py` |
| `optimizers\base.py` | from `optimizers\base.py` |
| `optimizers\dspy_adapter.py` | from `optimizers\dspy_adapter.py` |
| `optimizers\dspy_llm_wrapper.py` | from `optimizers\dspy_llm_wrapper.py` |
| `optimizers\dspy_optimizer.py` | from `optimizers\dspy_optimizer.py` |
| `optimizers\genetic.py` | from `optimizers\genetic.py` |
| `optimizers\utils.py` | from `optimizers\utils.py` |
| `prompt\__init__.py` | from `prompt\__init__.py` |
| `prompt\base.py` | from `prompt\base.py` |
| `prompt\dynamic_few_shot.py` | from `prompt\dynamic_few_shot.py` |
| `prompt\few_shot_pydantic_prompt.py` | from `prompt\few_shot_pydantic_prompt.py` |
| `prompt\mixin.py` | from `prompt\mixin.py` |
| `prompt\multi_modal_prompt.py` | from `prompt\multi_modal_prompt.py` |
| `prompt\pydantic_prompt.py` | from `prompt\pydantic_prompt.py` |
| `prompt\simple_prompt.py` | from `prompt\simple_prompt.py` |
| `prompt\utils.py` | from `prompt\utils.py` |
| `run_config.py` | from `run_config.py` |
| `testset\__init__.py` | from `testset\__init__.py` |
| `testset\graph.py` | from `testset\graph.py` |
| `testset\graph_queries.py` | from `testset\graph_queries.py` |
| `testset\persona.py` | from `testset\persona.py` |
| `testset\synthesizers\__init__.py` | from `testset\synthesizers\__init__.py` |
| `testset\synthesizers\base.py` | from `testset\synthesizers\base.py` |
| `testset\synthesizers\generate.py` | from `testset\synthesizers\generate.py` |
| `testset\synthesizers\multi_hop\__init__.py` | from `testset\synthesizers\multi_hop\__init__.py` |
| `testset\synthesizers\multi_hop\abstract.py` | from `testset\synthesizers\multi_hop\abstract.py` |
| `testset\synthesizers\multi_hop\base.py` | from `testset\synthesizers\multi_hop\base.py` |
| `testset\synthesizers\multi_hop\prompts.py` | from `testset\synthesizers\multi_hop\prompts.py` |
| `testset\synthesizers\multi_hop\specific.py` | from `testset\synthesizers\multi_hop\specific.py` |
| `testset\synthesizers\prompts.py` | from `testset\synthesizers\prompts.py` |
| `testset\synthesizers\single_hop\__init__.py` | from `testset\synthesizers\single_hop\__init__.py` |
| `testset\synthesizers\single_hop\base.py` | from `testset\synthesizers\single_hop\base.py` |
| `testset\synthesizers\single_hop\prompts.py` | from `testset\synthesizers\single_hop\prompts.py` |
| `testset\synthesizers\single_hop\specific.py` | from `testset\synthesizers\single_hop\specific.py` |
| `testset\synthesizers\testset_schema.py` | from `testset\synthesizers\testset_schema.py` |
| `testset\synthesizers\utils.py` | from `testset\synthesizers\utils.py` |
| `testset\transforms\__init__.py` | from `testset\transforms\__init__.py` |
| `testset\transforms\base.py` | from `testset\transforms\base.py` |
| `testset\transforms\default.py` | from `testset\transforms\default.py` |
| `testset\transforms\engine.py` | from `testset\transforms\engine.py` |
| `testset\transforms\extractors\__init__.py` | from `testset\transforms\extractors\__init__.py` |
| `testset\transforms\extractors\embeddings.py` | from `testset\transforms\extractors\embeddings.py` |
| `testset\transforms\extractors\llm_based.py` | from `testset\transforms\extractors\llm_based.py` |
| `testset\transforms\extractors\regex_based.py` | from `testset\transforms\extractors\regex_based.py` |
| `testset\transforms\filters.py` | from `testset\transforms\filters.py` |
| `testset\transforms\relationship_builders\__init__.py` | from `testset\transforms\relationship_builders\__init__.py` |
| `testset\transforms\relationship_builders\cosine.py` | from `testset\transforms\relationship_builders\cosine.py` |
| `testset\transforms\relationship_builders\traditional.py` | from `testset\transforms\relationship_builders\traditional.py` |
| `testset\transforms\splitters\__init__.py` | from `testset\transforms\splitters\__init__.py` |
| `testset\transforms\splitters\headline.py` | from `testset\transforms\splitters\headline.py` |
| `tokenizers.py` | from `tokenizers.py` |
| `utils.py` | from `utils.py` |
| `validation.py` | from `validation.py` |

## 使用方式

```python
# 将 question_synthesis/ 目录复制到你的项目中
from question_synthesis import ...
```
