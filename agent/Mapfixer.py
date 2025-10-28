import requests
from openai import OpenAI
import json
import re

def call_model(model, prompt, temperature=0.7):
    """
    统一模型调用函数，支持多种模型
    
    Args:
        model: 模型名称，支持 "gpt-4", "gpt-4o", "deepseek-chat", "deepseek-coder" 等
        prompt: 用户输入的提示词
        temperature: 生成温度，默认0.7
        api_key: API key (DeepSeek 或 OpenAI 的)，调用官方 API 时必需
    
    Returns:
        str: 模型生成的响应内容
    """
    if 1:
        api_key = "***REVOKED_DASHSCOPE_KEY***"  # 替换为你的 OpenAI API key
        try:
            client = OpenAI(
                # 若没有配置环境变量，请用阿里云百炼API Key将下行替换为：api_key="sk-xxx",
                api_key=api_key,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            )

            response = client.chat.completions.create(
                model=model,  # 模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
                messages=[
                    {"role": "system", "content": "You are an expert CGRA architecture designer."},
                    {"role": "user", "content": prompt}
                    ]
            )
            # print(response.choices[0].message.content)
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"错误信息：{e}")
            print("请参考文档：https://help.aliyun.com/zh/model-studio/developer-reference/error-code")

    # # DeepSeek 模型调用
    # if model.startswith("deepseek"):
    #     api_key = "sk-ca05d18a252d4d58ac40d174511c0a66"  # 替换为你的 DeepSeek API key
    #     if not api_key:
    #         raise ValueError(f"API key is required for {model} model")

    #     client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    #     response = client.chat.completions.create(
    #         model=model,
    #         messages=[
    #             {"role": "system", "content": "You are an expert CGRA architecture designer."},
    #             {"role": "user", "content": prompt},
    #         ],
    #         stream=False 
    #     )
    #     return response.choices[0].message.content.strip()

    # # OpenAI GPT 调用（官方 key）
    # elif model.startswith("gpt-"):
    #     api_key = "sk-nxUri1PbN8uBeg33ha1I50xADwD54Ny2sse1TSLVEJzAI1jG"  # 替换为你的 OpenAI API key
    #     if not api_key:
    #         raise ValueError("API key is required for OpenAI GPT models")
    #     try:
    #         client = OpenAI(api_key=api_key,
    #         base_url="https://api.chatanywhere.tech/v1"  # 指定转发的 Host
    #         )
    #         response = client.chat.completions.create(
    #             model=model,
    #             messages=[
    #                 {"role": "system", "content": "You are an expert CGRA architecture designer."},
    #                 {"role": "user", "content": prompt}
    #             ],
    #             temperature=temperature,
    #         )
    #         return response.choices[0].message.content.strip()
    #     except Exception as e:
    #         print(f"[OpenAI GPT API 错误] {e}")
    #         return None
    
    # # Qwen 调用（官方 key）
    # elif model.startswith("qwen"):
    #     api_key = "sk-0a2e93f069244076a8dced2a2c5256dd"  # 替换为你的 OpenAI API key
    #     try:
    #         client = OpenAI(
    #             # 若没有配置环境变量，请用阿里云百炼API Key将下行替换为：api_key="sk-xxx",
    #             api_key=api_key,
    #             base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    #         )

    #         response = client.chat.completions.create(
    #             model="qwen-plus",  # 模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
    #             messages=[
    #                 {"role": "system", "content": "You are an expert CGRA architecture designer."},
    #                 {"role": "user", "content": prompt}
    #                 ]
    #         )
    #         # print(response.choices[0].message.content)
    #         return response.choices[0].message.content.strip()
    #     except Exception as e:
    #         print(f"错误信息：{e}")
    #         print("请参考文档：https://help.aliyun.com/zh/model-studio/developer-reference/error-code")

    else:
        raise ValueError(f"Unsupported model: {model}")



# ================= 校验函数 =================
def validate_tile_fu(design):
    """
    校验单个 CGRA design 的 tile_size 与 FU 数量是否匹配
    返回 report 字典
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
        rows = cols = None  # 避免后续报错

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
    批量校验 CGRA design list
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
    使用 LLM 修复 CGRA design
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
    # 提取 JSON 部分
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
    # 从文件读取 LLM 生成的 JSON
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
        candidates = []  # 如果文件不存在或坏了，就新建一个 list

    # 2. 追加数据
    candidates.extend(fixed_candidates)

    # 输出修复后的 JSON
    with open("../results/cgra_candidates_fixed.json", "w") as f:
        json.dump(candidates, f, indent=2)

    print("✅ MapFixer finished, fixed JSON saved to cgra_candidates_fixed.json")
