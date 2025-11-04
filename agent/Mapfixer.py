import requests
from openai import OpenAI
import json
import re

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
        api_key = "***REVOKED_DASHSCOPE_KEY***"  # Replace with your API key
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



# ================= Validation function =================
def validate_tile_fu(design):
    """
    Validate whether tile_size of single CGRA design matches FU count
    Return report dictionary
    """
    report = {"valid": True, "issues": []}

    if not isinstance(design, dict):
        report["valid"] = False
        report["issues"].append(f"Design is not a dictionary: {design}")
        return report

    try:
        tile_size_str = design.get("tile_size")
        rows, cols = map(int, str(tile_size_str).split("x"))
        if rows != cols:
            report["valid"] = False
            report["issues"].append(f"tile_size {rows}x{cols} is not square")
        if not (2 <= rows <= 8):
            report["valid"] = False
            report["issues"].append(f"tile_size {rows}x{cols} out of range 2x2~8x8")
    except Exception:
        report["valid"] = False
        report["issues"].append(f"tile_size '{design.get('tile_size')}' is invalid")
        rows = cols = None  # Avoid subsequent errors

    fus = design.get("FUs", {})
    expected_tiles = rows * cols if rows and cols else None
    actual_tiles = len(fus) if isinstance(fus, dict) else 0
    if expected_tiles is not None and actual_tiles != expected_tiles:
        report["valid"] = False
        report["issues"].append(f"FU dictionary has {actual_tiles} tiles, expected {expected_tiles}")

    if expected_tiles is not None and isinstance(fus, dict):
        expected_names = [f"tile{i}" for i in range(expected_tiles)]
        missing = [n for n in expected_names if n not in fus]
        extra = [n for n in fus if n not in expected_names]
        if missing:
            report["valid"] = False
            report["issues"].append(f"Missing tiles in FU dictionary: {missing}")
        if extra:
            report["valid"] = False
            report["issues"].append(f"Extra tiles in FU dictionary: {extra}")

    return report



def validate_design_list(designs):
    """
    Batch validation of CGRA design list
    """
    reports = []
    for i, d in enumerate(designs):
        r = validate_tile_fu(d)
        r["design_index"] = i
        reports.append(r)
    # print(reports)
    return reports


# ================= MapFixer LLM =================
def map_fixer_llm(candidates, kernel, DFG_node_counts, max_independent_ops_per_cycle,
                   vectorizable_ops, optimization_goal, model="gpt-4"):
    """
    Use LLM to fix CGRA design
    """
    reports = validate_design_list(candidates)

    prompt = f"""
You are an expert CGRA architect and MapFixer.

You are given a list of CGRA candidate designs and a validation report.
Some designs may have inconsistencies:
- tile_size may be invalid (not square or outside 2x2~8x8)
- FU dictionaries may have missing or extra tiles, or tile names not matching tile_size
- Other parameters (config_mem, data_spm_kb, unroll_factor, vectorize) may need minor adjustment

Input:
kernel={kernel}
DFG_node_counts={DFG_node_counts}
max_independent_ops_per_cycle={max_independent_ops_per_cycle}
vectorizable_ops={vectorizable_ops}
optimization_goal="{optimization_goal}"

Candidates:
{json.dumps(candidates, separators=(',', ':'))}


Validation Report:
{json.dumps(reports, separators=(',', ':'))}

Task:
Fix the following CGRA candidate designs based on the validation report.
Return in a JSON object with two keys:
1. "fixed_arch_json": the valid JSON list of designs. 
2. "reason": explanation for why each modification was made.
"""
    content = call_model(model, prompt)
    print(content)
    # Extract JSON part
    # json_match = re.search(r"(\[.*\])", content, re.DOTALL)
    json_match = re.search(r"(\{[\s\S]*\})", content)
    if json_match:
        json_str = json_match.group(1)
        try:
            parsed = json.loads(json_str)
            fixed_candidates = parsed.get("fixed_arch_json", [])
        except json.JSONDecodeError:
            print("⚠️ Extracted JSON is invalid:")
            print(json_str)
            fixed_candidates = []
    else:
        # print(content)
        fixed_candidates = []

    return fixed_candidates


if __name__ == "__main__":
    # Read LLM generated JSON from file
    with open("../results/cgra_candidates_raw.json", "r") as f:
        candidates = json.load(f)

    kernel = {}
    DFG_node_counts = {"Add": 10, "Mul": 5, "Ld": 6, "St": 6, "Cmp": 2}
    max_independent_ops_per_cycle = 4
    vectorizable_ops = ["Add", "Mul"]
    optimization_goal = "performance"

    fixed_candidates = map_fixer_llm(
        candidates,
        kernel,
        DFG_node_counts,
        max_independent_ops_per_cycle,
        vectorizable_ops,
        optimization_goal,
        model="gpt-4"
    )

    try:
        with open("../results/cgra_candidates_fixed.json", "r") as f:
            candidates = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        candidates = []  # If file does not exist or is corrupted, create a new list

    # 2. Append data
    candidates.extend(fixed_candidates)

    # Output fixed JSON
    with open("../results/cgra_candidates_fixed.json", "w") as f:
        json.dump(candidates, f, indent=2)

    print("✅ MapFixer finished, fixed JSON saved to cgra_candidates_fixed.json")
