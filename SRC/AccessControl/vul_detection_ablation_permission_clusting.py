                                      
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

parser = argparse.ArgumentParser(description="detect vulnerabilities from access control models")

parser.add_argument("--model_name", type=str, required=True, help="模型名称，如 Qwen3-32B")

       
parser.add_argument("--access_control_model_path", type=str, required=True, help="抽取好的访问控制模型文件名")
parser.add_argument("--processed_access_control_model_path", type=str, required=True, help="Processed access control model 文件名")
parser.add_argument("--complete_access_control_model_path", type=str, required=True, help="Complete access model 文件名")
parser.add_argument("--diff_access_control_model_path", type=str, required=True, help="Diff access control model 文件名（初步扫描的结果）")
parser.add_argument("--call_chains_path", type=str, required=True, help="上下文调用链文件名")
parser.add_argument("--final_result_path", type=str, required=True, help="误报消除后的最终输出文件名")
parser.add_argument("--false_positives_path", type=str, required=True, help="被判为误报的模型输出文件名")
parser.add_argument("--resources_path", type=str, required=False, help="Resource data name")
      
parser.add_argument("--resource_list", nargs="+", required=False, help="资源列表，如 ThreatEvt ProcessPolicy NacPolicy")
parser.add_argument("--fp_setting", type=int, required=False, default=100, help="误报消除配置，默认100，111 代表has_equivalent_permission=1， is_operation_equivalent=1，has_equivalent_permission_in_call_chain=1")
# args = parser.parse_args()

args = parser.parse_args()

model_name = args.model_name

access_model_path = args.access_control_model_path
                          
processed_access_control_model_path = args.processed_access_control_model_path
                                                  
complete_access_model_path = args.complete_access_control_model_path
                
output_access_control_model_path = args.diff_access_control_model_path
          
call_chains_path = args.call_chains_path
            
after_reducing_false_positives_path = args.final_result_path
                  
false_positives_path = args.false_positives_path
resources_path = args.resources_path
      
resource_list=args.resource_list
fp_setting = args.fp_setting
                                               

# model_name="gpt-4o-mini"
# access_model_path=PathUtil.output_data("youlai_acm_4omini_429","json")
# processed_access_control_model_path=PathUtil.output_data("youlai_processed_models_1229","json")
# complete_access_model_path=PathUtil.output_data("youlai_complete_models_1229","json")
# output_access_control_model_path=PathUtil.output_data("youlai_diff_models_4omini_1229","json")
# call_chains_path=PathUtil.call_chain_data("youlai_call_chains_up_down_429","json")
# after_reducing_false_positives_path=PathUtil.output_data("youlai_final_result_4omini_1229","json")
# false_positives_path=PathUtil.output_data("youlai_false_positive_it4case5_6_7_4omini_1229","json")
# resources_path=PathUtil.resource_data("youlai-mall-master_resources","json")
# resource_list=["SysDictType"]


if resource_list is None:
    try:
        data = DataUtils.load_json(resources_path)
        resource_list = [str(item.get('Resource', '')).strip() for item in data if item.get('Resource')]
    except Exception as e:
        print(f"读取资源列表失败: {e}")
        resource_list = []


prompt = Prompt()
          
