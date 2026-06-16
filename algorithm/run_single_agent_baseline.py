"""Single-agent LLM CGRA baseline.

Reference implementation of the single-agent monolithic flow against which
MACO is benchmarked in the paper (Sec. IV, baseline "Single-Agent LLM Flow").
"""

import json
import re

from openai import OpenAI


def call_model(model, prompt, temperature=0.7):
    """
    Unified model calling function, supports multiple models

    Args:
        model: Model name, supports "gpt-4", "gpt-4o", "deepseek-chat", "deepseek-coder", etc.
        prompt: User input prompt
        temperature: Generation temperature, default 0.7
        api_key: API key (DeepSeek or OpenAI), required when calling official API

    Returns:
        str: Model generated response content
    """
    if 1:
        api_key = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # Replace with your OpenAI API key
        try:
            client = OpenAI(
                # If environment variable is not configured, replace the following line with Alibaba Cloud API Key: api_key="sk-xxx",
                api_key=api_key,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            )

            response = client.chat.completions.create(
                model=model,  # Model list: https://help.aliyun.com/zh/model-studio/getting-started/models
                messages=[
                    {"role": "system", "content": "You are an expert CGRA architecture designer."},
                    {"role": "user", "content": prompt}
                    ]
            )
            # print(response.choices[0].message.content)
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error message: {e}")
            print("Please refer to the documentation: https://help.aliyun.com/zh/model-studio/developer-reference/error-code")
    else:
        raise ValueError(f"Unsupported model: {model}")


class SingleAgentBaseline:
    """Monolithic single-agent CGRA designer used as the baseline comparison."""

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
        """Use the LLM to generate N candidate CGRA designs in one shot."""
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
Generate a CGRA designs in JSON format. The design must include:
- tile_size: 2x2 to 8x8 (the tile size should be square, each dimension indicates number of rows and columns of tiles; total tile count = rows * columns, e.g., 6x6 = 36 tiles, 8x8 = 64 tiles)
- FUs: dictionary mapping each tile to a list of supported functional units. Each tile can include any of ["Ld", "St", "Cmp", "Phi", "Br", "Sel", "Ret", "Add", "Mul", "Div"].
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
    "FUs": {{"tile0": ["Add"],"tile1": ["Ld", "Add"],"tile2": ["Mul"],"tile3": ["Ld"],"tile4": ["Cmp", "Phi", "Br"],"tile5": [],"tile6": [],"tile7": ["St"],"tile8": ["Ld"]}},
    "config_mem": 128,
    "data_spm_kb": 64,
    "unroll_factor": 2,
    "vectorize": "all",
    "reasoning": "Tile-level FU assignment balances computation and memory access; vectorize all Add/Mul for SIMD; config storage sufficient for kernel instructions; control units placed to handle branches and phi nodes."
  }}
]

Domain specific knowledge:
Rule 1. Larger tiles expose more parallelism but cost more area/power; smaller tiles save energy but may under-utilize compute.
Rule 3. Choose unroll for repeated independent operations, which expands the effective DFG node counts and informs the appropriate tile size.
Rule 4: Apply vectorization to SIMD-friendly operations, which affects the parallelism that each tile can handle
Rule 5. Balance tile size, unroll, and vector width: larger tiles need moderate unroll/vectorization; smaller tiles need moderate values to maintain utilization.

Please try to design a best CGRA architecture based on the input kernel characteristics and optimization goal.

Important:
- Return only a valid JSON list, no extra text.
- Ensure the design includes a brief reasoning explaining the choices.
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
    # input
    kernel = "fir"
    DFG_node_counts = {"Add": 4, "Mul": 1, "Ld": 3, "St": 1, "Cmp": 1, "Phi": 1, "Br": 1}
    max_independent_ops_per_cycle = 4
    vectorizable_ops = ["Add", "Mul"]
    optimization_goal = "power"
    model = "qwen-plus"

    print(f"\n=== Iteration 1: Start===\n")
    candidates = SingleAgentBaseline(model=model).design(
        kernel=kernel,
        DFG_node_counts=DFG_node_counts,
        max_independent_ops_per_cycle=max_independent_ops_per_cycle,
        vectorizable_ops=vectorizable_ops,
        optimization_goal=optimization_goal,
        N=1,
    )
    candidates_no_reason = [{k: v for k, v in c.items() if k != "reasoning"} for c in candidates]
    with open("../results/cgra_design_qwen_raw.json", "w") as f:
        json.dump(candidates_no_reason, f, indent=2)

    print("\n✅ Iteration 1(stage 1): SingleAgentBaseline finished, raw JSON saved to cgra_design_qwen_raw.json\n")
