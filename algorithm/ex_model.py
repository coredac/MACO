import random
import math
from copy import deepcopy
import json
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "agent")))

from ArchDesigner import generate_cgra_candidates  # Import from parent agent directory
from Mapfixer import map_fixer_llm  # Import from parent agent directory
from Expertjudge import ExpertJudgeAgent  # Import from parent agent directory
from Expertjudge_2 import ExpertJudge2Agent  # Import from parent agent directory
from algorithm2 import DesignSelector
from Heuristic_judge import HeuristicJudge
from algorithm1 import decaying_epsilon_greedy_CGRA

# input
# kernel = "fir"
# DFG_node_counts = {"Add": 4, "Mul": 1, "Ld": 3, "St": 1, "Cmp": 1, "Phi": 1, "Br": 1}
# max_independent_ops_per_cycle = 4
# vectorizable_ops = ["Add", "Mul"]
# optimization_goal = "power"
# model = "qwen-plus-latest"

# kernel = "conv"
# DFG_node_counts = {'Ld': 2, 'St': 0, 'Cmp': 1, 'Phi': 2, 'Br': 1, 'Sel': 0, 'Ret': 0, 'Add': 4, 'Mul': 1, 'Div': 1,'Logic':1}
# max_independent_ops_per_cycle = 4
# vectorizable_ops = ["Add", "Mul"]
# optimization_goal = "power"
# model = "qwen-plus"

kernel = "spmv"
DFG_node_counts = {'Ld': 5, 'St': 1, 'Cmp': 1, 'Phi': 1, 'Br': 1, 'Sel': 0, 'Ret': 0, 'Add': 7, 'Mul': 1, 'Div': 0, 'Logic': 1}
max_independent_ops_per_cycle = 4
vectorizable_ops = ["Add", "Mul"]
optimization_goal = "power"
model = "deepseek-r1-distill-qwen-14b"

# stage 1: Archdesigner
for model in [model]:
    print(f"\n=== Iteration 1: Start===\n")
    candidates = generate_cgra_candidates(
        kernel=kernel,
        DFG_node_counts=DFG_node_counts,
        max_independent_ops_per_cycle=max_independent_ops_per_cycle,
        vectorizable_ops=vectorizable_ops,
        optimization_goal=optimization_goal,
        N=3,
        model=model
    )
    # Remove reasoning field
    candidates_no_reason = []
    for c in candidates:
        c_copy = {k: v for k, v in c.items() if k != "reasoning"}
        candidates_no_reason.append(c_copy)

    with open("../results/cgra_candidates_raw.json", "w") as f:
        json.dump(candidates_no_reason, f, indent=2)

print("\n✅ Iteration 1(stage 1): ArchDesigner finished, raw JSON saved to cgra_candidates_raw.json\n")

# stage 2: Mapfixer

with open("../results/cgra_candidates_raw.json", "r") as f:
    candidates = json.load(f)
    # Process with Mapfixer
    fixed_candidates = map_fixer_llm(
        candidates=candidates,
        kernel=kernel,
        DFG_node_counts=DFG_node_counts,
        max_independent_ops_per_cycle=max_independent_ops_per_cycle,
        vectorizable_ops=vectorizable_ops,
        optimization_goal=optimization_goal,
        model=model
    )

    # Output fixed JSON
    with open("../results/cgra_candidates_fixed.json", "w") as f:
        json.dump(fixed_candidates, f, indent=2)

    print("\n✅ Iteration 1(stage 2): MapFixer finished, fixed JSON saved to cgra_candidates_fixed.json\n")

# stage 3-1: ExpertJudge and ExpertJudge_2
with open("../results/cgra_candidates_fixed.json", "r") as f:
    fixed_candidates = json.load(f)
    fixed_candidates = json.dumps(fixed_candidates, separators=(',', ':'))
# Process with ExpertJudge
judge_agent = ExpertJudgeAgent(model=model)
top_designs = judge_agent.judge_designs(fixed_candidates, optimization_goal=optimization_goal, top_k=2)
with open("../results/cgra_top_k.json", "w") as f:
    json.dump(top_designs, f, indent=2)
print("\n✅ Iteration 1(stage 3-1): ExpertJudge finished, top designs saved to cgra_top_k.json\n")

# stage 3-2: ExpertJudge_2

# No algorithm
# with open("../results/cgra_top_k.json", "r") as f:
#         topk_designs = json.load(f)
# # Convert to compact format JSON string
# topk_designs = json.dumps(topk_designs, separators=(',', ':'))
# judge2_agent = ExpertJudge2Agent(model=model)
# best_design = judge2_agent.select_best(topk_designs, optimization_goal=optimization_goal)
# with open("../results/cgra_best_design.json", "w") as f:
#     json.dump(best_design, f, indent=2)

# with algorithm2
import json
from pathlib import Path

json_files = [
    "../results/cgra_best_design.json",
    "../results/cgra_top_k.json"
]

kernel_path = "/WORK_REPO/CGRA-Flow/CGRA-Mapper/test/kernels/spmv/spmv.c"

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


with open("../results/cgra_top_k.json", "r") as f:
    K_designs = json.load(f)

selector = DesignSelector(model=model)
result = selector.run_once(K_designs, optimization_goal=optimization_goal)
print(result)
# Save history
with open("../results/final_choices.json", "w") as f:
    json.dump(result["final_choice"], f, indent=2)
print("\n✅ Iteration 1(stage 3-2): ExpertJudge_2 with algorithm2 finished, best design saved to final_choices.json\n")

# stage 4: HeuristicJudge
judge = HeuristicJudge(model=model)
candidate_designs = judge.run_test_process()
print("\n✅ Iteration 1(stage 4): HeuristicJudge finished, get the final data and recorded it to the historical data library.\n")
print(f"\n=== Iteration 1: Finished ===\n")
print("✅ Finished the first iteration, Now we need to use the algorithm 1 to decide the next iteration\n")