current_file = Path(__file__).resolve()
env_file = current_file.parent / "../.env"
load_dotenv(env_file.resolve())
client = {
                                                  
                                                 
    "gpt-4o-mini": OpenAI(
        base_url=os.getenv("BASE_URL"),
        api_key=os.getenv("GPT_4o_mini_KEY")),
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
    print(response)
    return response


def extract_result_from_response(result):
    if not isinstance(result, str):
        print(type(result))
        print(result)
        return []
    match = re.search(r'```json(.*?)```', result, re.DOTALL)
    if match:
        result_str = match.group(1).strip()
                                    
        if result_str == "{None}":
            return []
        result = json.loads(result_str)
        return result
    else:
        return []


def summarize_permissions(all_permissions):
    max_count = 3          
    detect_prompt = prompt.summarize_permissions_prompt(all_permissions)

    for count in range(max_count):
        messages = [
            {"role": "system", "content": detect_prompt},
            {"role": "user", "content": f"下面是输入的权限检查列表：\n {all_permissions}"},
        ]
        result = get_answer_from_llm(messages, model_name)
        # match = re.search(r'(?:\"\"\"|```json)(.*?)(?:\"\"\"|```)', result, re.DOTALL)
        # if match:
        #     return result
        # else:
        #     continue
        return result


def remove_duplicate_permission_permissions(all_permissions):
    max_count = 3          
    detect_prompt = prompt.remove_duplicate_permission_permissions_prompt(all_permissions)

    for count in range(max_count):
        messages = [
            {"role": "system", "content": detect_prompt},
            {"role": "user", "content": f"下面是输入的待分类的权限检查列表：\n {all_permissions}"},
        ]
        result = get_answer_from_llm(messages, model_name)
        match = re.search(r'(?:\"\"\"|```json)(.*?)(?:\"\"\"|```)', result, re.DOTALL)
        if match:
            return result
        else:
            continue


def has_equivalent_permission(model, missing_permission_requirements):
    max_count = 3          
    detect_prompt = prompt.has_equivalent_permission_prompt(model, missing_permission_requirements)

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

def has_permission_in_call_chain(model, missing_permission_requirements, call_chain_code):
    max_count = 3          
    detect_prompt = prompt.has_permission_in_call_chain_prompt(model, missing_permission_requirements, call_chain_code)

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


def has_equivalent_operation(model, missing_permission_requirements):
    max_count = 3          
    detect_prompt = prompt.has_equivalent_operation_prompt(model, missing_permission_requirements)

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

def get_lack_of_permission_check(most_complete_access_control_model, access_control_models):
    max_count = 3          
    detect_prompt = prompt.detect_lack_of_permission_check(most_complete_access_control_model, access_control_models)
    for count in range(max_count):
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": detect_prompt},
        ]
        result = get_answer_from_llm(messages, model_name)
        match = re.search(r'(?:\"\"\"|```json)(.*?)(?:\"\"\"|```)', result, re.DOTALL)
        if match:
            return result
        else:
            continue


def get_most_complete_access_control_model(access_control_models):
    max_count = 3          
    detect_prompt = prompt.detect_most_complete_access_control_model(access_control_models)
    for count in range(max_count):
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": detect_prompt},
        ]
        result = get_answer_from_llm(messages, model_name)
        # match = re.search(r'"""(.*?)"""', result, re.DOTALL)
                                         
        match = re.search(r'(?:\"\"\"|```json)(.*?)(?:\"\"\"|```)', result, re.DOTALL)
        if match:
            # print(f"The {count} Result for resource {resource}:\n{result}\n")
            return result
        else:
            continue


def get_diff_access_control_models(entry):
    max_count = 3          

    resource = entry["resource"]
    access_control_models = entry["access_control_model"]
    detect_prompt = prompt.detect_diff_access_control_models(resource, access_control_models)
    for count in range(max_count):

        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": detect_prompt},
        ]
        result = get_answer_from_llm(messages, model_name)
        # match = re.search(r'"""(.*?)"""', result, re.DOTALL)
                                         
        match = re.search(r'(?:\"\"\"|```json)(.*?)(?:\"\"\"|```)', result, re.DOTALL)
        if match:
            # print(f"The {count} Result for resource {resource}:\n{result}\n")
            return result
        else:
            continue


def find_relative_path(root_dir, target_filename):
    for dirpath, dirnames, filenames in os.walk(root_dir):
        if target_filename in filenames:
                    
            relative_path = os.path.relpath(os.path.join(dirpath, target_filename), root_dir)
            return relative_path
    return None


def get_resource_all_access_control_models(diff_model, processed_access_control_model_path):
    access_control_models = []
    data = DataUtils.load_json(processed_access_control_model_path)
    # with open(processed_access_control_model_path, 'r', encoding='utf-8') as f:
    #     data = json.load(f)
    for entry in data:
        if entry["resource"] == diff_model["resource"] and entry["operation_type"] == diff_model["operation_type"]:
            models = entry["access_control_model"]
            for model in models:
                if model["Operation Description"] != diff_model["Operation Description"]:
                    # pdb.set_trace()
                    access_control_models.append(model)
    return access_control_models


