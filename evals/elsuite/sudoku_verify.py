from typing import Any
import numpy as np

import evals
import evals.metrics
from evals.api import CompletionFn
from evals.prompt.base import is_chat_prompt


class SudokuVerify(evals.Eval):
    """Verify the solution for a sodoku puzzle generated by the llm model.

    The solution is a 9x9 matrix of integers in the range [1, 9].

    The solution is valid if:
    - Each row contains the digits 1-9 exactly once.
    - Each column contains the digits 1-9 exactly once.
    - Each 3x3 subgrid contains the digits 1-9 exactly once.

    The solution is invalid if:
    - Any row contains a digit more than once.
    - Any column contains a digit more than once.
    - Any 3x3 subgrid contains a digit more than once.
    - Any element is not an integer in the range [1, 9].
    - The solution is not a 9x9 matrix.

    Solving a Sudoku puzzle tests the following abilities:
    - understanding the rules of the game and then applying those rules to a grid of numbers
    - the ability to backtrack when a path explored to find the solution is incorrect.
    - maintain memory
    - understand if a puzzle is solvable or not
    - not going into repeated loops
    """

    def __init__(
        self,
        completion_fns: list[CompletionFn],
        samples_jsonl: str,
        *args,
        max_tokens: int = 500,
        num_few_shot: int = 0,
        few_shot_jsonl: str = None,
        **kwargs,
    ):
        super().__init__(completion_fns, *args, **kwargs)
        assert len(
            completion_fns) == 1, "SudokuVerify only supports one completion fn"
        self.max_tokens = max_tokens
        self.samples_jsonl = samples_jsonl
        self.num_few_shot = num_few_shot
        if self.num_few_shot > 0:
            assert few_shot_jsonl is not None, "few shot requires few shot sample dataset"
            self.few_shot_jsonl = few_shot_jsonl
            self.few_shot = evals.get_jsonl(self.few_shot_jsonl)

    def eval_sample(self, sample: Any, *_):
        prompt = sample["input"]
        expected = sample["ideal"]
        if self.num_few_shot > 0:
            assert is_chat_prompt(
                sample["input"]), "few shot requires chat prompt"
            prompt = sample["input"][:-1]
            for s in self.few_shot[: self.num_few_shot]:
                prompt += s["sample"]
            prompt += sample["input"][-1:]

        result = self.completion_fn(
            prompt=prompt,
            max_tokens=self.max_tokens,
        )
        sampled = result.get_completions()[0]
        solution = self.parse_sudoku(sampled)

        if self.sudoku_verify(solution) or expected in sampled:
            evals.record.record_match(
                True, expected=expected, sampled=sampled
            )
        else:
            evals.record.record_match(
                False, expected=expected, sampled=sampled
            )

    def run(self, recorder):
        samples = self.get_samples()
        self.eval_all_samples(recorder, samples)
        events = recorder.get_events("match")
        return {
            "accuracy": evals.metrics.get_accuracy(events),
        }

    def parse_sudoku(self, sampled):
        """Parse the solution for a sodoku puzzle generated by the llm model.

        Args:
            sampled (str): A string containing the solution for a sodoku puzzle.

        Returns:
            np.ndarray: A 9x9 matrix of integers in the range [1, 9].
        """
        # filter out empty lines and lines with only whitespaces 
        # and remove all whitespaces from all lines
        sudoku_text = "\n".join(["".join(line.strip().split())
                            for line in sampled.splitlines() if line.strip()])

        # filter out all lines which have non digit characters
        sudoku_text = "\n".join(
            [line for line in sudoku_text.splitlines() if line.isdigit()])

        if len("".join(sudoku_text)) != 81:
            return np.zeros((9, 9), dtype=int)
        
        # parse the solution
        solution = np.zeros((9, 9), dtype=int)
        try:
            for i, line in enumerate(sudoku_text.splitlines()):
                for j, c in enumerate(line):
                    if c.isdigit():
                        solution[i, j] = int(c)
        except Exception:
            return np.zeros((9, 9), dtype=int)
        return solution

    def sudoku_verify(self, solution):
        """Verify that a solution is valid.

        Args:
            solution (np.ndarray): A 9x9 matrix of integers in the range [1, 9].

        Returns:
            bool: True if the solution is valid, False otherwise.
        """
        if not isinstance(solution, np.ndarray) \
        or solution.shape != (9, 9) \
        or (not np.all(np.logical_and(solution >= 1, solution <= 9))) \
        or (not np.all(np.unique(solution, axis=1) == 9)) \
        or (not np.all(np.unique(solution, axis=0) == 9)):
            return False

        for i in range(3):
            for j in range(3):
                subgrid = solution[3 * i: 3 * i + 3, 3 * j: 3 * j + 3]
                if not np.all(np.unique(subgrid) == 9):
                    return False
        return True
