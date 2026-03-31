                                      
import pdb
import sys
import os
import time

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
from AccessControl.java_code_parser import get_db_pattern_from_java_code
from tqdm import tqdm
from dotenv import load_dotenv
from pathlib import Path
from openai import OpenAI
import argparse

#python AccessControl/vul_detection.py

# model_name = "Qwen3-32B"
# model_name = "gpt-4o-mini"
#
#
# access_model_path = PathUtil.output_data("DAYU_acm_Qwen3-32B_1203", "json")
                            
# input_access_control_model_path = PathUtil.output_data("DAYU_processed_models_1203", "json")
                                                    
# complete_access_model_path = PathUtil.output_data("DAYU_complete_operation_1203", "json")
                  
# output_access_control_model_path = PathUtil.output_data("DAYU_diff_operation_1203"+model_name , "json")
            
# call_chains_path = PathUtil.call_chain_data("DAYU_call_chains_up_down_77", "json")
              
# after_reducing_false_positives_path = PathUtil.output_data("DAYU_final_result_1203", "json")
                    
# false_positives_path = PathUtil.output_data("DAYU_false_positives_result_93", "json")
        
# #resource_list =  ['EscAttachment','CarDocument','BusiBase','Busi']
# resource_list=['WorkspaceUser']
#
#
#
#
#
# prompt = Prompt()
#
#
#
# client = {
#     "gpt-4o-mini": OpenAI(
                                                                                    
#     # base_url='https://api.openai-proxy.org/v1',
#     base_url='https://openkey.cloud/v1',
#     api_key='sk-i9xfELTdbFKeeooi1516Ec93302448F8929a91294aB640Aa'),
#     "deepseek-reasoner": OpenAI(api_key="sk-8f68830b4fb04ebda6267add4af148f3", base_url="https://api.deepseek.com"),
#     "gpt-4o-2024-08-06": OpenAI(
                                                                                    
#     # base_url='https://api.openai-proxy.org/v1',
#     base_url='https://openkey.cloud/v1',
#     api_key='sk-vQQVtY65hvKXajLVCe59759c33F34c79995eF96f6726E5A0'),
#     "Qwen3-32B":OpenAI(
#     api_key="DASHSCOPE_API_KEY",
#     base_url="http://70.181.3.224:9529/v1")
# }
parser = argparse.ArgumentParser(description="detect vulnerabilities from access control models")

parser.add_argument("--model_name", type=str, required=True, help="模型名称，如 Qwen3-32B")

       
parser.add_argument("--access_control_model_path", type=str, required=True, help="抽取好的访问控制模型文件名")
parser.add_argument("--processed_access_control_model_path", type=str, required=True,
                    help="Processed access control model 文件名")
parser.add_argument("--complete_access_control_model_path", type=str, required=True,
                    help="Complete access model 文件名")
parser.add_argument("--diff_access_control_model_path", type=str, required=True,
                    help="Diff access control model 文件名（初步扫描的结果）")
parser.add_argument("--call_chains_path", type=str, required=True, help="上下文调用链文件名")
parser.add_argument("--final_result_path", type=str, required=True, help="误报消除后的最终输出文件名")
parser.add_argument("--false_positives_path", type=str, required=True, help="被判为误报的模型输出文件名")
parser.add_argument("--resources_path", type=str, required=False, help="Resource data name")
      
parser.add_argument("--resource_list", nargs="+", required=False, help="资源列表，如 ThreatEvt ProcessPolicy NacPolicy")

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
      
resource_list = args.resource_list
                                               
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
    "gpt-4o-2024-08-06": OpenAI(
        base_url='https://openkey.cloud/v1',
        api_key='sk-vQQVtY65hvKXajLVCe59759c33F34c79995eF96f6726E5A0'),
    "Qwen3-32B": OpenAI(
        api_key="DASHSCOPE_API_KEY",
        base_url="http://70.181.3.224:9529/v1")
}


