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
        api_key = "xxxxxxxxxxxxxxxx"  # 替换为你的API key
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

    else:
        raise ValueError(f"Unsupported model: {model}")



class ExpertJudgeAgent:
    def __init__(self, model="gpt-4"):
        self.model = model

    def judge_designs(self, candidate_designs, optimization_goal="performance", top_k=3):
        """
        使用 LLM 对候选 CGRA design 进行评判并选出 Top-K。
        输出固定为一个 JSON 对象，包括 "top_k_design" 和 "reason"。
        返回值只提取 "top_k_design"。
        """
        prompt = f"""
    You are an expert in CGRA architecture design. 
    I will give you several candidate CGRA designs. 
    Your task is to evaluate them based on the optimization goal: {optimization_goal}.

    Criteria:
    - If goal is 'performance': prefer larger parallelism, vectorization, higher throughput.
    - If goal is 'power': prefer smaller area, lower memory usage, balanced FU count.

    Return in a JSON object with two keys:
    1. "top_k_design": the top-{top_k} designs in a valid JSON list, ordered from best to worst.
    2. "reason": explanation for why these designs were chosen.
    

    Candidate Designs:
    {json.dumps(candidate_designs, indent=2)}

    Important:
    - Return only the JSON object, no extra text.
    - Include everything without omission.
    """

        content = call_model(self.model, prompt, temperature=0.3)
        # print("=======content=======")
        print(content)

        # 匹配最外层的 JSON 对象 {}
        json_match = re.search(r"(\{[\s\S]*\})", content)
        if json_match:
            json_str = json_match.group(1)
            try:
                parsed = json.loads(json_str)
                # 只返回 top_k_design 部分
                topk_arch = parsed.get("top_k_design", [])
            except json.JSONDecodeError:
                print("⚠️ Extracted JSON is invalid:")
                print(json_str)
                topk_arch = []
        else:
            print("⚠️ No JSON found in content:")
            topk_arch = []

        return topk_arch



# ========== 使用示例 ==========
if __name__ == "__main__":
    with open("../results/cgra_candidates_fixed.json", "r") as f:
        candidate_designs = json.load(f)

    # 转成紧凑格式的 JSON 字符串
    candidate_designs_json = json.dumps(candidate_designs, separators=(',', ':'))

    for model in ["gpt-4"]:
        print(f"\n=== Judging with {model} ===")
        judge_agent = ExpertJudgeAgent(model=model)
        top_designs = judge_agent.judge_designs(candidate_designs_json, optimization_goal="performance", top_k=2)
        with open("../results/cgra_top_k.json", "w") as f:
            json.dump(top_designs, f, indent=2)
