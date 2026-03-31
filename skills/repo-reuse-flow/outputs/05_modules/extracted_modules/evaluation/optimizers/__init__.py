from .optimizers.base import Optimizer
from .optimizers.genetic import GeneticOptimizer

try:
    from .optimizers.dspy_optimizer import DSPyOptimizer

    __all__ = [
        "Optimizer",
        "GeneticOptimizer",
        "DSPyOptimizer",
    ]
except ImportError:
    __all__ = [
        "Optimizer",
        "GeneticOptimizer",
    ]
