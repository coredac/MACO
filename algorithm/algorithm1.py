import random
import math
from copy import deepcopy
import json
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "agent")))

from ArchDesigner import generate_cgra_candidates  # 从上级 agent 目录导入
from Mapfixer import map_fixer_llm  # 从上级 agent 目录导入
from Expertjudge import ExpertJudgeAgent  # 从上级 agent 目录导入
from algorithm2 import DesignSelector 
from Heuristic_judge import HeuristicJudge
from pathlib import Path


def LLM_generate_exploration(K_designs, N_candidates=1, kernel="fir", DFG_node_counts={"Add": 10, "Mul": 5, "Ld": 6, "St": 6, "Cmp": 2}, max_independent_ops_per_cycle=4,
                             vectorizable_ops=["Add", "Mul"], optimization_goal="performance", feedback=True, model="qwen-plus", output_path="../results/cgra_candidates_raw.json"):
    """
    LLM 探索模式生成新设计，结合历史反馈和优化目标进行大胆探索
    """
    # 尝试加载历史设计
    try:
        with open("../results/cgra_historical_design.json", "r") as f:
            historical_designs = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        historical_designs = []

    # 将 feedback 与历史设计合并，用于提示 LLM
    if feedback:
        historical_designs.append(feedback)
        prompt_feedback = (
            "Historical designs and feedback from previous iterations are provided below. "
            "Use this information to avoid repeating poor design choices and to learn from past improvements:\n"
            f"{historical_designs}\n"
        )

    # 探索提示
    exploration_hint = (
        "Exploration hint: Generate bold design variations that may differ from previous designs."
    )
    # 调用 generate_cgra_candidates 生成新设计
    candidates = generate_cgra_candidates(
        kernel=kernel,
        DFG_node_counts=DFG_node_counts,
        max_independent_ops_per_cycle=max_independent_ops_per_cycle,
        vectorizable_ops=vectorizable_ops,
        optimization_goal=optimization_goal,
        N=N_candidates,  # 只生成一个探索设计
        model=model,
        extra_prompt=f"{prompt_feedback}",
        extra_prompt2=f"{exploration_hint}"
    )

    # 如果 LLM 生成失败，回退到随机设计
    if not candidates:
        candidates = [deepcopy(random.choice(K_designs))]

    # 尝试读取已有文件
    # try:
    #     with open(output_path, "r") as f:
    #         raw_candidates = json.load(f)
    # except (FileNotFoundError, json.JSONDecodeError):
    #     raw_candidates = []

    # 去掉 reasoning 字段，保持结构一致
    candidates_no_reason = []
    for c in candidates:
        c_copy = {k: v for k, v in c.items() if k != "reasoning"}
        candidates_no_reason.append(c_copy)

    # raw_candidates.extend(candidates_no_reason)

    # 写入文件
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(candidates_no_reason, f, indent=2)

    return candidates

import json

def get_historical_best(design_path="../results/cgra_historical_design.json", optimization_goal=None):
    """
    从历史设计中选择最优设计
    metric: "speedup" 或 "power/speedup" 等
    """
    try:
        with open(design_path, "r") as f:
            designs = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

    if not designs:
        return None

    # 根据指定指标选择最优设计
    if optimization_goal == "speedup":
        historical_best = max(designs, key=lambda x: x.get("speedup", 0))
    elif optimization_goal == "power":
        # 较小的 power 比值优先
        historical_best = min(designs, key=lambda x: x.get("power", 1))
    else:
        historical_best = designs[0]

    return historical_best


