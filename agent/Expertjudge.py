import requests
from openai import OpenAI
import json
import re

def call_model(model, prompt, temperature=0.7):
    """
    Unified model calling function, supports multiple models

    Args:
        model: Model name, supports "gpt-4", "gpt-4o", "deepseek-chat", "deepseek-coder", etc.
        prompt: User input prompt
        temperature: Generation temperature, default 0.7
        api_key: API key (DeepSeek or OpenAI), required when calling official API

    Returns:
        str: Model generated response content
    """
    if 1:
        api_key = "***REVOKED_DASHSCOPE_KEY***"  # Replace with your API key
        try:
            client = OpenAI(
                # If environment variable is not configured, replace the following line with Alibaba Cloud API Key: api_key="sk-xxx",
                api_key=api_key,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            )

            response = client.chat.completions.create(
                model=model,  # Model list: https://help.aliyun.com/zh/model-studio/getting-started/models
                messages=[
                    {"role": "system", "content": "You are an expert CGRA architecture designer."},
                    {"role": "user", "content": prompt}
                    ]
            )
            # print(response.choices[0].message.content)
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error message: {e}")
            print("Please refer to the documentation: https://help.aliyun.com/zh/model-studio/developer-reference/error-code")

    else:
        raise ValueError(f"Unsupported model: {model}")



class ExpertJudgeAgent:
    def __init__(self, model="gpt-4"):
        self.model = model

    def judge_designs(self, candidate_designs, optimization_goal="performance", top_k=3):
        """
        Use LLM to evaluate candidate CGRA designs and select Top-K.
        Output is fixed as a JSON object, including "top_k_design" and "reason".
        Return value only extracts "top_k_design".
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

        # Match outermost JSON object {}
        json_match = re.search(r"(\{[\s\S]*\})", content)
        if json_match:
            json_str = json_match.group(1)
            try:
                parsed = json.loads(json_str)
                # Only return top_k_design part
                topk_arch = parsed.get("top_k_design", [])
            except json.JSONDecodeError:
                print("⚠️ Extracted JSON is invalid:")
                print(json_str)
                topk_arch = []
        else:
            print("⚠️ No JSON found in content:")
            topk_arch = []

        return topk_arch



# ========== Usage example ==========
if __name__ == "__main__":
    with open("../results/cgra_candidates_fixed.json", "r") as f:
        candidate_designs = json.load(f)

    # Convert to compact format JSON string
    candidate_designs_json = json.dumps(candidate_designs, separators=(',', ':'))

    for model in ["gpt-4"]:
        print(f"\n=== Judging with {model} ===")
        judge_agent = ExpertJudgeAgent(model=model)
        top_designs = judge_agent.judge_designs(candidate_designs_json, optimization_goal="performance", top_k=2)
        with open("../results/cgra_top_k.json", "w") as f:
            json.dump(top_designs, f, indent=2)
