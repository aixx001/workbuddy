# Legacy embeddings - maintain backward compatibility
# Modern embeddings - new interface
from .embeddings.base import (
    BaseRagasEmbedding,
    BaseRagasEmbeddings,
    HuggingfaceEmbeddings,
    LangchainEmbeddingsWrapper as _LangchainEmbeddingsWrapper,
    LlamaIndexEmbeddingsWrapper as _LlamaIndexEmbeddingsWrapper,
    embedding_factory as _embedding_factory,
)
from .embeddings.google_provider import GoogleEmbeddings
from .embeddings.haystack_wrapper import HaystackEmbeddingsWrapper
from .embeddings.huggingface_provider import HuggingFaceEmbeddings
from .embeddings.litellm_provider import LiteLLMEmbeddings
from .embeddings.openai_provider import OpenAIEmbeddings

# Utilities
from .embeddings.utils import batch_texts, get_optimal_batch_size, validate_texts
from .utils import DeprecationHelper

# Create deprecation wrappers for legacy classes
LangchainEmbeddingsWrapper = DeprecationHelper(
    _LangchainEmbeddingsWrapper,
    "LangchainEmbeddingsWrapper is deprecated and will be removed in a future version. "
    "Use the modern embedding providers instead: "
    "embedding_factory('openai', model='text-embedding-3-small', client=openai_client) "
    "or from .embeddings import OpenAIEmbeddings, GoogleEmbeddings, HuggingFaceEmbeddings",
)

LlamaIndexEmbeddingsWrapper = DeprecationHelper(
    _LlamaIndexEmbeddingsWrapper,
    "LlamaIndexEmbeddingsWrapper is deprecated and will be removed in a future version. "
    "Use the modern embedding providers instead: "
    "embedding_factory('openai', model='text-embedding-3-small', client=openai_client) "
    "or from .embeddings import OpenAIEmbeddings, GoogleEmbeddings, HuggingFaceEmbeddings",
)


def embedding_factory(*args, **kwargs):
    """Deprecated: Use embedding_factory from base module directly."""
    import warnings

    warnings.warn(
        "Importing embedding_factory from ragas.embeddings is deprecated. "
        "Import directly from ragas.embeddings.base or use modern providers: "
        "from .embeddings import OpenAIEmbeddings, GoogleEmbeddings, HuggingFaceEmbeddings",
        DeprecationWarning,
        stacklevel=2,
    )
    return _embedding_factory(*args, **kwargs)


__all__ = [
    # Legacy interface (backward compatibility)
    "BaseRagasEmbeddings",
    "HaystackEmbeddingsWrapper",
    "HuggingfaceEmbeddings",
    "LangchainEmbeddingsWrapper",
    "LlamaIndexEmbeddingsWrapper",
    "embedding_factory",
    # Modern interface
    "BaseRagasEmbedding",
    # Backward compatibility alias
    "RagasBaseEmbedding",
    "OpenAIEmbeddings",
    "GoogleEmbeddings",
    "LiteLLMEmbeddings",
    "HuggingFaceEmbeddings",
    # Utilities
    "validate_texts",
    "batch_texts",
    "get_optimal_batch_size",
]

# Backward compatibility alias
RagasBaseEmbedding = BaseRagasEmbedding