def get_answer_from_llm(messages, model_name):
    chat_completion = client[model_name].chat.completions.create(
        messages=messages,
        temperature=0.0000001,
        model=model_name
    )
    response = chat_completion.choices[0].message.content
    # print(response)
    # if resource=='Strategy' and func_name=='deleteStrategy':
    #    print(response)
    # LLM_org_response.append({"resource": org_resource[-1], "location": org_location[-1], "original answer": response})
    # print("\033[31m" + response + "\033[0m")
    try:
        json_response = split_answer(response)
        if json_response == None:
            print('\n' + response)
            json_response = json.loads(response[response.find('</think>') + 8:].strip())
        return json_response
        # print("\033[32m" + str(response) + "\033[0m")
    except Exception as e:
        print("\033[33m" + f"Error type: {type(e).__name__}, Error message: {str(e)}" + "\033[0m")
        print("\033[33m" + "Response content: " + str(response) + "\033[0m")
                               
        return []



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


def get_resource_all_access_control_models(diff_model, input_access_control_model_path):
    access_control_models = []
    data = DataUtils.load_json(input_access_control_model_path)
    # with open(input_access_control_model_path, 'r', encoding='utf-8') as f:
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


def model_classification_by_operation_type(models, output_file, resources):
    data = models

    merged_data = defaultdict(list)

    for item in data:
        # pdb.set_trace()
        resource = item["resource"]
        if resource not in resources:
            continue
        location = item["location"]
        #     role_type=item["Role Type"]
        path_info = item["path_info"]
        for model in item["access_control_model"]:
            if "Operation Type" not in model:
                continue
            operation_type = model["Operation Type"]
            key = (resource, operation_type)

                                             
            model_data = {key: value for key, value in model.items() if key != "Operation Type"}

            merged_data[key].append({
                "location": location,
                "path_info": path_info,
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


def find_complete_operation(resource, operation_type, complete_access_models):
                                                                                              
    relevant_complete_permissions = []
    relevant_complete_parameters = []
    for complete_model in complete_access_models:
        if complete_model["resource"] == resource and complete_model["operation_type"] == operation_type:
            relevant_complete_permissions = complete_model["complete_operation"]
            relevant_complete_parameters = complete_model["complete_parameters"]
            break
    return relevant_complete_permissions, relevant_complete_parameters


def filter_id_parameter(raw_parameter):
               
    if "id" not in raw_parameter.lower():
        return None
    segs = raw_parameter.split(".")
    if segs[-1].lower().startswith("get") and segs[-1].lower().endswith("()"):
        return segs[-1][3:-2].lower()
    return raw_parameter.lower()


def find_missing_operation_param(acm_op_param_list, relevant_complete_operation_params):
    missing_params = []
    acm_op_param_list = [filter_id_parameter(param) for param in acm_op_param_list]
    for param in relevant_complete_operation_params:
        if param not in acm_op_param_list:
            missing_params.append(param)
    return missing_params


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


def add_operation_info(entry, all_permissions_new):
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


def parse_json_with_error(json_str):
    """解析 JSON 并显示详细错误信息"""
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        lines = json_str.split('\n')
        error_line_num = e.lineno - 1 if e.lineno > 0 else 0
        error_line = lines[error_line_num] if error_line_num < len(lines) else ""

        print(f"\033[33mJSON解析错误详情: 第{e.lineno}行, 第{e.colno}列\033[0m")
        print(f"\033[33m错误信息: {str(e)}\033[0m")
        print(f"\033[33m错误行内容: {error_line}\033[0m")

        if error_line_num > 0:
            print(f"\033[33m上一行: {lines[error_line_num - 1]}\033[0m")

        raise


def split_answer(answer):
    if "</think>" in answer:
        answer=answer.split("</think>")[1]
    patterns = [
        r'```json(.*?)```',
        r'```(.*?)```',
        # r'\[(.*?)\]',
        r'`(.*?)`'
    ]

    for i,pattern in enumerate(patterns):
        if pattern==r'`(.*?)`':
            answer=answer.split('\n')[-1]
        match = re.search(pattern, answer, re.DOTALL)
        if match:
            json_str = match.group(1).strip()
            return parse_json_with_error(json_str)

    raise ValueError("未匹配JSON 代码块")


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
        model_classification_by_operation_type(models, processed_access_control_model_path, resource_list)

    # pdb.set_trace()

    data = DataUtils.load_json(processed_access_control_model_path)
    complete_operations = []
    existing_diff_access_models = []
    err_diff_access_control_models = []
    # existing_vulnerabilities = []

                                                
    if PathUtil.exists(complete_access_model_path):
        print("complete_access_model_path exists!")
    else:
        for entry in data:
            # if entry["resource"] != "SysUser":
            #     continue
            all_operations = []
                                                                               
            for model in entry["access_control_model"]:
                model.pop("Permission Requirements")
                model.pop("location")
                model.pop("path_info")
                operation_info = model
                all_operations.append(operation_info)

                           
            # all_permissions = qc(all_operations)
            # print("\033[32m" + str(all_permissions) + "\033[0m")
            #
                              
            # # result = remove_duplicate_permission_permissions(all_permissions)
            # # all_permissions_new = extract_result_from_response(result)
            # #
            # # all_permissions_new = add_operation_info(entry, all_permissions_new)
            # all_permissions_new=all_permissions
            complete_operations.append({
                "resource": entry["resource"],
                "operation_type": entry["operation_type"],
                # "role_type": entry["role type"],
                "complete_operation": all_operations
            })

                           
        for index, classified_complete_operation in enumerate(complete_operations):
            all_parameters_in_one_operation = []
            resource = classified_complete_operation["resource"]
            operation_type = classified_complete_operation["operation_type"]
            for operation in classified_complete_operation["complete_operation"]:
                for param in operation["Parameters"]:
                    if param not in all_parameters_in_one_operation:
                        all_parameters_in_one_operation.append(param)
            complete_operations[index]["complete_parameters"] = all_parameters_in_one_operation

        DataUtils.save_json(complete_access_model_path, complete_operations)

                                                    
    complete_access_models = DataUtils.load_json(complete_access_model_path)
    for entry in data:
        resource = entry["resource"]
        operation_type = entry["operation_type"]
                               
        relevant_complete_permissions, relevant_complete_parameters = find_complete_operation(resource, operation_type,
                                                                                              complete_access_models)
        relevant_complete_parameters = list(
            set([filter_id_parameter(raw_para) for raw_para in relevant_complete_parameters if
                 filter_id_parameter(raw_para) != None]))
        for model in entry["access_control_model"]:
                       
            missing_permission = find_missing_operation_param(model["Parameters"],
                                                              relevant_complete_parameters)
            model["missing_parameters"] = missing_permission
    DataUtils.save_json(output_access_control_model_path, data)

          
    # print("=================false positive elimination============")
    diff_access_control_models = DataUtils.load_json(output_access_control_model_path)
    db_code_path = ''
    db_patterns = get_db_pattern_from_java_code(db_code_path)
    for same_type_access_control_models in diff_access_control_models:
        resource = same_type_access_control_models["resource"]
        operation_type = same_type_access_control_models["operation_type"]
        for access_control_model in same_type_access_control_models["access_control_model"]:
            object = access_control_model["Object"].lower()
            missing_parameters = access_control_model["missing_parameters"]
            new_missing_parameters = []

                                                    
            db_pattern = db_patterns.get(object)
            if db_pattern:
                for param in missing_parameters:
                    if param in [attr.lower() for attr in db_pattern]:
                        new_missing_parameters.append(param)
                access_control_model["missing_parameters"] = new_missing_parameters

            op_params_info = {"Relevant Code Snippet": access_control_model["Relevant Code Snippet"],
                              "Operation Location": access_control_model["Operation Location"],
                              "Parameters": access_control_model["Parameters"],
                              "missing_parameters": access_control_model["missing_parameters"]}
            operation_type=access_control_model["Operation Type"]
            compare_parameters_prompt=prompt.compare_parameters_prompt(op_params_info,operation_type,resource)
            messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": compare_parameters_prompt},
            ]
            result = get_answer_from_llm(messages, model_name)
            access_control_model["missing_parameters"]=result

    DataUtils.save_json(after_reducing_false_positives_path, diff_access_control_models)


if __name__ == '__main__':
    pipeline()
