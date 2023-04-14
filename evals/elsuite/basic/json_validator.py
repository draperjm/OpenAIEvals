import json
from typing import Any

import numpy as np

import evals
import evals.record
from evals.api import CompletionFn


def is_valid_json(s):
    try:
        json.loads(s)
        return True
    except ValueError:
        return False


class JsonValidator(evals.Eval):
    def __init__(
        self,
        completion_fns: list[CompletionFn],
        samples_jsonl: str,
        *args,
        max_tokens: int = 500,
        **kwargs,
    ):
        super().__init__(completion_fns, *args, **kwargs)
        assert len(completion_fns) == 1, "JsonValidator only supports one completion fn"
        self.max_tokens = max_tokens
        self.samples_jsonl = samples_jsonl

    def eval_sample(self, sample: Any, *_):
        prompt = sample["input"]
        result = self.completion_fn(
            prompt=prompt,
            temperature=0.0,
        )
        sampled = result.get_completions()[0]
        return evals.record.record_metrics(
            is_valid_json=is_valid_json(sampled),
        )

    def run(self, recorder):
        samples = self.get_samples()
        self.eval_all_samples(recorder, samples)
        metrics = recorder.get_metrics()
        return {"num_valid_json": np.mean([m["is_valid_json"] for m in metrics])}
