"""Stage-3a agent: Coarse-grained Judge.

First-level screen described in MACO Sec. III-D.
Uses LLM reasoning only (no EDA tool calls) to quickly shortlist top-K
high-potential designs from the fixed candidate pool.
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


class CoarseGrainedJudge:
    """Stage-3a agent: LLM-only top-K screening of candidate designs."""

    def __init__(self, model="qwen-plus"):
        self.model = model

    def judge(self, candidate_designs, optimization_goal="performance", top_k=3):
        """Return the LLM-selected top-K designs."""
        prompt = f"""
    You are an expert in CGRA architecture design.
    I will give you several candidate CGRA designs.
    Your task is to evaluate them based on the optimization goal: {optimization_goal}.

    Criteria:
    - If goal is 'performance': prefer larger parallelism, vectorization, higher throughput.
    - If goal is 'power': prefer smaller area, lower memory usage, balanced FU count.

    Return in a JSON object with two keys:
    1. "top_k_design": the top-{top_k} designs in a valid JSON list, ordered from best to worst.
    2. "reason": explanation for why these designs were chosen.


    Candidate Designs:
    {json.dumps(candidate_designs, indent=2)}

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
                return parsed.get("top_k_design", [])
            except json.JSONDecodeError:
                print("⚠️ Extracted JSON is invalid:")
                print(json_match.group(1))
        else:
            print("⚠️ No JSON found in content.")
        return []


if __name__ == "__main__":
    with open("../results/cgra_candidates_fixed.json", "r") as f:
        candidate_designs = json.load(f)
    candidate_designs_json = json.dumps(candidate_designs, separators=(',', ':'))

    judge = CoarseGrainedJudge(model="qwen-plus")
    top_designs = judge.judge(candidate_designs_json, optimization_goal="performance", top_k=2)
    with open("../results/cgra_top_k.json", "w") as f:
        json.dump(top_designs, f, indent=2)
