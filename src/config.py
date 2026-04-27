from dataclasses import dataclass, field
from typing import List
import yaml


@dataclass
class ExperimentConfig:
    attacker_model:    str
    target_model:      str
    judge_model:       str
    embedding_model:   str
    top_k:             List[int]
    poison_ratio:      List[float]
    seed:              int
    max_iter:          int   = 4
    sim_threshold:     float = 0.75
    stealth_threshold: float = 0.60
    payload_threshold: float = 0.70

    @classmethod
    def from_yaml(cls, path: str) -> "ExperimentConfig":
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(**data)
