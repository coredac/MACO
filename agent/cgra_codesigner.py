"""Stage-1 agent: CGRA Co-designer.

Implements the joint HW/SW candidate generator described in
MACO Sec. III-B (Stage 1: CGRA Design).
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


class CGRACoDesigner:
    """Stage-1 agent that proposes candidate CGRA HW/SW designs."""

    def __init__(self, model="qwen-plus"):
        self.model = model

    def design(
        self,
        kernel,
        DFG_node_counts,
        max_independent_ops_per_cycle,
        vectorizable_ops,
        optimization_goal,
        N=5,
        extra_prompt=None,
        extra_prompt2=None,
    ):
        """Generate N candidate CGRA designs as a JSON list."""
        prompt = f"""
You are an expert CGRA architect.

Input:
kernel={kernel}
DFG_node_counts={DFG_node_counts}
max_independent_ops_per_cycle={max_independent_ops_per_cycle}
vectorizable_ops={vectorizable_ops}
optimization_goal="{optimization_goal}"

{extra_prompt}

Task:
{extra_prompt2}
Generate {N} candidate CGRA designs in JSON format. Each design must include:
- tile_size: 2x2 to 8x8 (the tile size should be square, each dimension indicates number of rows and columns of tiles; total tile count = rows * columns, e.g., 6x6 = 36 tiles, 8x8 = 64 tiles)
- FUs: dictionary mapping each tile to a list of supported functional units. Each tile can include any of ["Ld", "St", "Cmp", "Phi", "Br", "Sel", "Ret", "Add", "Mul", "Div", "Logic"].
  ⚠️ The FU dictionary must include exactly total_tile_count tiles named sequentially from tile0 to tile total_tile_count - 1.
  For example, if tile_size is 8x8, there are 64 tiles, so they should be named tile0, tile1, ..., tile63.
- config_mem: number of configuration instructions each tile can store (range 16 to 1024 instructions)
- data_spm_kb: scratchpad memory in KB (range 4KB to 256KB)
- unroll_factor: loop unroll factor (1 to 6)
- vectorize: one of "all", "interleaved", or "none"
- reasoning: brief explanation why this design fits the input kernel and optimization goal

Example output (JSON list):

[
  {{
    "tile_size": "4x4",
    "FUs": {{"tile0": ["Add"],"tile1": ["Ld", "Add"],"tile2": ["Mul"],"tile3": ["Ld"],"tile4": ["Cmp", "Phi", "Br"],"tile5": ["Logic","Sel","Ret"],"tile6": ["Div"],"tile7": ["St"],"tile8": ["Ld"]}},
    "config_mem": 128,
    "data_spm_kb": 64,
    "unroll_factor": 2,
    "vectorize": "all",
    "reasoning": "Tile-level FU assignment balances computation and memory access; vectorize all Add/Mul for SIMD; config storage sufficient for kernel instructions; control units placed to handle branches and phi nodes."
  }}
]

Important:
- Return only a valid JSON list, no extra text.
- Ensure each design includes a brief reasoning explaining the choices.
"""

        content = call_model(self.model, prompt)
        print(content)
        json_match = re.search(r"(\[.*\])", content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                print("⚠️ Extracted JSON is invalid:")
                print(json_match.group(1))
        return []


if __name__ == "__main__":
    DFG_node_counts = {"Add": 10, "Mul": 5, "Ld": 6, "St": 6, "Cmp": 2}
    co_designer = CGRACoDesigner(model="deepseek-chat")
    candidates = co_designer.design(
        kernel={},
        DFG_node_counts=DFG_node_counts,
        max_independent_ops_per_cycle=4,
        vectorizable_ops=["Add", "Mul"],
        optimization_goal="performance",
        N=2,
    )
    candidates_no_reason = [{k: v for k, v in c.items() if k != "reasoning"} for c in candidates]

    try:
        with open("../results/cgra_candidates_raw.json", "r") as f:
            raw_candidates = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        raw_candidates = []

    raw_candidates.extend(candidates_no_reason)
    with open("../results/cgra_candidates_raw.json", "w") as f:
        json.dump(raw_candidates, f, indent=2)
