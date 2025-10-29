import math 
import json
import sys
import os
from Expertjudge_2 import ExpertJudge2Agent  # 假设这里封装了 LLM_judge / select_best
# 将上一级目录的 agent 加入模块搜索路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "agent")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tool")))
import test_process_candidates  # 假设这里封装了 Tool_judge

def unified_score(design, optimization_goal="performance"):
    """
    统一评分函数
    """
    design = {k: v for k, v in design.items() if k != "id"}  # 去除 id 字段
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
    """计算 LLM 与工具结果的相似度"""
    return math.exp(-abs(llm_score - tool_score) / sigma)


class DesignSelector:
    def __init__(self, model="qwen-plus",
             conf_threshold=0.7,
             validation_interval=5,
             alpha=0.3,
             sigma=0.1):
        self.judge_agent = ExpertJudge2Agent(model=model)

        # 状态（在多次调用时会保留）
        self.conf = 0.0
        self.iteration = 0
        self.prev_feedback = None   # 👈 初始化
        self.LLM_memory = []        # LLM 反馈记忆
        self.history = []           # 保存所有选择过程
        # 在类的 __init__ 里初始化计数器
        self.tool_calls = 0


        # 超参数
        self.conf_threshold = conf_threshold
        self.validation_interval = validation_interval
        self.alpha = alpha
        self.sigma = sigma


    def LLM_update(self, K_designs, llm_choice, tool_choice, optimization_goal="performance"):
        """
        根据 Tool 报告更新 LLM 自学习
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
        执行一次选择（保留状态）
        """
        self.iteration += 1
        print("===iteration===")
        print(self.iteration)
        print("===previous feedback===")
        print(self.prev_feedback)
        print("===conf===")
        print(self.conf)
        # Step 1: LLM 选择
        llm_choice = self.judge_agent.select_best(K_designs, optimization_goal,self.prev_feedback)
        # print(llm_choice)
        llm_score = unified_score(llm_choice, optimization_goal)

        # Step 2: 决定是否调用 Tool
        if self.conf < self.conf_threshold or self.iteration % self.validation_interval == 0:

            tool_report = test_process_candidates.eval_metrics_by_arch(path="../results/cgra_top_k.json")
            # flat_report = [item for sublist in tool_report for item in sublist]

            if optimization_goal == "performance":
                tool_best = max(tool_report, key=lambda d: d.get("speedup", 0))
            elif optimization_goal == "power":
                tool_best = min(tool_report, key=lambda d: d.get("power_consumption (mW)", float("inf")))
            # # 根据 optimization_goal 选择最佳设计
            # if optimization_goal == "performance":
            #     tool_best = max(tool_report, key=lambda d: d.get("speedup", 0))
            # elif optimization_goal == "power":
            #     tool_best = min(tool_report, key=lambda d: d.get("power", float("inf")))
            else:
                # 你也可以用加权或 EDP
                tool_best = max(tool_report, key=lambda d: d.get("speedup", 0)/d.get("power", 1))
            tool_score = unified_score(tool_best, optimization_goal)

            # 更新置信度
            sim = similarity_score(llm_score, tool_score, self.sigma)
            self.conf = self.alpha * sim + (1 - self.alpha) * self.conf

            final_choice = tool_best  # 工具优先
            feedback = self.LLM_update(K_designs, llm_choice, tool_best, optimization_goal)
            self.tool_calls += 1  # 调用次数 +1
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


# ========== 使用示例 ==========
if __name__ == "__main__":
    with open("../results/cgra_top_k.json", "r") as f:
        K_designs = json.load(f)

    selector = DesignSelector()
    for _ in range(3):   # 连续调用三次，状态会保留
        result = selector.run_once(K_designs, optimization_goal="performance")
        print(result)

    # 保存历史
    with open("../results/final_choices.json", "w") as f:
        json.dump(selector.history, f, indent=2)
