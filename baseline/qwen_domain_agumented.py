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
        api_key = "xxxxxxxxxxxxx"  # Replace with your OpenAI API key
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
- tile_size: 2x2 to 4x4 (the tile size should be square, each dimension indicates number of rows and columns of tiles; total tile count = rows * columns, e.g., 2x2 = 4 tiles, 4x4 = 16 tiles)
- FUs: dictionary mapping each tile to a list of supported functional units. Each tile can include any of ["Ld", "St", "Cmp", "Phi", "Br", "Sel", "Ret", "Add", "Mul", "Div", "Logic"]. 
  ⚠️ The FU dictionary must include exactly total_tile_count tiles named sequentially from tile0 to tile total_tile_count - 1.
  For example, if tile_size is 4x4, there are 16 tiles, so they should be named tile0, tile1, ..., tile15.
- config_mem: number of configuration instructions each tile can store (range 8 to 16 instructions)
- data_spm_kb: scratchpad memory in KB (range 4KB to 128KB)
- unroll_factor: loop unroll factor (1 to 6)
- vectorize: one of "all", "interleaved", or "none"
- reasoning: brief explanation why this design fits the input kernel and optimization goal

Example output (JSON list):

[
  {{
    "tile_size": "3x3",
    "FUs": {{"tile0": ["Add"],"tile1": ["Ld", "Add"],"tile2": ["Mul"],"tile3": ["Ld"],"tile4": ["Cmp", "Phi", "Br"],"tile5": ["Logic","Sel","Ret"],"tile6": ["Div"],"tile7": ["St"],"tile8": ["Ld"]}},
    "config_mem": 24,
    "data_spm_kb": 64,
    "unroll_factor": 2,
    "vectorize": "all",
    "reasoning": "Tile-level FU assignment balances computation and memory access; vectorize all Add/Mul for SIMD; config storage sufficient for kernel instructions; control units placed to handle branches and phi nodes."
  }}
]

Domain Knowledge:
1. Control Units Placement: Place control FUs (Cmp, Phi, Br, Sel, Ret) preferably in central tiles for global control and reduced communication delay. In larger arrays, distribute a few control units to avoid bottlenecks.
2. Balance of Compute and Memory: Each tile should ideally include at least one compute FU (Add, Mul, Logic) and one memory FU (Ld, St). Place memory units (Ld, St) near array edges to reduce communication with external memory.
3. Vectorization and Parallelism: If the kernel has many independent operations, replicate compute units (Add, Mul) and enable vectorization ("all" or "interleaved"). Place vectorizable ops on neighboring tiles to support SIMD execution.
4. Configuration Memory (config_mem): Small kernels → fewer instructions (8–10). Complex kernels with loops/branches → larger storage (12–16).
5. Scratchpad Memory (data_spm_kb): Memory-bound kernels benefit from larger scratchpad (64–128KB). Compute-intensive kernels can use smaller scratchpad (8–32KB).
6. Loop Unrolling and Mapping: unroll_factor should match max_independent_ops_per_cycle without exceeding available resources. Typical range: 2–4, maximum 6.
7. Operator Distribution: Add/Mul should be evenly distributed for parallel compute array. Div/Logic are resource-heavy, place sparsely in few tiles. Ld/St should be placed near edges for memory access efficiency. Cmp/Phi/Br/Sel/Ret should be placed centrally for global scheduling.


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
    kernel = "gemm"
    DFG_node_counts = {'Ld': 3, 'St': 1, 'Cmp': 1, 'Phi': 1, 'Br': 1, 'Sel': 0, 'Ret': 0, 'Add': 4, 'Mul': 1, 'Div': 0}
    max_independent_ops_per_cycle = 4
    vectorizable_ops = ["Add", "Mul"]
    optimization_goal = "power"
    model = "qwen-plus"

    # Change model here ["gpt-4", "gemma-3.3-27b", "llama-3.3-70b"]
    for model in ["qwen-plus"]:
        print(f"=== Running {model} ===")
        candidates = generate_cgra_candidates(
            kernel,
            DFG_node_counts,
            max_independent_ops_per_cycle,
            vectorizable_ops,
            optimization_goal,
            N=1,
            model=model
        )
        # Remove reasoning field
        candidates_no_reason = []
        for c in candidates:
            c_copy = {k: v for k, v in c.items() if k != "reasoning"}
            candidates_no_reason.append(c_copy)

        # try:
        #     with open("qwen_domain_augmented_fir.json", "r") as f:
        #         raw_candidates = json.load(f)
        # except (FileNotFoundError, json.JSONDecodeError):
        raw_candidates = []

        raw_candidates.extend(candidates_no_reason)

        with open("qwen_domain_augmented_gemm.json", "w") as f:
            json.dump(raw_candidates, f, indent=2)

