import math
import json
import sys
import os
from Expertjudge_2 import ExpertJudge2Agent  # Assume LLM_judge / select_best is encapsulated here
# Add parent agent directory to module search path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "agent")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tool")))
import test_process_candidates  # Assume Tool_judge is encapsulated here

def unified_score(design, optimization_goal="performance"):
    """
    Unified scoring function
    """
    design = {k: v for k, v in design.items() if k != "id"}  # Remove id field
    if optimization_goal == "performance":
        score = design.get("speedup", 1.0)
        vector_factor = {"none": 0.5, "interleaved": 0.8, "all": 1.0}.get(design.get("vectorize", "none"), 0.7)
        unroll_factor = design.get("unroll_factor", 1) / 6.0
        score = score * 0.7 + vector_factor * 0.2 + unroll_factor * 0.1
    elif optimization_goal in ["energy", "area", "power"]:
        power = design.get("power", 1.0)
        area = design.get("area", 1.0)
        score = 1.0 / (1.0 + power + area)
    else:
        score = 0.0
    return score


def similarity_score(llm_score, tool_score, sigma=0.1):
    """Calculate similarity between LLM and tool results"""
    return math.exp(-abs(llm_score - tool_score) / sigma)


class DesignSelector:
    def __init__(self, model="qwen-plus",
             conf_threshold=0.7,
             validation_interval=5,
             alpha=0.3,
             sigma=0.1):
        self.judge_agent = ExpertJudge2Agent(model=model)

        # State (will be retained across multiple calls)
        self.conf = 0.0
        self.iteration = 0
        self.prev_feedback = None   # Initialize
        self.LLM_memory = []        # LLM feedback memory
        self.history = []           # Save all selection process
        # Initialize counter in class __init__
        self.tool_calls = 0


        # Hyperparameters
        self.conf_threshold = conf_threshold
        self.validation_interval = validation_interval
        self.alpha = alpha
        self.sigma = sigma


    def LLM_update(self, K_designs, llm_choice, tool_choice, optimization_goal="performance"):
        """
        Update LLM self-learning based on Tool report
        """
        if llm_choice == tool_choice:
            feedback = (
                f"Your selection matches the tool's best design. "
                f"Continue selecting the best design based on {optimization_goal}."
            )
        else:
            feedback = (
                f"Your selection differs from the tool's best design.\n"
                f"Tool-best: {tool_choice}\nYour choice: {llm_choice}\n"
                f"Adjust next selection to align with the tool-best design for {optimization_goal}."
            )
        self.LLM_memory.append({
            "optimization_goal": optimization_goal,
            "feedback": feedback,
            "tool_best": tool_choice,
            "llm_choice": llm_choice
        })
        return feedback

    def run_once(self, K_designs, optimization_goal="performance"):
        """
        Perform one selection (retain state)
        """
        self.iteration += 1
        print("===iteration===")
        print(self.iteration)
        print("===previous feedback===")
        print(self.prev_feedback)
        print("===conf===")
        print(self.conf)
        # Step 1: LLM selection
        llm_choice = self.judge_agent.select_best(K_designs, optimization_goal,self.prev_feedback)
        # print(llm_choice)
        llm_score = unified_score(llm_choice, optimization_goal)

        # Step 2: Decide whether to call Tool
        if self.conf < self.conf_threshold or self.iteration % self.validation_interval == 0:

            tool_report = test_process_candidates.eval_metrics_by_arch(path="../results/cgra_top_k.json")
            # flat_report = [item for sublist in tool_report for item in sublist]

            if optimization_goal == "performance":
                tool_best = max(tool_report, key=lambda d: d.get("speedup", 0))
            elif optimization_goal == "power":
                tool_best = min(tool_report, key=lambda d: d.get("power_consumption (mW)", float("inf")))
            # # Select best design based on optimization_goal
            # if optimization_goal == "performance":
            #     tool_best = max(tool_report, key=lambda d: d.get("speedup", 0))
            # elif optimization_goal == "power":
            #     tool_best = min(tool_report, key=lambda d: d.get("power", float("inf")))
            else:
                # Can also use weighted or EDP
                tool_best = max(tool_report, key=lambda d: d.get("speedup", 0)/d.get("power", 1))
            tool_score = unified_score(tool_best, optimization_goal)

            # Update confidence
            sim = similarity_score(llm_score, tool_score, self.sigma)
            self.conf = self.alpha * sim + (1 - self.alpha) * self.conf

            final_choice = tool_best  # Tool priority
            feedback = self.LLM_update(K_designs, llm_choice, tool_best, optimization_goal)
            self.tool_calls += 1  # Call count +1
            print(f"=== tool call #{self.tool_calls} ===")
        else:
            final_choice = llm_choice
            feedback = None

        record = {
            "iteration": self.iteration,
            "final_choice": final_choice,
            "confidence": self.conf,
            "feedback": feedback
        }
        self.prev_feedback = feedback
        self.history.append(record)
        return record


# ========== Usage example ==========
if __name__ == "__main__":
    with open("../results/cgra_top_k.json", "r") as f:
        K_designs = json.load(f)

    selector = DesignSelector()
    for _ in range(3):   # Consecutive calls three times, state will be retained
        result = selector.run_once(K_designs, optimization_goal="performance")
        print(result)

    # Save history
    with open("../results/final_choices.json", "w") as f:
        json.dump(selector.history, f, indent=2)
