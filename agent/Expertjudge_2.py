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
        api_key = "xxxxxxxxxxxxxxxxxxxxxxx"  # Replace with your API key
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



class ExpertJudge2Agent:
    def __init__(self, model="qwen-plus"):
        self.model = model

    def select_best(self, topk_designs, optimization_goal="performance", feedback=None):
        """
        Use LLM to select the best design from top-k designs, and return best_design part.
        Output is fixed as a JSON object, containing "best_design" and "reason".
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

        # Try matching outermost {} JSON object
        json_match = re.search(r"(\{[\s\S]*\})", content)
        if json_match:
            json_str = json_match.group(1)
            try:
                parsed = json.loads(json_str)
                # Only return best_design part
                best_design_arch = parsed.get("best_design", {})
            except json.JSONDecodeError:
                #print("⚠️ Extracted JSON is invalid:")
                best_design_arch = {}
        else:
            #print("⚠️ No JSON found in content:")
            best_design_arch = {}

        return best_design_arch




# ========== Usage example ==========
if __name__ == "__main__":
    with open("../results/cgra_top_k.json", "r") as f:
        topk_designs = json.load(f)

    # Convert to compact format JSON string
    topk_designs = json.dumps(topk_designs, separators=(',', ':'))

    for model in ["gpt-4"]:
        #print(f"\n=== Judging with {model} ===")
        judge_agent = ExpertJudge2Agent(model=model)
        best_design = judge_agent.select_best(topk_designs, optimization_goal="performance")
        with open("../results/cgra_best_design.json", "w") as f:
            json.dump(best_design, f, indent=2)
