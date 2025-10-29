import json
import subprocess
import os
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


class HeuristicJudge:
    def __init__(self, model="gpt-4"):
        self.model = model

    def run_test_process(self):
        """
        调用上级目录 tool/test_process_candidates.py 脚本
        并获取输出的 candidate designs
        """
        script_path = os.path.join("..", "tool", "test_process_candidates.py")
        result = subprocess.run(
            ["python", script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return result

    def load_historical_data(self, json_path="cgra_historical_design.json"):
        """
        打开历史 design 数据
        """
        if not os.path.exists(json_path):
            return []
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def judge(self, candidate_designs, historical_data, optimization_goal="performance", top_k=3):
        """
        用 LLM 评判候选 designs，参考历史数据给出提示
        """
        prompt = f"""
You are an expert in CGRA architecture design. 
You need to evaluate candidate designs based on the optimization goal: {optimization_goal}.

Criteria:
- If goal is 'performance': prefer larger parallelism, vectorization, higher throughput.
- If goal is 'power': prefer smaller area, lower memory usage, balanced FU count.

Historical Designs (for reference):
{json.dumps(historical_data, indent=2)}

Candidate Designs:
{json.dumps(candidate_designs, indent=2)}

Return in a JSON object with two keys:
1. "top_k_design": the top-{top_k} designs in a valid JSON list, ordered from best to worst.
2. "reason": explanation for why these designs were chosen.

Important:
- Return only the JSON object, no extra text.
- Include everything without omission.
"""
        content = call_model(self.model, prompt, temperature=0.3)

        try:
            result_json = json.loads(content)
            return result_json["top_k_design"], result_json.get("reason", "")
        except Exception as e:
            raise ValueError(f"LLM output is not valid JSON: {content}") from e


if __name__ == "__main__":
    judge = HeuristicJudge(model="gpt-4")

    # Step 1: 获取候选设计
    candidate_designs = judge.run_test_process()

    # # Step 2: 读取历史数据
    # historical_data = judge.load_historical_data()

    # # Step 3: 调用模型进行评判
    # top_designs, reason = judge.judge(candidate_designs, historical_data, optimization_goal="performance", top_k=3)

    # print("Top Designs:", top_designs)
    # print("Reason:", reason)
