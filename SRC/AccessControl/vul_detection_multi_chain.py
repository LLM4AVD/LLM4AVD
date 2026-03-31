                                      
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
from AccessControl.prompt_templates_618 import Prompt
from tqdm import tqdm


from openai import OpenAI

#python AccessControl/vul_detection.py

model_name = "Qwen3-32B"
# model_name = "gpt-4o-mini"


access_model_path = PathUtil.output_data("prm-newest_acm_1021"+model_name, "json")
                          
input_access_control_model_path = PathUtil.output_data("prm-newest_processed_models_1021", "json")
                                                  
complete_access_model_path = PathUtil.output_data("prm-newest_complete_models_1021", "json")
                
output_access_control_model_path = PathUtil.output_data("prm-newest_diff_models_1021"+model_name , "json")
                                    
output_missing_operation_path = PathUtil.output_data("prm-newest_missing_operation_1021", "json")
            
after_reducing_false_positives_path = PathUtil.output_data("prm-newest_final_result_1021", "json")
                  
false_positives_path = PathUtil.output_data("prm_Busi_BusiBase_false_positives_result_811", "json")

corpus_path=PathUtil.output_data("Annotation_summary","json")
enable_rag=False

          
call_chains_path = PathUtil.call_chain_data("prm-newest_call_chains_up_down_1021", "json")
multi_call_chain_path=PathUtil.call_chain_data("It2Case3Gw", "json")
enable_multi_call_chain=False
      
resource_list =  ['Document', 'ApplicationRole', 'Application']



prompt = Prompt()

