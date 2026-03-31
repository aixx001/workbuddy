"""Collections of metrics using modern component architecture."""

from ..metrics.collections._bleu_score import BleuScore
from ..metrics.collections._rouge_score import RougeScore
from ..metrics.collections._semantic_similarity import SemanticSimilarity
from ..metrics.collections._string import (
    DistanceMeasure,
    ExactMatch,
    NonLLMStringSimilarity,
    StringPresence,
)
from ..metrics.collections.agent_goal_accuracy import (
    AgentGoalAccuracy,
    AgentGoalAccuracyWithoutReference,
    AgentGoalAccuracyWithReference,
)
from ..metrics.collections.answer_accuracy import AnswerAccuracy
from ..metrics.collections.answer_correctness import AnswerCorrectness
from ..metrics.collections.answer_relevancy import AnswerRelevancy
from ..metrics.collections.base import BaseMetric
from ..metrics.collections.chrf_score import CHRFScore
from ..metrics.collections.context_entity_recall import ContextEntityRecall
from ..metrics.collections.context_precision import (
    ContextPrecision,
    ContextPrecisionWithoutReference,
    ContextPrecisionWithReference,
    ContextUtilization,
)
from ..metrics.collections.context_recall import ContextRecall
from ..metrics.collections.context_relevance import ContextRelevance
from ..metrics.collections.datacompy_score import DataCompyScore
from ..metrics.collections.domain_specific_rubrics import (
    DomainSpecificRubrics,
    RubricsScoreWithoutReference,
    RubricsScoreWithReference,
)
from ..metrics.collections.factual_correctness import FactualCorrectness
from ..metrics.collections.faithfulness import Faithfulness
from ..metrics.collections.instance_specific_rubrics import InstanceSpecificRubrics
from ..metrics.collections.multi_modal_faithfulness import MultiModalFaithfulness
from ..metrics.collections.multi_modal_relevance import MultiModalRelevance
from ..metrics.collections.noise_sensitivity import NoiseSensitivity
from ..metrics.collections.quoted_spans import QuotedSpansAlignment
from ..metrics.collections.response_groundedness import ResponseGroundedness
from ..metrics.collections.sql_semantic_equivalence import SQLSemanticEquivalence
from ..metrics.collections.summary_score import SummaryScore
from ..metrics.collections.tool_call_accuracy import ToolCallAccuracy
from ..metrics.collections.tool_call_f1 import ToolCallF1
from ..metrics.collections.topic_adherence import TopicAdherence

__all__ = [
    "BaseMetric",  # Base class
    # RAG metrics
    "AnswerAccuracy",
    "AnswerCorrectness",
    "AnswerRelevancy",
    "BleuScore",
    "CHRFScore",
    "ContextEntityRecall",
    "ContextRecall",
    "ContextPrecision",
    "ContextPrecisionWithReference",
    "ContextPrecisionWithoutReference",
    "ContextRelevance",
    "ContextUtilization",
    "DistanceMeasure",
    "ExactMatch",
    "FactualCorrectness",
    "Faithfulness",
    "MultiModalFaithfulness",
    "MultiModalRelevance",
    "NoiseSensitivity",
    "NonLLMStringSimilarity",
    "QuotedSpansAlignment",
    "ResponseGroundedness",
    "RougeScore",
    "SemanticSimilarity",
    "StringPresence",
    "SummaryScore",
    # Agent & Tool metrics
    "AgentGoalAccuracy",
    "AgentGoalAccuracyWithReference",
    "AgentGoalAccuracyWithoutReference",
    "ToolCallAccuracy",
    "ToolCallF1",
    "TopicAdherence",
    # Rubric metrics
    "DomainSpecificRubrics",
    "InstanceSpecificRubrics",
    "RubricsScoreWithoutReference",
    "RubricsScoreWithReference",
    # SQL & Data metrics
    "DataCompyScore",
    "SQLSemanticEquivalence",
]