def LLM_generate_exploitation(K_designs, N_candidates=1, kernel="fir", DFG_node_counts={"Add": 10, "Mul": 5, "Ld": 6, "St": 6, "Cmp": 2}, max_independent_ops_per_cycle=4,
                             vectorizable_ops=["Add", "Mul"], optimization_goal="performance", feedback=True, model="qwen-plus", output_path="../results/cgra_candidates_raw.json"):
    """
    LLM 利用模式生成新设计，只参考历史最佳设计进行优化
    """
    # 历史最佳设计提示
    prompt_feedback = ""
    historical_best = get_historical_best("../results/cgra_historical_design.json", optimization_goal)
    if historical_best:
        prompt_feedback = (
            f"Use the following historical best CGRA design as reference to optimize {optimization_goal}:\n"
            f"{historical_best}\n"
        )

    optimization_hint = (
        "Optimization hint: Generate a design that improves upon the historical best design "
        f"with respect to the optimization goal '{optimization_goal}'. Avoid degrading previous improvements."
    )

    # 调用 generate_cgra_candidates 生成新设计
    candidates = generate_cgra_candidates(
        kernel=kernel,
        DFG_node_counts=DFG_node_counts,
        max_independent_ops_per_cycle=max_independent_ops_per_cycle,
        vectorizable_ops=vectorizable_ops,
        optimization_goal=optimization_goal,
        N=N_candidates,  # 只生成一个 exploitation 设计
        model=model,
        extra_prompt=f"{prompt_feedback}",
        extra_prompt2=f"{optimization_hint}"
    )
    

    # 如果 LLM 生成失败，回退到随机选择
    if not candidates:
        candidates = [deepcopy(random.choice(K_designs))]


    # 去掉 reasoning 字段
    candidates_no_reason = [{k: v for k, v in c.items() if k != "reasoning"} for c in candidates]


    # 写入文件
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(candidates_no_reason, f, indent=2)

    return candidates


def select_best_candidate(candidates, strategy="heuristic"):
    """从候选设计中选出最终设计"""
    # 简单示例：按统一评分选出最高的
    return max(candidates, key=lambda d: unified_score(d))

def unified_score(design, optimization_goal="performance"):
    """统一评分函数"""
    design = {k: v for k, v in design.items() if k != "id"}  # 去掉 id
    if optimization_goal == "performance":
        vector_factor = {"none": 0.5, "interleaved": 0.8, "all": 1.0}.get(design.get("vectorize", "none"), 0.7)
        unroll_factor = design.get("unroll_factor", 1) / 6.0
        speedup = design.get("speedup", 1.0)
        score = speedup * 0.7 + vector_factor * 0.2 + unroll_factor * 0.1
    elif optimization_goal in ["energy", "area"]:
        power = design.get("power", 1.0)
        area = design.get("area", 1.0)
        score = 1.0 / (1.0 + power + area)
    else:
        score = 0.0
    return score

def update_design_pool(prev_pool, D_final):
    """更新设计池，可根据策略替换"""
    new_pool = deepcopy(prev_pool)
    new_pool.append(D_final)
    return new_pool

def get_reward_from_historical(D_final, historical_data, optimization_goal="performance"):
    """
    从历史数据中找到 D_final 对应的 reward
    optimization_goal: "performance" -> speedup
                       "energy" -> power（可改成功耗相关指标）
    """
    for d in historical_data:
        # 完全匹配所有关键字段
        fields = ["tile_size", "FUs", "config_mem", "data_spm_kb", "unroll_factor", "vectorize"]
        match = True
        for f in fields:
            if f == "FUs":
                if d[f].keys() != D_final[f].keys():
                    match = False
                    break
                for k in d[f].keys():
                    if sorted(d[f][k]) != sorted(D_final[f][k]):
                        match = False
                        break
            else:
                if d[f] != D_final[f]:
                    match = False
                    break
        if match:
            if optimization_goal == "performance":
                return d.get("speedup", 1.0)  # 默认 1.0
            elif optimization_goal == "power":
                power = d.get("power", 500.0)  # 默认 500 mW
                # 合理缩放到大约 1~6 区间，例如 power 越小 reward 越大
                # 这里假设功耗范围 ~100~1000 mW
                reward = (1000.0 / max(power, 1.0))  # ~6 对应 100 mW, ~0.6 对应 1000 mW
                return reward
    # 如果历史里没找到，返回默认值
    return 1.0


def extract_strategy(design):
    """从设计中提取策略，用于 Q_type='strategy'"""
    return design.get("strategy", "default")