client = {
    "gpt-4o-mini": OpenAI(
                                                                                  
    # base_url='https://api.openai-proxy.org/v1',
    base_url='https://openkey.cloud/v1',
    api_key='sk-vQQVtY65hvKXajLVCe59759c33F34c79995eF96f6726E5A0'),
    "deepseek-reasoner": OpenAI(api_key="sk-8f68830b4fb04ebda6267add4af148f3", base_url="https://api.deepseek.com"),
    "gpt-4o-2024-08-06": OpenAI(
                                                                                  
    # base_url='https://api.openai-proxy.org/v1',
    base_url='https://openkey.cloud/v1',
    api_key='sk-vQQVtY65hvKXajLVCe59759c33F34c79995eF96f6726E5A0'),
    "Qwen3-32B":OpenAI(
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
    #print(response)
    return response


def extract_result_from_response(result):
    if not isinstance(result, str):
        #print(type(result))
        #print(result)
        return []
    match = re.search(r'```json(.*?)```', result, re.DOTALL)
    if match:
        result_str = match.group(1).strip()
                                    
        if result_str == "{None}":
            return []
        #result_str=result_str.replace('\\','\\\\')
        #print(result_str)
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
            {"role": "user", "content": f"Here is the incoming list of permission-check items awaiting categorization:\n {all_permissions}"},
        ]
        result = get_answer_from_llm(messages, model_name)
        #print(f"Get one result:\n {result}")
        match = re.search(r'(?:\"\"\"|```json)(.*?)(?:\"\"\"|```)', result, re.DOTALL)
        if match:
            return result
        else:
            count+=1
            continue


def has_equivalent_permission(model, missing_permission_requirements):
    max_count = 3          
    detect_prompt = prompt.has_equivalent_permission_prompt(model, missing_permission_requirements)

    for count in range(max_count):
        print(f'has_equivalent_permission count {count}')
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
                return result_str
            except json.JSONDecodeError as e:
                print(f"JSON 解析失败（第 {count + 1} 次尝试）：{e}")
                continue           
        else:
            continue

def has_permission_in_call_chain(model, missing_permission_requirements, call_chain_code,insert_info=None):
    max_count = 3          
    detect_prompt = prompt.has_permission_in_call_chain_prompt(model, missing_permission_requirements, call_chain_code)
    external_knowledge_prompt=f"""
    ###Additional information
        Below you will find **supplementary notes** that clarify any special frameworks, annotations, or code fragments appearing in the provided call-chain:
        {insert_info}
    """
    for count in range(max_count):
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": detect_prompt+'\n'+external_knowledge_prompt if insert_info!=None else detect_prompt},
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
                return result_str
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


def model_classification_by_operation_type(models, output_file,resources):
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


def find_complete_access_control_model(resource, operation_type, complete_access_models):
                                                                                              
    relevant_complete_permissions = []
    for complete_model in complete_access_models:
        if complete_model["resource"] == resource and complete_model["operation_type"] == operation_type :
            relevant_complete_permissions = complete_model["complete_permissions"]
            break
    return relevant_complete_permissions

def find_missing_requirements(permission_list, relevant_complete_permissions):
    code_permission_list = {item["Relevant Code Snippet"] for item in permission_list}
                                                                         
    missing_permissions = []
    #print(f"relevant:\n{relevant_complete_permissions}")
    for permission_set_all in relevant_complete_permissions:
        permission_set = permission_set_all["missing_permission_requirements"]
        #for permission in permission_set:
        #    print(f"permission:{permission}")
        
        for permission in permission_set:
            if "Permission Requirements" not in permission.keys():
                permission["Permission Requirements"]={"Description":"None","Details":"None","Relevant Code Snippet":"None","Detailed Code Snippet":"None"}
            if permission["Permission Requirements"]["Relevant Code Snippet"] not in code_permission_list:
                missing_permissions.append(permission_set_all)
                break
        # if not any(permission["Permission Requirements"]["Relevant Code Snippet"] in code_permission_list for permission in
        #            permission_set):
        #     missing_permissions.append(permission_set_all)
    return missing_permissions


def handle_similarity_check():
    data = DataUtils.load_json(input_access_control_model_path)
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

def get_insert_info(corpus_path,code_item,enable_rag):
    if not enable_rag:
        return None
    insert_annotations_info=[]
    corpus=DataUtils.load_json(corpus_path)
    corpus_annotations=[]
    for info in corpus:
        corpus_annotations.append(list(info.keys())[0])
    callchain_annotations=code_item["annotation_down"]+code_item["annotation_up"]
    for func_annotations in callchain_annotations:
        for func_annotation in func_annotations:
            for corpus_annotation in corpus_annotations:
                if corpus_annotation.lower() in func_annotation.lower():
                    for info in corpus:
                        if list(info.keys())[0]==corpus_annotation:
                            insert_annotations_info.append(info)
                    break
    print(insert_annotations_info)
    return insert_annotations_info

def get_multi_chain(multi_call_chain_data,resource,location):
    multi_chain_locs=[]
    multi_chain_codes=[]
    for chain_data in multi_call_chain_data:
        if not(chain_data["resource"] == resource and chain_data["location"]==location):
            continue
        else:
            sink_location=chain_data["location"]
            sink_func_name=chain_data["func_name"]
            sink_file_path=chain_data["file_path"]
            sink_func_code=chain_data["code"]
            for i in range(len(chain_data["annotation"])-1,-1,-1):         
                sink_func_code=chain_data["annotation"][i]+'\n'+sink_func_code
            all_down_chain_code=[]                          
            all_down_chain_loc=[]
                                    
            for down_chain in chain_data["call_chain_down"]:                       
                down_chain_location=[]
                down_chain_code=[]
                for layer_down in range(len(down_chain)):
                    if layer_down==len(down_chain)-1:
                        last_layer_location=[loc.split('/')[-1] for loc in down_chain[layer_down][0][0]]
                        down_chain_location.append(last_layer_location)
                        down_chain_code.append(down_chain[layer_down][0][1])
                    else:
                        down_chain_location.append(down_chain[layer_down][0][0].split('/')[-1])
                        down_chain_code.append(down_chain[layer_down][0][1])
                all_down_chain_code.append(down_chain_code)
                all_down_chain_loc.append(down_chain_location)
            all_up_chain_code=[]
            all_up_chain_loc=[]
                                    
            for up_chain in chain_data["call_chain_up"]:
                up_chain_location=[]
                up_chain_code=[]
                for layer_up in range(len(up_chain)):
                    if layer_up==len(up_chain)-1:
                        last_layer_location=[loc.split('/')[-1] for loc in up_chain[layer_up][0][0]]
                        up_chain_location.append(last_layer_location)
                        up_chain_code.append(up_chain[layer_up][0][1])
                    else:
                        up_chain_location.append(up_chain[layer_up][0][0].split('/')[-1])
                        up_chain_code.append(up_chain[layer_up][0][1])
                all_up_chain_code.append(up_chain_code[::-1])
                all_up_chain_loc.append(up_chain_location[::-1])
                                      
            for index1,down_chain_loc in enumerate(all_down_chain_loc):
                down_chain_code=all_down_chain_code[index1]
                for index2,up_chain_loc in enumerate(all_up_chain_loc):
                    up_chain_code=all_up_chain_code[index2]
                    # multi_chain_loc=up_chain_loc+[sink_location]+down_chain_loc
                    # multi_chain_code=up_chain_code+[sink_func_code]+down_chain_code
                    # multi_chain=[multi_chain_loc,multi_chain_code]
                    multi_chain_locs.append(up_chain_loc+[sink_location]+down_chain_loc)
                    multi_chain_codes.append(up_chain_code+[sink_func_code]+down_chain_code)

            return (multi_chain_locs,multi_chain_codes)

def pipeline():
                                
    print("********************************")
    # if input_path exist:
    if PathUtil.exists(input_access_control_model_path):
        print("processed_data exists!")
        print("&&&&&&&&&&&&&&&&&&&&&&&********************************")
    else:
        models = DataUtils.load_json(access_model_path)
                   
        model_classification_by_operation_type(models, input_access_control_model_path,resource_list)

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
            #print(all_permissions)
                          
            result = remove_duplicate_permission_permissions(all_permissions)
            all_permissions_new = extract_result_from_response(result)

            all_permissions_new = add_operation_info(entry, all_permissions_new)

            complete_access_models.append({
                "resource": entry["resource"],
                "operation_type": entry["operation_type"],
               # "role_type": entry["role type"],
                "complete_permissions": all_permissions_new
            })

                    
        for complete_access_model in complete_access_models:
            new_complete_access_models = []
            for permission_set in complete_access_model["complete_permissions"]:
                result = summarize_permissions(permission_set)
                permission_description = extract_result_from_response(result)
                new_permission_set = {
                    "permission_description":"None" if permission_description==[] else permission_description["permission_description"],
                    "missing_permission_requirements": permission_set
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


          
    print("=================false positive elimination============")
    data_1 = DataUtils.load_json(output_access_control_model_path)
    old_data_1=data_1
    data_2 = DataUtils.load_json(output_access_control_model_path)
    call_chains_data = DataUtils.load_json(call_chains_path)
    print(len(data_1))
    for i, item in tqdm(enumerate(data_1)):
        resource = item["resource"]
        if resource not in resource_list:
            continue
        #print(resource)
        access_control_models = item["access_control_model"]
        real_bug = []
        false_positives = []
        for j, model in enumerate(access_control_models):
            #if not(model["location"]=="DataTableServiceImpl.java:deleteByTableId") and not(model["location"]=="ResourceConfigServiceImpl.java:batchUpdateResourceMapConfig"):
                #continue
            print(model["location"])
            location=model["location"]
            length=len(model["missing_permission"])
            for k, missing_permission in enumerate(model["missing_permission"]):
                print(f"{k+1}    {length}")
                result_equivalent_operation={}
                cnt=0
                while ("is_operation_equivalent" not in result_equivalent_operation.keys() or "reason_for_is_operation_equivalent" not in result_equivalent_operation.keys()) and cnt<5:
                    result_equivalent_operation = has_equivalent_operation(model, missing_permission["missing_permission_requirements"])
                    #print(f'op result:\n{op_result}')
                    #result_equivalent_operation = extract_result_from_response(op_result)
                    if not isinstance(result_equivalent_operation,dict):
                        print(f'result_equivalent_operation:\n{result_equivalent_operation}')
                        result_equivalent_operation={}
                        continue
                    cnt+=1
                print(f'result_equivalent_operation:\n{result_equivalent_operation}')
                result_equivalent_permission={}
                cnt=0
                while (
                        "has_equivalent_permission" not in result_equivalent_permission.keys() or "reason_for_has_equivalent_permission" not in result_equivalent_permission.keys()) and cnt < 5:
                    result_equivalent_permission = has_equivalent_permission(model,
                                                              missing_permission["missing_permission_requirements"])
                    #print(f'permission:\n{permission_result}')
                    #result_equivalent_permission = extract_result_from_response(permission_result)
                    if not isinstance(result_equivalent_permission,dict):
                        result_equivalent_permission={}
                        cnt+=1
                        continue
                    cnt+=1
                print(f" result_equivalent_permission:\n{result_equivalent_permission}")
                
                                                   
                code_item=call_chains_data[resource][model["location"]]
                insert_annotations_info=get_insert_info(corpus_path,code_item,enable_rag)

                multi_call_chain_data=DataUtils.load_json(multi_call_chain_path)
                multi_call_chain=get_multi_chain(multi_call_chain_data,resource,location)
                multi_chain_locs=multi_call_chain[0]
                multi_chain_codes=multi_call_chain[1]

                missing_permission["result"]=defaultdict(list)
                for multi_chain_loc,multi_chain_code in zip(multi_chain_locs,multi_chain_codes):
                    multi_chain=[multi_chain_loc,multi_chain_code]
                    result_permission_in_call_chain=[{}]
                    cnt=0
                    while ("has_equivalent_permission_in_call_chain" not in result_permission_in_call_chain[0].keys() or "is_irrelevant_permission" not in result_permission_in_call_chain[0].keys()) and cnt < 5:
                        pr_in_call_chain_result = has_permission_in_call_chain(model, missing_permission[
                            "missing_permission_requirements"], multi_chain,insert_annotations_info)
                        result_permission_in_call_chain = extract_result_from_response(pr_in_call_chain_result)
                        #print(f'result_permission_in_call_chain:{result_permission_in_call_chain}')
                        if not isinstance(result_permission_in_call_chain,list):
                            result_permission_in_call_chain=[result_permission_in_call_chain]
                        if not isinstance(result_permission_in_call_chain[0],dict):
                            result_permission_in_call_chain[0]={}
                            continue
                        cnt+=1
                        #print(f'type:{type(result_permission_in_call_chain)}')
                    result_equivalent_permission_operation = {
                        "has_equivalent_permission": result_equivalent_permission["has_equivalent_permission"],
                        "reason_for_has_equivalent_permission": result_equivalent_permission[
                            "reason_for_has_equivalent_permission"],
                        "is_operation_equivalent": result_equivalent_operation["is_operation_equivalent"],
                        "reason_for_is_operation_equivalent": result_equivalent_operation[
                            "reason_for_is_operation_equivalent"],
                        "permission_in_call_code": result_permission_in_call_chain,
                    }
                    print(f"result_equivalent_permission_operation:{result_equivalent_permission_operation}")
                    all_no = all((result_item["has_equivalent_permission_in_call_chain"] == "no" and result_item["is_irrelevant_permission"]=="no") for result_item in
                                result_permission_in_call_chain)

                    if result_equivalent_permission_operation["has_equivalent_permission"] == "no" and\
                            result_equivalent_permission_operation["is_operation_equivalent"] == "yes" and not all_no:
                        missing_permission["result"]["is_not_vul"].append(result_equivalent_permission_operation)
                        real_bug.append(model)
                        break

                    if result_equivalent_permission_operation["has_equivalent_permission"] == "no" and\
                            result_equivalent_permission_operation["is_operation_equivalent"] == "yes" and all_no:
                                             
                        missing_permission["result"]["is_vul"].append(result_equivalent_permission_operation)
                        real_bug.append(model)
                        continue

        item["access_control_model"] = real_bug
        data_2[i]["access_control_model"] = false_positives
    DataUtils.save_json(after_reducing_false_positives_path, data_1)
    #DataUtils.save_json(false_positives_path, data_2)

if __name__ == '__main__':
    pipeline()
