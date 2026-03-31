                                      
import pdb
import sys
import os
import time
import argparse
#python AccessControl/vul_detection.py

# Add project root directory to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

import json
import re
from collections import defaultdict
from utils.path_util import PathUtil
from utils.data_utils import DataUtils
from AccessControl.prompt_templates import Prompt
from tqdm import tqdm

from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path
import copy

model_name = "gpt-4o-mini"

client = {
                                                  
                                                 
    "gpt-4o-mini": OpenAI(
        base_url="https://openkey.cloud/v1",
        api_key="sk-173jLU0nFUc5yPy3A32fB6Aa2dB340038366Eb8b073a465f"),
    "deepseek-reasoner": OpenAI(
        api_key="sk-8f68830b4fb04ebda6267add4af148f3", 
        base_url="https://api.deepseek.com"),
    # "gpt-4o-mini": OpenAI(
    #     base_url='https://openkey.cloud/v1',
    #     api_key='api_key'),
    "Qwen3-32B":OpenAI(
        api_key="DASHSCOPE_API_KEY",
        base_url="base_url")
}


def get_answer_from_llm(messages, model_name):
    chat_completion = client[model_name].chat.completions.create(
        messages=messages,
        temperature=0.0000001,
        model=model_name
    )
    response = chat_completion.choices[0].message.content
    return response

prompt = Prompt()

def has_permission_in_call_chain(model, missing_permission_requirements, call_chain_code):
    max_count = 3          
    detect_prompt = prompt.has_permission_in_call_chain_prompt(model, missing_permission_requirements, call_chain_code)
    print(detect_prompt)
    for count in range(max_count):
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": detect_prompt},
        ]
        result = get_answer_from_llm(messages, model_name)
        match = re.search(r'(?:\"\"\"|```json)(.*?)(?:\"\"\"|```)', result, re.DOTALL)
        if match:
            result_str = match.group(1).strip()
            try:
                result_str = json.loads(result_str)
                return result
            except json.JSONDecodeError as e:
                print(f"JSON 解析失败（第 {count + 1} 次尝试）：{e}")
                continue           
        else:
            continue

print("=================false positive elimination============")
diff_access_control_model = DataUtils.load_json("/home/huxin/AccessControlSrc/experiment/normal/booklore/output_debug/diff_access_control_model.json")
call_chains_data = DataUtils.load_json("/home/huxin/AccessControlSrc/experiment/normal/booklore/output_old/booklore_call_chains_up_down.json")

false_positives = []
enable_is_operation_equivalent = 1
for i, item in tqdm(enumerate(diff_access_control_model)):
    resource = item["resource"]

    process_flag = False
    result = {"resource": item["resource"], "operation_type": item["operation_type"]}
    fp_result = {"resource": item["resource"], "operation_type": item["operation_type"]}
    access_control_models = item["access_control_model"]
    real_bug = []
    fp = []
    for j, model in enumerate(access_control_models):
        if model["missing_permission"] == []:
            continue
        print(f"location: {model['location']}")
        call_chain_code =[call_chains_data[resource][model["location"]]["code_snippet"]] + call_chains_data[resource][model["location"]]["call_chain_code_down"] +\
            call_chains_data[resource][model["location"]]["call_chain_code_up"]
        if call_chain_code == [] or call_chain_code == [""]:
            print("call_chain_code is empty, pass")
            continue
        tp_model = copy.deepcopy(model)
        fp_model = copy.deepcopy(model)
        tp_model["missing_permission"] = []
        fp_model["missing_permission"] = []
        
        for k, missing_permission in enumerate(model["missing_permission"]):
            
            result_equivalent_permission_operation = {}
            
                   
            pr_in_call_chain_result = has_permission_in_call_chain(model, 
                missing_permission["missing_permission_requirements"], call_chain_code)
            print(pr_in_call_chain_result)