def detect_access_control_vulnerabilities(diff_model, code_snippet, call_chain, access_control_models):
    max_count = 3          
    # pdb.set_trace()
    detect_prompt = prompt.detect_access_control_vulnerabilities_test(diff_model["resource"], code_snippet, call_chain,
                                                                      diff_model)
    for count in range(max_count):
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": detect_prompt},
        ]
        result = get_answer_from_llm(messages, model_name)
        # match = re.search(r'"""(.*?)"""', result, re.DOTALL)
                           
        # match = re.search(r'(?:\"\"\"|```json)(.*?)(?:\"\"\"|```)', result, re.DOTALL)
        # if match:
        #     # print(f"The {count} Result for resource {resource_opt[0]}:\n{result}\n")
        #     return result
        # else:
        #     continue
        return result


def model_classification_by_operation_type(models, output_file,resources):
    data = models

    merged_data = defaultdict(list)
                                      
    for item in data:
        # pdb.set_trace()
        resource = item["resource"]
        if resource not in resources:
            continue
        location = item["location"]
        if "Service" in location:
            continue
   #     role_type=item["Role Type"]
   #      path_info = item["path_info"]
        for model in item["access_control_model"]:
            if "Operation Type" not in model:
                continue
            operation_type = model["Operation Type"]
            key = (resource, operation_type)

                                             
            model_data = {key: value for key, value in model.items() if key != "Operation Type"}

            merged_data[key].append({
                "location": location,
                # "path_info": path_info,
                **model_data
            })

    transformed_data = []

    for (resource, operation_type), acm_list in merged_data.items():
        transformed_data.append({
            "resource": resource,
            "operation_type": operation_type,
#            "role type": role_type,
            "access_control_model": acm_list
        })

                                                                            
    for entry in transformed_data:
        for model in entry["access_control_model"]:
            if "Operation description" in model:
                model["Operation Description"] = model["Operation description"]
                del model["Operation description"]

    DataUtils.save_json(output_file, transformed_data)


def find_complete_access_control_model(resource, operation_type, complete_access_models):
                                                                                              
    relevant_complete_permissions = []
    for complete_model in complete_access_models:
        if complete_model["resource"] == resource and complete_model["operation_type"] == operation_type :
            relevant_complete_permissions = complete_model["complete_permissions"]
            break
    return relevant_complete_permissions


def find_missing_requirements(permission_list, relevant_complete_permissions, location):
    code_permission_list = {item["Relevant Code Snippet"] for item in permission_list}
                                                                         
    missing_permissions = []
    for permission_set_all in relevant_complete_permissions:
        permission_set = permission_set_all["missing_permission_requirements"]
        # for permission in permission_set:
        #    print(f"permission:{permission}")
        if not any(permission["Permission Requirements"]["Relevant Code Snippet"] in code_permission_list for permission in
                   permission_set)\
            and not any(permission["location"] == location for permission in permission_set):
            missing_permissions.append(permission_set_all)
    return missing_permissions


def handle_similarity_check():
    data = DataUtils.load_json(processed_access_control_model_path)
    print(len(data))
    complete_access_models = []
    for entry in data:
        all_permissions = []
        all_details = []
        all_codes = []
        for model in entry["access_control_model"]:
            for permission in model["Permission Requirements"]:
                if (permission["Description"] == "None"):
                    continue
                detail = permission["Details"]
                code = permission["Relevant Code Snippet"]
                if code in all_codes:
                    print("之前出现过")
                    continue
                all_codes.append(code)
                all_permissions.append(permission)

        complete_access_models.append({
            "resource": entry["resource"],
            "operation_type": entry["operation_type"],
            "complete_permissions": all_permissions
        })
        print("开始对比")
        print(len(all_codes))
        all_codes = list(set(all_codes))
        print(len(all_codes))
    DataUtils.save_json(complete_access_model_path, complete_access_models)
    # print(all_permissions)


def qc(all_permissions):
    all_permissions_new = []
    all_codes = []
    for permission in all_permissions:
        if permission["Relevant Code Snippet"] in all_codes:
            print("之前出现过")
            continue
        all_codes.append(permission["Relevant Code Snippet"])
        all_permissions_new.append(permission)
    return all_permissions_new


