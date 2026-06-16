"""Stage-2 agent: CGRA Fixer.

Implements the rule-driven repair mechanism described in
MACO Sec. III-C (Stage 2: Validation & Correction).
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


def validate_tile_fu(design):
    """Validate whether tile_size of a single CGRA design matches FU count."""
    report = {"valid": True, "issues": []}

    if not isinstance(design, dict):
        report["valid"] = False
        report["issues"].append(f"Design is not a dictionary: {design}")
        return report

    rows = cols = None
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
    """Batch validation of a CGRA design list."""
    reports = []
    for i, d in enumerate(designs):
        r = validate_tile_fu(d)
        r["design_index"] = i
        reports.append(r)
    return reports


class CGRAFixer:
    """Stage-2 agent that repairs syntax / mapping errors via rule-driven LLM prompting."""

    def __init__(self, model="qwen-plus"):
        self.model = model

    def repair(
        self,
        candidates,
        kernel,
        DFG_node_counts,
        max_independent_ops_per_cycle,
        vectorizable_ops,
        optimization_goal,
    ):
        """Validate each candidate and ask the LLM to repair invalid ones."""
        reports = validate_design_list(candidates)

        prompt = f"""
You are an expert CGRA architect and CGRA Fixer.

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
        content = call_model(self.model, prompt)
        print(content)
        json_match = re.search(r"(\{[\s\S]*\})", content)
        if json_match:
            try:
                parsed = json.loads(json_match.group(1))
                return parsed.get("fixed_arch_json", [])
            except json.JSONDecodeError:
                print("⚠️ Extracted JSON is invalid:")
                print(json_match.group(1))
        return []


if __name__ == "__main__":
    with open("../results/cgra_candidates_raw.json", "r") as f:
        candidates = json.load(f)

    fixer = CGRAFixer(model="qwen-plus")
    fixed_candidates = fixer.repair(
        candidates=candidates,
        kernel={},
        DFG_node_counts={"Add": 10, "Mul": 5, "Ld": 6, "St": 6, "Cmp": 2},
        max_independent_ops_per_cycle=4,
        vectorizable_ops=["Add", "Mul"],
        optimization_goal="performance",
    )

    try:
        with open("../results/cgra_candidates_fixed.json", "r") as f:
            existing = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        existing = []
    existing.extend(fixed_candidates)

    with open("../results/cgra_candidates_fixed.json", "w") as f:
        json.dump(existing, f, indent=2)
    print("✅ CGRAFixer finished, fixed JSON saved to cgra_candidates_fixed.json")
