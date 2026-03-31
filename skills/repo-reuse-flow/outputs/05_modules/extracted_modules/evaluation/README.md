# evaluation

> RAG evaluation metrics: faithfulness, relevance, context precision, answer correctness

**提取时间**: 2026-03-29 12:16
**文件数量**: 176
**外部依赖**: PIL, appdirs, atexit, binascii, datacompy, datasets, diskcache, dspy, git, google, google_auth_oauthlib, googleapiclient, haystack, huggingface_hub, instructor, langchain, langchain_community, langchain_core, langchain_openai, llama_index, nest_asyncio, numpy, oci, openai, pandas, pydantic, pydantic_core, ragas, ragas_experimental, rapidfuzz, requests, rich, rouge_score, sacrebleu, scipy, sentence_transformers, sklearn, tenacity, tiktoken, torch, tqdm, transformers, vertexai

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
| `metrics\__init__.py` | from `metrics\__init__.py` |
| `metrics\_answer_correctness.py` | from `metrics\_answer_correctness.py` |
| `metrics\_answer_relevance.py` | from `metrics\_answer_relevance.py` |
| `metrics\_answer_similarity.py` | from `metrics\_answer_similarity.py` |
| `metrics\_aspect_critic.py` | from `metrics\_aspect_critic.py` |
| `metrics\_bleu_score.py` | from `metrics\_bleu_score.py` |
| `metrics\_chrf_score.py` | from `metrics\_chrf_score.py` |
| `metrics\_context_entities_recall.py` | from `metrics\_context_entities_recall.py` |
| `metrics\_context_precision.py` | from `metrics\_context_precision.py` |
| `metrics\_context_recall.py` | from `metrics\_context_recall.py` |
| `metrics\_datacompy_score.py` | from `metrics\_datacompy_score.py` |
| `metrics\_domain_specific_rubrics.py` | from `metrics\_domain_specific_rubrics.py` |
| `metrics\_factual_correctness.py` | from `metrics\_factual_correctness.py` |
| `metrics\_faithfulness.py` | from `metrics\_faithfulness.py` |
| `metrics\_goal_accuracy.py` | from `metrics\_goal_accuracy.py` |
| `metrics\_instance_specific_rubrics.py` | from `metrics\_instance_specific_rubrics.py` |
| `metrics\_multi_modal_faithfulness.py` | from `metrics\_multi_modal_faithfulness.py` |
| `metrics\_multi_modal_relevance.py` | from `metrics\_multi_modal_relevance.py` |
| `metrics\_noise_sensitivity.py` | from `metrics\_noise_sensitivity.py` |
| `metrics\_nv_metrics.py` | from `metrics\_nv_metrics.py` |
| `metrics\_rouge_score.py` | from `metrics\_rouge_score.py` |
| `metrics\_simple_criteria.py` | from `metrics\_simple_criteria.py` |
| `metrics\_sql_semantic_equivalence.py` | from `metrics\_sql_semantic_equivalence.py` |
| `metrics\_string.py` | from `metrics\_string.py` |
| `metrics\_summarization.py` | from `metrics\_summarization.py` |
| `metrics\_tool_call_accuracy.py` | from `metrics\_tool_call_accuracy.py` |
| `metrics\_tool_call_f1.py` | from `metrics\_tool_call_f1.py` |
| `metrics\_topic_adherence.py` | from `metrics\_topic_adherence.py` |
| `metrics\base.py` | from `metrics\base.py` |
| `metrics\collections\__init__.py` | from `metrics\collections\__init__.py` |
| `metrics\collections\_bleu_score.py` | from `metrics\collections\_bleu_score.py` |
| `metrics\collections\_rouge_score.py` | from `metrics\collections\_rouge_score.py` |
| `metrics\collections\_semantic_similarity.py` | from `metrics\collections\_semantic_similarity.py` |
| `metrics\collections\_string.py` | from `metrics\collections\_string.py` |
| `metrics\collections\agent_goal_accuracy\__init__.py` | from `metrics\collections\agent_goal_accuracy\__init__.py` |
| `metrics\collections\agent_goal_accuracy\metric.py` | from `metrics\collections\agent_goal_accuracy\metric.py` |
| `metrics\collections\agent_goal_accuracy\util.py` | from `metrics\collections\agent_goal_accuracy\util.py` |
| `metrics\collections\answer_accuracy\__init__.py` | from `metrics\collections\answer_accuracy\__init__.py` |
| `metrics\collections\answer_accuracy\metric.py` | from `metrics\collections\answer_accuracy\metric.py` |
| `metrics\collections\answer_accuracy\util.py` | from `metrics\collections\answer_accuracy\util.py` |
| `metrics\collections\answer_correctness\__init__.py` | from `metrics\collections\answer_correctness\__init__.py` |
| `metrics\collections\answer_correctness\metric.py` | from `metrics\collections\answer_correctness\metric.py` |
| `metrics\collections\answer_correctness\util.py` | from `metrics\collections\answer_correctness\util.py` |
| `metrics\collections\answer_relevancy\__init__.py` | from `metrics\collections\answer_relevancy\__init__.py` |
| `metrics\collections\answer_relevancy\metric.py` | from `metrics\collections\answer_relevancy\metric.py` |
| `metrics\collections\answer_relevancy\util.py` | from `metrics\collections\answer_relevancy\util.py` |
| `metrics\collections\base.py` | from `metrics\collections\base.py` |
| `metrics\collections\chrf_score\__init__.py` | from `metrics\collections\chrf_score\__init__.py` |
| `metrics\collections\chrf_score\metric.py` | from `metrics\collections\chrf_score\metric.py` |
| `metrics\collections\context_entity_recall\__init__.py` | from `metrics\collections\context_entity_recall\__init__.py` |
| `metrics\collections\context_entity_recall\metric.py` | from `metrics\collections\context_entity_recall\metric.py` |
| `metrics\collections\context_entity_recall\util.py` | from `metrics\collections\context_entity_recall\util.py` |
| `metrics\collections\context_precision\__init__.py` | from `metrics\collections\context_precision\__init__.py` |
| `metrics\collections\context_precision\metric.py` | from `metrics\collections\context_precision\metric.py` |
| `metrics\collections\context_precision\util.py` | from `metrics\collections\context_precision\util.py` |
| `metrics\collections\context_recall\__init__.py` | from `metrics\collections\context_recall\__init__.py` |
| `metrics\collections\context_recall\metric.py` | from `metrics\collections\context_recall\metric.py` |
| `metrics\collections\context_recall\util.py` | from `metrics\collections\context_recall\util.py` |
| `metrics\collections\context_relevance\__init__.py` | from `metrics\collections\context_relevance\__init__.py` |
| `metrics\collections\context_relevance\metric.py` | from `metrics\collections\context_relevance\metric.py` |
| `metrics\collections\context_relevance\util.py` | from `metrics\collections\context_relevance\util.py` |
| `metrics\collections\datacompy_score\__init__.py` | from `metrics\collections\datacompy_score\__init__.py` |
| `metrics\collections\datacompy_score\metric.py` | from `metrics\collections\datacompy_score\metric.py` |
| `metrics\collections\domain_specific_rubrics\__init__.py` | from `metrics\collections\domain_specific_rubrics\__init__.py` |
| `metrics\collections\domain_specific_rubrics\metric.py` | from `metrics\collections\domain_specific_rubrics\metric.py` |
| `metrics\collections\domain_specific_rubrics\util.py` | from `metrics\collections\domain_specific_rubrics\util.py` |
| `metrics\collections\example_metric.py` | from `metrics\collections\example_metric.py` |
| `metrics\collections\factual_correctness\__init__.py` | from `metrics\collections\factual_correctness\__init__.py` |
| `metrics\collections\factual_correctness\metric.py` | from `metrics\collections\factual_correctness\metric.py` |
| `metrics\collections\factual_correctness\util.py` | from `metrics\collections\factual_correctness\util.py` |
| `metrics\collections\faithfulness\__init__.py` | from `metrics\collections\faithfulness\__init__.py` |
| `metrics\collections\faithfulness\metric.py` | from `metrics\collections\faithfulness\metric.py` |
| `metrics\collections\faithfulness\util.py` | from `metrics\collections\faithfulness\util.py` |
| `metrics\collections\instance_specific_rubrics\__init__.py` | from `metrics\collections\instance_specific_rubrics\__init__.py` |
| `metrics\collections\instance_specific_rubrics\metric.py` | from `metrics\collections\instance_specific_rubrics\metric.py` |
| `metrics\collections\instance_specific_rubrics\util.py` | from `metrics\collections\instance_specific_rubrics\util.py` |
| `metrics\collections\multi_modal_faithfulness\__init__.py` | from `metrics\collections\multi_modal_faithfulness\__init__.py` |
| `metrics\collections\multi_modal_faithfulness\metric.py` | from `metrics\collections\multi_modal_faithfulness\metric.py` |
| `metrics\collections\multi_modal_faithfulness\util.py` | from `metrics\collections\multi_modal_faithfulness\util.py` |
| `metrics\collections\multi_modal_relevance\__init__.py` | from `metrics\collections\multi_modal_relevance\__init__.py` |
| `metrics\collections\multi_modal_relevance\metric.py` | from `metrics\collections\multi_modal_relevance\metric.py` |
| `metrics\collections\multi_modal_relevance\util.py` | from `metrics\collections\multi_modal_relevance\util.py` |
| `metrics\collections\noise_sensitivity\__init__.py` | from `metrics\collections\noise_sensitivity\__init__.py` |
| `metrics\collections\noise_sensitivity\metric.py` | from `metrics\collections\noise_sensitivity\metric.py` |
| `metrics\collections\noise_sensitivity\util.py` | from `metrics\collections\noise_sensitivity\util.py` |
| `metrics\collections\quoted_spans\__init__.py` | from `metrics\collections\quoted_spans\__init__.py` |
| `metrics\collections\quoted_spans\metric.py` | from `metrics\collections\quoted_spans\metric.py` |
| `metrics\collections\quoted_spans\util.py` | from `metrics\collections\quoted_spans\util.py` |
| `metrics\collections\response_groundedness\__init__.py` | from `metrics\collections\response_groundedness\__init__.py` |
| `metrics\collections\response_groundedness\metric.py` | from `metrics\collections\response_groundedness\metric.py` |
| `metrics\collections\response_groundedness\util.py` | from `metrics\collections\response_groundedness\util.py` |
| `metrics\collections\sql_semantic_equivalence\__init__.py` | from `metrics\collections\sql_semantic_equivalence\__init__.py` |
| `metrics\collections\sql_semantic_equivalence\metric.py` | from `metrics\collections\sql_semantic_equivalence\metric.py` |
| `metrics\collections\sql_semantic_equivalence\util.py` | from `metrics\collections\sql_semantic_equivalence\util.py` |
| `metrics\collections\summary_score\__init__.py` | from `metrics\collections\summary_score\__init__.py` |
| `metrics\collections\summary_score\metric.py` | from `metrics\collections\summary_score\metric.py` |
| `metrics\collections\summary_score\util.py` | from `metrics\collections\summary_score\util.py` |
| `metrics\collections\tool_call_accuracy\__init__.py` | from `metrics\collections\tool_call_accuracy\__init__.py` |
| `metrics\collections\tool_call_accuracy\metric.py` | from `metrics\collections\tool_call_accuracy\metric.py` |
| `metrics\collections\tool_call_accuracy\util.py` | from `metrics\collections\tool_call_accuracy\util.py` |
| `metrics\collections\tool_call_f1\__init__.py` | from `metrics\collections\tool_call_f1\__init__.py` |
| `metrics\collections\tool_call_f1\metric.py` | from `metrics\collections\tool_call_f1\metric.py` |
| `metrics\collections\tool_call_f1\util.py` | from `metrics\collections\tool_call_f1\util.py` |
| `metrics\collections\topic_adherence\__init__.py` | from `metrics\collections\topic_adherence\__init__.py` |
| `metrics\collections\topic_adherence\metric.py` | from `metrics\collections\topic_adherence\metric.py` |
| `metrics\collections\topic_adherence\util.py` | from `metrics\collections\topic_adherence\util.py` |
| `metrics\decorator.py` | from `metrics\decorator.py` |
| `metrics\discrete.py` | from `metrics\discrete.py` |
| `metrics\numeric.py` | from `metrics\numeric.py` |
| `metrics\quoted_spans.py` | from `metrics\quoted_spans.py` |
| `metrics\ranking.py` | from `metrics\ranking.py` |
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
| `prompt\metrics\base_prompt.py` | from `prompt\metrics\base_prompt.py` |
| `prompt\metrics\common.py` | from `prompt\metrics\common.py` |
| `prompt\mixin.py` | from `prompt\mixin.py` |
| `prompt\multi_modal_prompt.py` | from `prompt\multi_modal_prompt.py` |
| `prompt\pydantic_prompt.py` | from `prompt\pydantic_prompt.py` |
| `prompt\simple_prompt.py` | from `prompt\simple_prompt.py` |
| `prompt\utils.py` | from `prompt\utils.py` |
| `run_config.py` | from `run_config.py` |
| `tokenizers.py` | from `tokenizers.py` |
| `utils.py` | from `utils.py` |
| `validation.py` | from `validation.py` |

## 使用方式

```python
# 将 evaluation/ 目录复制到你的项目中
from evaluation import ...
```
