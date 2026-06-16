"""Per-kernel MACO experiment driver.

Runs the four-stage MACO flow end-to-end (including the DC-tools-backed
ConfidenceAdaptiveSelector) for a single kernel — used to reproduce the
per-domain results in the paper's evaluation.
"""

import json
import sys
import os
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(_HERE, "agent"))
sys.path.append(os.path.join(_HERE, "algorithm"))

from cgra_codesigner import CGRACoDesigner
from cgra_fixer import CGRAFixer
from coarse_grained_judge import CoarseGrainedJudge
from confidence_adaptive_selector import ConfidenceAdaptiveSelector

# input
kernel = "fir"
DFG_node_counts = {"Add": 4, "Mul": 1, "Ld": 3, "St": 1, "Cmp": 1, "Phi": 1, "Br": 1}
max_independent_ops_per_cycle = 4
vectorizable_ops = ["Add", "Mul"]
optimization_goal = "power"
model = "qwen-plus-latest"

# Stage 1: CGRA Co-designer
print(f"\n=== Iteration 1: Start===\n")
candidates = CGRACoDesigner(model=model).design(
    kernel=kernel,
    DFG_node_counts=DFG_node_counts,
    max_independent_ops_per_cycle=max_independent_ops_per_cycle,
    vectorizable_ops=vectorizable_ops,
    optimization_goal=optimization_goal,
    N=3,
)
candidates_no_reason = [{k: v for k, v in c.items() if k != "reasoning"} for c in candidates]
with open("results/cgra_candidates_raw.json", "w") as f:
    json.dump(candidates_no_reason, f, indent=2)
print("\n✅ Iteration 1(stage 1): CGRACoDesigner finished, raw JSON saved to cgra_candidates_raw.json\n")

# Stage 2: CGRA Fixer
with open("results/cgra_candidates_raw.json", "r") as f:
    candidates = json.load(f)
fixed_candidates = CGRAFixer(model=model).repair(
    candidates=candidates,
    kernel=kernel,
    DFG_node_counts=DFG_node_counts,
    max_independent_ops_per_cycle=max_independent_ops_per_cycle,
    vectorizable_ops=vectorizable_ops,
    optimization_goal=optimization_goal,
)
with open("results/cgra_candidates_fixed.json", "w") as f:
    json.dump(fixed_candidates, f, indent=2)
print("\n✅ Iteration 1(stage 2): CGRAFixer finished, fixed JSON saved to cgra_candidates_fixed.json\n")

# Stage 3a: Coarse-grained Judge top-K screen
with open("results/cgra_candidates_fixed.json", "r") as f:
    fixed_candidates = json.load(f)
fixed_candidates = json.dumps(fixed_candidates, separators=(',', ':'))
top_designs = CoarseGrainedJudge(model=model).judge(fixed_candidates, optimization_goal=optimization_goal, top_k=2)
with open("results/cgra_top_k.json", "w") as f:
    json.dump(top_designs, f, indent=2)
print("\n✅ Iteration 1(stage 3-1): CoarseGrainedJudge finished, top designs saved to cgra_top_k.json\n")

# Stage 3b: Fine-grained Judge + Confidence-Adaptive Selection
json_files = [
    "results/cgra_best_design.json",
    "results/cgra_top_k.json"
]

kernel_path = "/WORK_REPO/CGRA-Flow/CGRA-Mapper/test/kernels/fir/fir.cpp"

for file_path in json_files:
    path = Path(file_path)
    if not path.exists():
        print(f"File does not exist: {file_path}")
        continue

    # Read original JSON
    with open(path, "r") as f:
        designs = json.load(f)

    # If single dict, wrap into list
    if isinstance(designs, dict):
        designs = [designs]
        single_object = True
    else:
        single_object = False

    # Add kernel field to each design
    for design in designs:
        if isinstance(design, dict):
            design["kernel"] = kernel_path
        else:
            print(f"Skip non-dictionary entry: {design}")

    # If originally a single object, unpack to dict when saving back
    save_data = designs[0] if single_object else designs

    # Save back to original file
    with open(path, "w") as f:
        json.dump(save_data, f, indent=4)

    print(f"Updated {file_path}, added kernel field to each design")


with open("results/cgra_top_k.json", "r") as f:
    K_designs = json.load(f)

selector = ConfidenceAdaptiveSelector(model=model)
result = selector.run_once(K_designs, optimization_goal=optimization_goal)
print(result)
with open("results/final_choices.json", "w") as f:
    json.dump(result["final_choice"], f, indent=2)
print("\n✅ Iteration 1(stage 3-2): FineGrainedJudge + ConfidenceAdaptiveSelector finished, best design saved to final_choices.json\n")
print(f"\n=== Iteration 1: Finished ===\n")
