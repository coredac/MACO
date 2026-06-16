"""Stage-3b agent: Fine-grained Judge.

Second-level selection described in MACO Sec. III-D. Cooperates with the
ConfidenceAdaptiveSelector to pick the single best design from the top-K
shortlist, optionally consuming self-learning feedback from prior iterations
(Fig. 6 in the paper).
"""

import json
import os
import re

from openai import OpenAI


def call_model(model, prompt, temperature=0.7):
    """Unified model calling function (DashScope-compatible OpenAI SDK)."""
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        raise RuntimeError("DASHSCOPE_API_KEY environment variable is not set")
    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert CGRA architecture designer."},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error message: {e}")
        print("Please refer to the documentation: https://help.aliyun.com/zh/model-studio/developer-reference/error-code")


class FineGrainedJudge:
    """Stage-3b agent: picks the single best CGRA design from the top-K shortlist."""

    def __init__(self, model="qwen-plus"):
        self.model = model

    def select_best(self, topk_designs, optimization_goal="performance", feedback=None):
        """Return the best design among the top-K, honoring prior-iteration feedback."""
        feedback_text = f"\nPrevious iteration feedback: {feedback}\n" if feedback else ""

        prompt = f"""
    You are an expert in CGRA architecture design.
    I will give you several Top-K candidate CGRA designs (already filtered).
    Now your task is to select the SINGLE best design based on the optimization goal: {optimization_goal}.
    {feedback_text}
    Criteria:
    - If goal is 'performance': prefer larger parallelism, vectorization, higher throughput.
    - If goal is 'power': prefer smaller area, lower memory usage, balanced FU count.

    Return in a JSON object with two keys:
    1. "best_design": the best design in a valid JSON object.
    2. "reason": explanation for why this design was chosen.

    Top-K Designs:
    {json.dumps(topk_designs, indent=2)}

    Important:
    - Return only the JSON object, no extra text.
    - Include everything without omission.
    """

        content = call_model(self.model, prompt, temperature=0.3)
        print(content)

        json_match = re.search(r"(\{[\s\S]*\})", content)
        if json_match:
            try:
                parsed = json.loads(json_match.group(1))
                return parsed.get("best_design", {})
            except json.JSONDecodeError:
                pass
        return {}


if __name__ == "__main__":
    with open("../results/cgra_top_k.json", "r") as f:
        topk_designs = json.load(f)
    topk_designs = json.dumps(topk_designs, separators=(',', ':'))

    judge = FineGrainedJudge(model="qwen-plus")
    best_design = judge.select_best(topk_designs, optimization_goal="performance")
    with open("../results/cgra_best_design.json", "w") as f:
        json.dump(best_design, f, indent=2)
