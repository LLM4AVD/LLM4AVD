                                      
import pdb
import sys
import os
import time

# Add project root directory to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

import json
import re
from collections import defaultdict
from utils.path_util import PathUtil
from utils.data_utils import DataUtils
from AccessControl.prompt_templates import Prompt

from openai import OpenAI

# model_name = "deepseek-reasoner"
model_name = "gpt-4o-mini"

resources_path = PathUtil.resource_data("youlai-mall-master_resources", "json")
call_chains_path = PathUtil.call_chain_data("youlai_call_chains_up_down_417_bugcase", "json")
access_model_path = PathUtil.output_data("youlai_acm_claude37_430_3", "json")
complete_access_model_path = PathUtil.output_data("youlai_430_3_claude37_complete_models", "json")
input_access_control_model_path = PathUtil.output_data("youlai_430_3_claude37_processed_models", "json")
# diff_access_control_models_path = PathUtil.output_data("test_diff_models_" + model_name, "json")
output_access_control_model_path = PathUtil.output_data("youlai_430_3_diff_models_" + "claude37", "json")
output_vulnerabilities_path = PathUtil.output_data("youlai_429_3_detect_vul_" + model_name, "json")

prompt = Prompt()

# client = {
#     "gpt-4o-mini": OpenAI(
                                            
#     # base_url='https://api.openai-proxy.org/v1',
#     base_url='https://openkey.cloud/v1',
#     api_key='sk-9wLmg9ZiMNdRQHhd27Ce07200fE74eE4Ae1c813701B49a3f'),
#     "deepseek-reasoner": OpenAI(api_key="sk-8f68830b4fb04ebda6267add4af148f3", base_url="https://api.deepseek.com")
# }

client = {
    "gpt-4o-mini": OpenAI(
                                          
    # base_url='https://api.openai-proxy.org/v1',
    base_url='https://openkey.cloud/v1',
    api_key='sk-vQQVtY65hvKXajLVCe59759c33F34c79995eF96f6726E5A0'),
    "deepseek-reasoner": OpenAI(api_key="sk-8f68830b4fb04ebda6267add4af148f3", base_url="https://api.deepseek.com"),
    "gpt-4o-2024-08-06": OpenAI(
                                          
    # base_url='https://api.openai-proxy.org/v1',
    base_url='https://openkey.cloud/v1',
    api_key='sk-vQQVtY65hvKXajLVCe59759c33F34c79995eF96f6726E5A0')
}


url = "https://openkey.cloud/v1/chat/completions"

headers = {
  'Content-Type': 'application/json',
  'Authorization': 'Bearer sk-vQQVtY65hvKXajLVCe59759c33F34c79995eF96f6726E5A0'
}
import requests
def get_answer_from_llm(messages, model_name):
    if model_name=='claude3.7':
        data = {
            "model": "claude-3-7-sonnet-20250219",
            "messages": messages
        }
        try_times = 0
        chat_completion = requests.post(url, headers=headers, json=data).json()
        while 'choices' not in chat_completion.keys():
            print(f"Network problem, {try_times + 1} try")
            chat_completion = requests.post(url, headers=headers, json=data).json()
        response = chat_completion['choices'][0]['message']['content']
        print("\033[31m" + response + "\033[0m")
    else:
        chat_completion = client[model_name].chat.completions.create(
            messages=messages,
            temperature=0.0000001,
            model=model_name
        )
        response = chat_completion.choices[0].message.content
        # LLM_org_response.append({"resource": org_resource[-1], "location": org_location[-1], "original answer": response})
        print("\033[31m" + response + "\033[0m")
    return response


def extract_result_from_response(result):
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
        match = re.search(r'(?:\"\"\"|```json)(.*?)(?:\"\"\"|```)', result, re.DOTALL)
        if match:
            return result
        else:
            continue

def remove_duplicate_permission_permissions(all_permissions):
    max_count = 3          
    detect_prompt = prompt.remove_duplicate_permission_permissions_prompt(all_permissions)

    for count in range(max_count):
        messages = [
            {"role": "system", "content": detect_prompt},
            {"role": "user", "content": f"下面是输入的待分类的权限检查列表：\n {all_permissions}"},
        ]
        result = get_answer_from_llm(messages, 'gpt-4o-2024-08-06')
        match = re.search(r'(?:\"\"\"|```json)(.*?)(?:\"\"\"|```)', result, re.DOTALL)
        if match:
            return result
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