def add_operation_info(entry,all_permissions_new):
    print(f"all_permissions_new:{all_permissions_new}")
    for i, complete_model in enumerate(all_permissions_new):
        for j, model in enumerate(complete_model):
            for access_control_model in entry["access_control_model"]:
                for permission in access_control_model["Permission Requirements"]:
                    if model["Relevant Code Snippet"] == permission["Relevant Code Snippet"]:
                        new_model = {
                            "location": access_control_model["location"],
                            "Operation Description": access_control_model["Operation Description"],
                            "Relevant Code Snippet": access_control_model["Relevant Code Snippet"],
                            "Permission Requirements": model
                        }
                                     
                        all_permissions_new[i][j] = new_model

    return all_permissions_new

def cls_vul_type(vul_model):
    max_count = 3          
    detect_prompt = prompt.cls_vul_type_prompt(vul_model)

    result=""
    for count in range(max_count):
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": detect_prompt},
        ]
        result = get_answer_from_llm(messages, model_name)
        if result.lower() not in ["authentication","horizontal privilege escalation","vertical privilege escalation"]:
            continue
        else:
            break

    return result

def split_answer(answer):
    match = re.search(r'```json(.*?)```', answer, re.DOTALL)
    if match:
        oplist_str = match.group(1).strip()
        operation_list = json.loads(oplist_str)
        return operation_list
    else:
        print("output format wrong，can't split answer")
def reduce_false_positives(code_item, code_snippet, call_chains, call_chain_code, missing_permission):
    """
    Reduce false positives in the data
    """
    # func_name, code_snippet, call_chains, call_chain_code,missing_permission
    extract_operation_list_prompt = prompt.reduce_false_positives_prompt(code_item["function_name"], code_snippet,
                                                                         call_chains, call_chain_code,
                                                                         missing_permission)

    # pdb.set_trace()

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": extract_operation_list_prompt}
    ]
    chat_completion = client[model_name].chat.completions.create(
        messages=messages,
        temperature=0.0000001,
        model=model_name
    )
    response = chat_completion.choices[0].message.content
    response = split_answer(response)
    return response