# ==================== 算法实现 ====================
def decaying_epsilon_greedy_CGRA(K_designs_init,
                                 epsilon_0=0.9,
                                 gamma=0.95,
                                 alpha=0.3,
                                 Q_type="design",
                                 N_candidates=5,
                                 max_iterations=20,
                                 optimization_goal="performance",
                                 kernel={},
                                 DFG_node_counts={},
                                 max_independent_ops_per_cycle=4,
                                 vectorizable_ops=["Add", "Mul"],
                                 model="qwen-plus"
                                 ):
    t = 0
    Q = {}  # Q-values
    C = []  # 记录最终选择

    K_designs = deepcopy(K_designs_init)
    selector = DesignSelector()
    while t < max_iterations:
        t += 1
        epsilon_t = epsilon_0 * (gamma ** t)
        print(f"\n=== Iteration {t+1}: Start===\n")
        # Step 1: Generate N_candidates designs using epsilon-greedy
        candidates = []
        # for _ in range(N_candidates):
        if random.random() < epsilon_t:
            D_new = LLM_generate_exploration(K_designs=K_designs,N_candidates=N_candidates, kernel=kernel, 
                                             DFG_node_counts=DFG_node_counts, max_independent_ops_per_cycle=max_independent_ops_per_cycle, 
                                             vectorizable_ops=vectorizable_ops,model=model,optimization_goal=optimization_goal)
        else:
                # if Q_type == "strategy":
                #     S_best = max(Q, key=Q.get) if Q else None
                #     D_new = LLM_generate_exploitation(S_best)
                # else:
            D_best = max(Q, key=Q.get) if Q else None
            D_new = LLM_generate_exploitation(K_designs=D_best,N_candidates=N_candidates, kernel=kernel, 
                                             DFG_node_counts=DFG_node_counts, max_independent_ops_per_cycle=max_independent_ops_per_cycle, 
                                             vectorizable_ops=vectorizable_ops,model=model,optimization_goal=optimization_goal)
        candidates.append(D_new)

        print(f"\n✅ Iteration {t+1}(stage 1): ArchDesigner finished, raw JSON saved to cgra_candidates_raw.json\n")

        # Step 2: Select a single design to evaluate and keep
        # stage2
        with open("../results/cgra_candidates_raw.json", "r") as f:
            candidates_raw = json.load(f)


        fixed_candidates = map_fixer_llm(
            candidates_raw,
            kernel=kernel,
            DFG_node_counts=DFG_node_counts,
            max_independent_ops_per_cycle=max_independent_ops_per_cycle,
            vectorizable_ops=vectorizable_ops,
            optimization_goal=optimization_goal,
            model=model
        )
        # 输出修复后的 JSON
        with open("../results/cgra_candidates_fixed.json", "w") as f:
            json.dump(candidates, f, indent=2)

        print(f"\n✅ Iteration {t+1}(stage 2): MapFixer finished, fixed JSON saved to cgra_candidates_fixed.json\n")

        #stage3-1
        with open("../results/cgra_candidates_fixed.json", "r") as f:
            candidate_designs = json.load(f)

        # 转成紧凑格式的 JSON 字符串
        candidate_designs_json = json.dumps(candidate_designs, separators=(',', ':'))

        for model in [model]:
            print(f"\n=== Judging with {model} ===")
            judge_agent = ExpertJudgeAgent(model=model)
            top_designs = judge_agent.judge_designs(candidate_designs_json, optimization_goal=optimization_goal, top_k=2)
            with open("../results/cgra_top_k.json", "w") as f:
                json.dump(top_designs, f, indent=2)

        print(f"\n✅ Iteration {t+1}(stage 3-1): ExpertJudge finished, top designs saved to cgra_top_k.json\n")

        json_files = [
            "../results/cgra_best_design.json",
            "../results/cgra_top_k.json"
        ]

        kernel_path = "/WORK_REPO/CGRA-Flow/CGRA-Mapper/test/kernels/fir/fir.cpp"

        for file_path in json_files:
            path = Path(file_path)
            if not path.exists():
                print(f"文件不存在: {file_path}")
                continue

            # 读取原 JSON
            with open(path, "r") as f:
                designs = json.load(f)

            # 如果是单个 dict，包装成列表
            if isinstance(designs, dict):
                designs = [designs]
                single_object = True
            else:
                single_object = False

            # 给每个设计加上 kernel 字段
            for design in designs:
                if isinstance(design, dict):
                    design["kernel"] = kernel_path
                else:
                    print(f"跳过非字典条目: {design}")

            # 如果原本是单个对象，保存回去时解包成 dict
            save_data = designs[0] if single_object else designs

            # 保存回原文件
            with open(path, "w") as f:
                json.dump(save_data, f, indent=4)

            print(f"已更新 {file_path}，每个设计添加 kernel 字段")


        #stage 3-2
        with open("../results/cgra_top_k.json", "r") as f:
            K_designs = json.load(f)
        result = selector.run_once(K_designs, optimization_goal=optimization_goal)
        print(result)
        # 保存历史
        # with open("../results/final_choices.json", "w") as f:
        #     json.dump(result["final_choice"], f, indent=2)
        path = "../results/final_choices.json"

        # 如果文件已存在，先读出来，否则用空list
        if os.path.exists(path):
            with open(path, "r") as f:
                data = json.load(f)
        else:
            data = {}

        # 用 iteration 或 tool_calls 或时间戳做 key
        key = f"choice_{len(data) + 1}"
        data[key] = result["final_choice"]

        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"\n✅ Iteration {t+1}(stage 3-2): ExpertJudge_2 with algorithm2 finished, best design saved to final_choices.json\n")
        D_final = result["final_choice"]

        # stage 4: HeuristicJudge
        judge = HeuristicJudge(model=model)
        candidate_designs = judge.run_test_process()
        print(f"\n✅ Iteration {t+1}(stage 4): HeuristicJudge finished, get the final data and recorded it to the historical data library.\n")
        print(f"\n=== Iteration {t+1}: Finished ===\n")


        # Step 3: Evaluate the selected design
        historical_file = "../results/cgra_historical_design.json"
        if os.path.exists(historical_file):
            with open(historical_file, "r") as f:
                historical_data = json.load(f)
        else:
            historical_data = []
        print(D_final)
        r_final = get_reward_from_historical(D_final, historical_data, optimization_goal)

        # Step 4: Update Q-value
        # if Q_type == "strategy":
        #     S_used = extract_strategy(D_final)
        #     Q[S_used] = (1 - alpha) * Q.get(S_used, 0) + alpha * r_final
        # else:
        D_key = str(D_final)  # 可序列化作为字典 key
        Q[D_key] = (1 - alpha) * Q.get(D_key, 0) + alpha * r_final

        # Step 5: Record final choice and reward
        C.append({
            "iteration": t,
            "design": D_final,
            "reward": r_final,
            "epsilon": epsilon_t
        })

        # Step 6: Update design pool
        K_designs = update_design_pool(K_designs, D_final)

    return C

# ==================== 示例运行 ====================
if __name__ == "__main__":
    # 构造 K_designs 示例
    with open("../results/cgra_historical_design.json", "r") as f:
        historical_data = json.load(f)

    # 提取 K_designs，保留所有关键字段
    K_designs = []
    for d in historical_data:
        K_designs.append({
            "tile_size": d["tile_size"],
            "FUs": d["fu_counts"],
            "config_mem": d.get("config_mem", 128),
            "data_spm_kb": d.get("data_spm_kb", 64),
            "unroll_factor": d.get("unroll_factor", 1),
            "vectorize": d.get("vectorize", "none"),
            "speedup": d.get("speedup", 1.0),
            "power": d.get("power", 1.0)
        })

    results = decaying_epsilon_greedy_CGRA(K_designs,
                                            epsilon_0=0.9,
                                            gamma=0.95,
                                            alpha=0.3,
                                            Q_type="design",
                                            N_candidates=3,
                                            max_iterations=2,
                                            optimization_goal="performance")
    for r in results:
        print(f"Iter {r['iteration']}, Reward: {r['reward']:.3f}, Epsilon: {r['epsilon']:.3f}")
