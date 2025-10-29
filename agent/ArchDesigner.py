import requests
from openai import OpenAI
import json
import re
import os

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
        api_key = "xxxxxxxxxxxxxxxxxxxxxxxxxxx"  # Replace with API key
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


def generate_cgra_candidates(
    kernel,
    DFG_node_counts,
    max_independent_ops_per_cycle,
    vectorizable_ops,
    optimization_goal,
    N=5,
    model="gpt-4",
    extra_prompt=None,
    extra_prompt2=None
):
    """
    Use LLM to generate N candidate CGRA designs
    """
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



    content = call_model(model, prompt)
    print(content)
    # Extract JSON part
    json_match = re.search(r"(\[.*\])", content, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
        try:
            candidates = json.loads(json_str)
        except json.JSONDecodeError:
            print("⚠️ Extracted JSON is invalid:")
            print(json_str)
            candidates = []
    else:
        candidates = []

    return candidates


if __name__ == "__main__":
    kernel = {}
    DFG_node_counts = {"Add": 10, "Mul": 5, "Ld": 6, "St": 6, "Cmp": 2}
    max_independent_ops_per_cycle = 4
    vectorizable_ops = ["Add", "Mul"]
    optimization_goal = "performance"

    # Change model here ["gpt-4", "gemma-3.3-27b", "llama-3.3-70b"]
    for model in ["deepseek-chat"]:
        print(f"=== Running {model} ===")
        candidates = generate_cgra_candidates(
            kernel,
            DFG_node_counts,
            max_independent_ops_per_cycle,
            vectorizable_ops,
            optimization_goal,
            N=2,
            model=model
        )
        # Remove reasoning field
        candidates_no_reason = []
        for c in candidates:
            c_copy = {k: v for k, v in c.items() if k != "reasoning"}
            candidates_no_reason.append(c_copy)

        try:
            with open("../results/cgra_candidates_raw.json", "r") as f:
                raw_candidates = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            raw_candidates = []

        raw_candidates.extend(candidates_no_reason)

        with open("../results/cgra_candidates_raw.json", "w") as f:
            json.dump(raw_candidates, f, indent=2)

