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
        api_key = "xxxxxxxxxxxxx"  # 替换为你的API key
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



class ExpertJudge2Agent:
    def __init__(self, model="qwen-plus"):
        self.model = model

    def select_best(self, topk_designs, optimization_goal="performance", feedback=None): 
        """
        使用 LLM 从 top-k 设计中选择最优设计，并返回 best_design 部分。
        输出固定为一个 JSON 对象，包含 "best_design" 和 "reason"。
        """
        feedback_text = f"\nPrevious iteration feedback: {feedback}\n" if feedback else ""

        prompt = f"""
    You are an expert in CGRA architecture design. 
    I will give you several Top-K candidate CGRA designs (already filtered). 
    Now your task is to select the SINGLE best design based on the optimization goal: {optimization_goal}.
    {feedback_text}
    Criteria:
    - If goal is 'performance': prefer larger parallelism, vectorization, higher throughput.
    - If goal is 'power': prefer smaller area, lower memory usage, balanced FU count.

    Return in a JSON object with two keys:
    1. "best_design": the best design in a valid JSON object.
    2. "reason": explanation for why this design was chosen.

    Top-K Designs:
    {json.dumps(topk_designs, indent=2)}

    Important:
    - Return only the JSON object, no extra text.
    - Include everything without omission.
    """

        content = call_model(self.model, prompt, temperature=0.3)
        

        #print("=======content=======")
        print(content)

        # 尝试匹配最外层的 {} JSON 对象
        json_match = re.search(r"(\{[\s\S]*\})", content)
        if json_match:
            json_str = json_match.group(1)
            try:
                parsed = json.loads(json_str)
                # 只返回 best_design 部分
                best_design_arch = parsed.get("best_design", {})
            except json.JSONDecodeError:
                #print("⚠️ Extracted JSON is invalid:")
                best_design_arch = {}
        else:
            #print("⚠️ No JSON found in content:")
            best_design_arch = {}

        return best_design_arch




# ========== 使用示例 ==========
if __name__ == "__main__":
    with open("../results/cgra_top_k.json", "r") as f:
        topk_designs = json.load(f)

    # 转成紧凑格式的 JSON 字符串
    topk_designs = json.dumps(topk_designs, separators=(',', ':'))

    for model in ["gpt-4"]:
        #print(f"\n=== Judging with {model} ===")
        judge_agent = ExpertJudge2Agent(model=model)
        best_design = judge_agent.select_best(topk_designs, optimization_goal="performance")
        with open("../results/cgra_best_design.json", "w") as f:
            json.dump(best_design, f, indent=2)