def pipeline():
                                
    print("********************************")
    # if input_path exist:
    if PathUtil.exists(processed_access_control_model_path):
        print("processed_data exists!")
        print("&&&&&&&&&&&&&&&&&&&&&&&********************************")
    else:
        models = DataUtils.load_json(access_model_path)
                   
        #print('here')
        model_classification_by_operation_type(models, processed_access_control_model_path,resource_list)

    # pdb.set_trace()

    data = DataUtils.load_json(processed_access_control_model_path)
    existing_diff_access_models = []
    err_diff_access_control_models = []
    # existing_vulnerabilities = []

                                           
    complete_access_models = []
    if PathUtil.exists(complete_access_model_path):
        print("complete_access_model_path exists! Loading existing data...")
        complete_access_models = DataUtils.load_json(complete_access_model_path)
    else:
        print("complete_access_model_path does not exist, starting from scratch...")

                                                
    for entry in data:

        skip_entry = False
                        
        for model in complete_access_models:
            if model["resource"] == entry["resource"] and model["operation_type"] == entry["operation_type"] and model["complete_permissions"] != []:
                print(f"Skipping already processed entry: {entry['resource']} - {entry['operation_type']}")
                skip_entry = True
                break
        if skip_entry:
            continue
        all_permissions = []
                                      
        for model in entry["access_control_model"]:
            effective_permissions = []
            for permission in model["Permission Requirements"]:
                                            
                if not all(value == "None" for value in permission.values()):
                    effective_permissions.append(permission)
            if len(all_permissions) < len(effective_permissions):
                all_permissions = effective_permissions

        print(f"all_permissions:{all_permissions}")
        if all_permissions == []:
            continue
                     
        all_permissions = qc(all_permissions)
        print("\033[32m" + str(all_permissions) + "\033[0m")
                             
        all_permissions = json.dumps(all_permissions)
                      
        result = remove_duplicate_permission_permissions(all_permissions)
        print(f"result:{result}")
        all_permissions_new = extract_result_from_response(result)
        print(f"all_permissions_new:{all_permissions_new}")
        all_permissions_new = add_operation_info(entry, all_permissions_new)

                    
        new_complete_access_models = []
        for permission_set in all_permissions_new:
            result = summarize_permissions(permission_set)
            permission_description = extract_result_from_response(result)
            new_permission_set = {
                "permission_description":"None" if permission_description==[] else permission_description["permission_description"],
                "missing_permission_requirements": permission_set
            }
            new_complete_access_models.append(new_permission_set)

                                   
        complete_access_model = {
            "resource": entry["resource"],
            "operation_type": entry["operation_type"],
           # "role_type": entry["role type"],
            "complete_permissions": new_complete_access_models
        }
        complete_access_models.append(complete_access_model)
        
                    
        DataUtils.save_json(complete_access_model_path, complete_access_models)
        print(f"Saved progress for entry: {entry['resource']} - {entry['operation_type']}")

    if not os.path.exists(complete_access_model_path):
        print(f"output_access_control_model_path does not exist!")
        exit(1)

                                                    
    complete_access_models = DataUtils.load_json(complete_access_model_path)
    for entry in data:
                      
        relevant_complete_permissions = find_complete_access_control_model(entry["resource"], entry["operation_type"],
                                                                           complete_access_models)
        for model in entry["access_control_model"]:
                       
            missing_permission = find_missing_requirements(model["Permission Requirements"],
                                                           relevant_complete_permissions, model["location"])
            model["missing_permission"] = missing_permission
    DataUtils.save_json(output_access_control_model_path, data)

    
                   
    enable_has_equivalent_permission = (fp_setting // 100) > 0
    enable_is_operation_equivalent = (fp_setting // 10 % 10) > 0
    enable_permission_in_call_chain = (fp_setting % 10) > 0

    if enable_has_equivalent_permission:
        print("enable_has_equivalent_permission")
    if enable_is_operation_equivalent:
        print("enable_is_operation_equivalent")
    if enable_permission_in_call_chain:
        print("enable_permission_in_call_chain")
    
           
           
                                                           
                                                            
                                                             
                                                                    
                                                                    
    print("=================false positive elimination============")
    data_1 = DataUtils.load_json(output_access_control_model_path)
    call_chains_data = DataUtils.load_json(call_chains_path)
    if PathUtil.exists(after_reducing_false_positives_path):
        final_result = DataUtils.load_json(after_reducing_false_positives_path)
    else:
        final_result = []
    if PathUtil.exists(false_positives_path):
        false_positives = DataUtils.load_json(false_positives_path)
    else:
        false_positives = []
        
    for i, item in tqdm(enumerate(data_1)):
        resource = item["resource"]
        # if item["operation_type"] != "read":
        #     continue
        if resource not in resource_list:
            continue
        process_flag = False
        for model in final_result:
            if model["resource"] == item["resource"] and model["operation_type"] == item["operation_type"]:
                process_flag = True
                break
        if process_flag:
            continue
        result = {"resource": item["resource"], "operation_type": item["operation_type"]}
        fp_result = {"resource": item["resource"], "operation_type": item["operation_type"]}
        access_control_models = item["access_control_model"]
        real_bug = []
        fp = []
        for j, model in enumerate(access_control_models):
            # if not(model["location"]=="ApiPayController.java:payPrepay") :
            #     continue
            # if model["location"]!="SysDictController.java:getDictTypeForm" and model["location"]!="SysDictController.java:updateDictType" and model["location"]!="SysDictTypeServiceImpl.java:saveDictType":
            #    continue

            # acm_operation_description = model["Operation Description"]
            # acm_relevant_code_snippet = model["Relevant Code Snippet"]
            # acm_permission_requirements = model["Permission Requirements"]
                                  
            for k, missing_permission in enumerate(model["missing_permission"]):
                result_equivalent_permission_operation = {}
                """
                # (一) 判定“是否存在等价操作”——若存在，则说明功能上该操作已实现，不一定缺失权限
                """
                result_equivalent_operation={}
                cnt=0
                if enable_is_operation_equivalent:
                    while ("is_operation_equivalent" not in result_equivalent_operation.keys() or "reason_for_is_operation_equivalent" not in result_equivalent_operation.keys()) and cnt<5:
                        op_result = has_equivalent_operation(model, missing_permission["missing_permission_requirements"])
                        result_equivalent_operation = extract_result_from_response(op_result)
                        if not isinstance(result_equivalent_operation,dict):
                            result_equivalent_operation={}
                            continue
                        cnt+=1
                    result_equivalent_permission_operation["is_operation_equivalent"]= result_equivalent_operation["is_operation_equivalent"]
                    result_equivalent_permission_operation["reason_for_is_operation_equivalent"]= result_equivalent_operation["reason_for_is_operation_equivalent"]
                """
                # (二) 判定“是否存在等价权限检查”——若存在，则无需再标记缺失
                """
                result_equivalent_permission={}
                cnt=0
                if enable_has_equivalent_permission:
                    while (
                        "has_equivalent_permission" not in result_equivalent_permission.keys() or "reason_for_has_equivalent_permission" not in result_equivalent_permission.keys()) and cnt < 5:
                        permission_result = has_equivalent_permission(model,
                                                                missing_permission["missing_permission_requirements"])
                        result_equivalent_permission = extract_result_from_response(permission_result)
                        if not isinstance(result_equivalent_permission,dict):
                            result_equivalent_permission={}
                            continue
                        cnt+=1
                    result_equivalent_permission_operation["has_equivalent_permission"]= result_equivalent_permission["has_equivalent_permission"]
                    result_equivalent_permission_operation["reason_for_has_equivalent_permission"]= result_equivalent_permission["reason_for_has_equivalent_permission"]
                """
                # (三) 在“调用链上下文”里搜索权限证据（当前函数代码 + 下游调用 + 上游调用）
                """
                if enable_permission_in_call_chain:
                    call_chain_code =[call_chains_data[resource][model["location"]]["code_snippet"]] + call_chains_data[resource][model["location"]]["call_chain_code_down"] +\
                                    call_chains_data[resource][model["location"]]["call_chain_code_up"]
                    #print(f"callchain_code:\n{call_chain_code}")
                    result_permission_in_call_chain=[{}]
                    cnt=0
                    while ("has_equivalent_permission_in_call_chain" not in result_permission_in_call_chain[0].keys() or "is_irrelevant_permission" not in result_permission_in_call_chain[0].keys()) and cnt < 5:
                               
                        pr_in_call_chain_result = has_permission_in_call_chain(model, 
                            missing_permission["missing_permission_requirements"], call_chain_code)
                              
                        result_permission_in_call_chain = extract_result_from_response(pr_in_call_chain_result)
                        #print(f'result_permission_in_call_chain:{result_permission_in_call_chain}')
                        if not isinstance(result_permission_in_call_chain,list):
                            result_permission_in_call_chain=[result_permission_in_call_chain]
                        if not isinstance(result_permission_in_call_chain[0],dict):
                            result_permission_in_call_chain[0]={}
                            continue
                        cnt+=1
                    all_no = all((result_item["has_equivalent_permission_in_call_chain"] == "no" and result_item["is_irrelevant_permission"]=="no") for result_item in
                             result_permission_in_call_chain)
                    result_equivalent_permission_operation['permission_in_call_code'] = result_permission_in_call_chain

                # print(f"result_equivalent_permission_operation:{result_equivalent_permission_operation}")
                                                      
                       
                                                              
                                                                           
                
                missing_permission["result"] = result_equivalent_permission_operation
                                 
                                                             
                if (not enable_has_equivalent_permission or (enable_has_equivalent_permission and result_equivalent_permission_operation["has_equivalent_permission"] == "no")) and\
                        (not enable_is_operation_equivalent or (enable_is_operation_equivalent and result_equivalent_permission_operation["is_operation_equivalent"] == "yes")) and\
                        (not enable_permission_in_call_chain or (enable_permission_in_call_chain and all_no)):
                                  
                    real_bug.append(model)
                    break
                else:
                                  
                    fp.append(model)
        result["access_control_model"] = real_bug
        fp_result["access_control_model"] = fp
        final_result.append(result)
        false_positives.append(fp_result)
        DataUtils.save_json(after_reducing_false_positives_path, final_result)
        DataUtils.save_json(false_positives_path, false_positives)

    result=DataUtils.load_json(after_reducing_false_positives_path)
    for vuls in result:
        for vul in vuls["access_control_model"]:
            vul["vulnerability_type"]=cls_vul_type(vul)
    DataUtils.save_json(after_reducing_false_positives_path, result)



if __name__ == '__main__':
    pipeline()
