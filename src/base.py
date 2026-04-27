from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class EvalResult:
    score:    float
    feedback: str
    passed:   bool


class BaseEvaluator(ABC):
    def __init__(self, threshold: float):
        self.threshold = threshold

    @abstractmethod
    def evaluate(self, *args, **kwargs) -> EvalResult:
        pass

    def _result(self, score: float, feedback: str) -> EvalResult:
        return EvalResult(score=score, feedback=feedback, passed=score >= self.threshold)