def process_json(models, output_file):
    data = models

    merged_data = defaultdict(list)

    for item in data:
        resource = item["resource"]
        location = item["location"]
        if item["access_control_model"] == None:
            continue
        for model in item["access_control_model"]:
            if "Operation Type" not in model:
                continue
            operation_type = model["Operation Type"]
            key = (resource, operation_type)

                                             
            model_data = {key: value for key, value in model.items() if key != "Operation Type"}

            merged_data[key].append({
                "location": location,
                **model_data
            })

    transformed_data = []

    for (resource, operation_type), acm_list in merged_data.items():
        transformed_data.append({
            "resource": resource,
            "operation_type": operation_type,
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
        if complete_model["resource"] == resource and complete_model["operation_type"] == operation_type:
            relevant_complete_permissions = complete_model["complete_permissions"]
            break
    return relevant_complete_permissions


def find_missing_requirements(permission_list, relevant_complete_permissions):
    code_permission_list = {item["Relevant Code Snippet"] for item in permission_list}
                                                                         
    missing_permissions = []
    for permission_set_all in relevant_complete_permissions:
        permission_set = permission_set_all["Permission Requirements"]
        if not any(permission["Relevant Code Snippet"] in code_permission_list for permission in
                   permission_set):
            missing_permissions.append(permission_set_all)
    return missing_permissions

def qc(all_permissions):
    all_permissions_new = []
    all_codes=[]
    for permission in all_permissions:
        if permission["Relevant Code Snippet"] in all_codes:
            print("之前出现过")
            continue
        all_codes.append(permission["Relevant Code Snippet"])
        all_permissions_new.append(permission)
    return all_permissions_new

def main():
    # if input_path exist:
    if PathUtil.exists(input_access_control_model_path):
        print("processed_data exists!")
    else:
        models = DataUtils.load_json(access_model_path)
                   
        process_json(models, input_access_control_model_path)

    # pdb.set_trace()

    data = DataUtils.load_json(input_access_control_model_path)
    complete_access_models = []
    existing_diff_access_models = []
    err_diff_access_control_models = []
    # existing_vulnerabilities = []

                                                
    if PathUtil.exists(complete_access_model_path):
        print("complete_access_model_path exists!")
    else:
        for entry in data:
            # if entry["resource"] != "SysUser":
            #     continue
            all_permissions = []
                                                                               
            for model in entry["access_control_model"]:
                for permission in model["Permission Requirements"]:
                                                
                    if not all(value == "None" for value in permission.values()):
                        all_permissions.append(permission)

                         
            all_permissions = qc(all_permissions)
            print("\033[32m" + str(all_permissions) + "\033[0m")
            result = remove_duplicate_permission_permissions(all_permissions)
            all_permissions_new = extract_result_from_response(result)
            complete_access_models.append({
                "resource": entry["resource"],
                "operation_type": entry["operation_type"],
                "complete_permissions": all_permissions_new
            })
                    
        for complete_access_model in complete_access_models:
            new_complete_access_models = []
            for permission_set in complete_access_model["complete_permissions"]:
                result = summarize_permissions(permission_set)
                permission_description = extract_result_from_response(result)
                new_permission_set = {
                    "permission_description": permission_description["permission_description"],
                    "Permission Requirements": permission_set
                }
                new_complete_access_models.append(new_permission_set)
            complete_access_model["complete_permissions"] = new_complete_access_models
        DataUtils.save_json(complete_access_model_path, complete_access_models)

                                          
    complete_access_models = DataUtils.load_json(complete_access_model_path)
    for entry in data:
                      
        relevant_complete_permissions = find_complete_access_control_model(entry["resource"], entry["operation_type"],
                                                                           complete_access_models)
        for model in entry["access_control_model"]:
                       
            missing_permission = find_missing_requirements(model["Permission Requirements"],
                                                           relevant_complete_permissions)
            model["missing_permission"] = missing_permission
    DataUtils.save_json(output_access_control_model_path, data)

    # if PathUtil.exists(complete_access_model_path):
    #     print("complete_access_model_path exists!")
    # else:
                          
    #     for entry in data:
    #         if entry["resource"] == "SysRole":
    #             continue
    #         result = get_most_complete_access_control_model(entry)
    #         if result is None:
    #             print(f"Error in  get_most_complete_access_control_model resource: {entry['resource']} operation_type {entry['operation_type']} ")
    #             continue
    #         complete_access_model = extract_result_from_response(result)
    #         complete_access_models.append({
    #             "resource": entry["resource"],
    #             "operation_type": entry["operation_type"],
    #             "most_complete_access_control_model": complete_access_model
    #         })
    #
    #     DataUtils.save_json(complete_access_model_path,complete_access_models)
    #
                                            
    # complete_access_models = DataUtils.load_json(complete_access_model_path)
    # for entry in data:
    #     if entry["resource"] == "SysRole":
    #         continue
    #     resource = entry["resource"]
    #     operation_type = entry["operation_type"]
                                                                                                    
    #     most_complete_access_control_model = []
    #     for complete_model in complete_access_models:
    #         if complete_model["resource"] == resource and complete_model["operation_type"] == operation_type:
    #             most_complete_access_control_model = complete_model["most_complete_access_control_model"]
    #             break
    #     for model in entry["access_control_model"]:
    #         result = get_lack_of_permission_check(most_complete_access_control_model, model)
    #         time.sleep(1)
    #         if result is None:
    #             print(f"Error in get_lack_of_permission_check resource: {entry['resource']} operation_type {entry['operation_type']} ")
    #             continue
    #         lack_of_permission_check = extract_result_from_response(result)
                                                                               
    #         model["missing_permission"] = lack_of_permission_check
    # DataUtils.save_json(output_access_control_model_path, data)

                      
    # for entry in data:
    #     if entry["resource"] != "SysUser" or entry["operation_type"] != "edit":
    #         continue
    #     # pdb.set_trace()
    #     result = get_diff_access_control_models(entry)
    #     if result is None:
    #         err_diff_access_control_models.append(entry['resource'])
    #         print(f"None diff_access_control_models {entry['resource']} operation_type {entry['operation_type']} ")
    #         continue
    #     # pdb.set_trace()
    #     diff_access_models = extract_result_from_response(result)
    #
    #     # pdb.set_trace()
    #
    #     # print("diff_access_models", diff_access_models)
    #
                               
    #     for diff_access_model in diff_access_models:
    #         # diff_access_model_data = {}
    #         resource_name = diff_access_model["resource"]
    #         operation_discription = diff_access_model["Operation Description"]
                                                                  
    #         for raw_entry in data:
    #             if raw_entry["resource"] == resource_name:
                                                             
    #                 for raw_model in raw_entry["access_control_model"]:
    #                     # print("raw_model", raw_model)
    #                     if raw_model["Operation Description"] == operation_discription:
    #                         existing_diff_access_models.append({
    #                             "resource": resource_name,
    #                             "operation_type": raw_entry["operation_type"],
    #                             **raw_model,
    #                             "Cause Analysis": diff_access_model["Cause Analysis"]
    #                         })
    #                         # diff_access_model["operation_type"] = raw_entry["operation_type"]
    #                         break
    #         # existing_diff_access_models.append(diff_access_model_data)
    #
    #     DataUtils.save_json(output_access_control_model_path,existing_diff_access_models)
    #
                   
    # DataUtils.save_json(diff_access_control_models_path,err_diff_access_control_models)

                
    # diff_models = DataUtils.load_json(output_access_control_model_path)
    # call_chains = DataUtils.load_json(call_chains_path)
    #
    # for diff_model in diff_models:
    #     code_item = call_chains[diff_model["resource"]][diff_model["location"]]
    #     code_snippet = code_item["code_snippet"]
    #     call_chain_code = code_item["call_chain_code_down"]
    #     # call_chain_code = code_item["call_chain_code"]
    #     # pdb.set_trace()
    #
    #     access_control_models = get_resource_all_access_control_models(diff_model,input_access_control_model_path)
    #     result = detect_access_control_vulnerabilities(diff_model, code_snippet, call_chain_code, access_control_models)
    #     # vulnerabilities = extract_result_from_response(result)
    #     # pdb.set_trace()
    #     # for vulnerability in vulnerabilities:
    #
                        
    #     existing_vulnerabilities_data = { key : value for key, value in diff_model.items() }
    #
    #     existing_vulnerabilities.append({
    #         **existing_vulnerabilities_data,
    #         "vulnerability": result
    #     })
    #     # existing_vulnerabilities.append({
    #     #     "resource": diff_model["resource"],
    #     #     "location": diff_model["location"],
    #     #     "operation_type": diff_model["operation type"],
    #     #     "operation_description": diff_model["Operation Description"],
    #     #     "Relevant code snippet": diff_model["Relevant code snippet"],
    #     #     "Cause Analysis": diff_model["Cause Analysis"],
    #     #     "Permission Requirements": diff_model["Permission Requirements"],
    #     #     "vulnerability": result
    #     # })
    #
    #     DataUtils.save_json(output_vulnerabilities_path,existing_vulnerabilities)


if __name__ == '__main__':
    main()
