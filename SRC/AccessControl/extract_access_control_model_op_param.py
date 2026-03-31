from logging import log
import pdb
import sys
import os
import argparse

# python AccessControl/extract_access_control_model_op_param.py
# Add project root directory to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from tqdm import tqdm
from openai import OpenAI
# from my_callchain import get_call_chain
# from build import get_call_chain,get_resources
import json
# import javalang
import re
# from utils import get_call_chain
from utils.path_util import PathUtil
from utils.data_utils import DataUtils
from AccessControl.prompt_templates import Prompt
# from AccessControl.get_callchain_by_op import extend_call_chain_by_opType
from dotenv import load_dotenv
from pathlib import Path

# parser = argparse.ArgumentParser(description="extract access control model from callchains")
#
# parser.add_argument("--model_name", type=str, required=True, help="Model name, e.g., Qwen3-32B")
# parser.add_argument("--resources_file", type=str, required=True, help="Resource file name")
# parser.add_argument("--call_chains_file", type=str, required=True, help="Call chain file name")
# parser.add_argument("--resource_list", nargs="+", required=False, help="List of resource types")
# parser.add_argument("--project_name", type=str, required=True, help="Scanned project name")
# parser.add_argument("--project_path", type=str, required=True, help="Absolute path of scanned project")
# args = parser.parse_args()
#
# model_name = args.model_name
# resources_file_name = args.resources_file
# call_chains_file_name = args.call_chains_file
# resource_list = args.resource_list
# project_name = args.project_name
# project_path = args.project_path

model_name="gpt-4o-mini"
resources_file_name="resources"
call_chains_file_name="RuoYi_call_chains_up_down_422"
resource_list=["SysDept"]
project_name="RuoYi"
project_path="/Users/huangzhuochen/IdeaProjects/RuoYi"
resources_path = PathUtil.resource_data(resources_file_name, "json")
call_chains_path = PathUtil.call_chain_data(call_chains_file_name, "json")
project_func_map_path = PathUtil.call_chain_data(f"{project_name}_func_map", "json")
project_func_map = DataUtils.load_json(project_func_map_path) if os.path.exists(project_func_map_path) else {}
output_path = PathUtil.output_data(project_name + '_acm_' + model_name, "json")

                                               
if resource_list is None:
    try:
        data = DataUtils.load_json(resources_path)
        resource_list = [str(item.get('Resource', '')).strip() for item in data if item.get('Resource')]
    except Exception as e:
        print(f"读取资源列表失败: {e}")
        resource_list = []
# --resource_list ResourceA ResourceB ResourceC
        
# resource_list = list(call_chains.keys())

          
current_file = Path(__file__).resolve()
env_file = current_file.parent / "../.env"
load_dotenv(env_file.resolve())

client = {
    "gpt-4o-mini": OpenAI(
        base_url="https://openkey.cloud/v1",
        api_key="sk-i9xfELTdbFKeeooi1516Ec93302448F8929a91294aB640Aa")}

# client = {
#     "gpt-4o-mini": OpenAI(
#         base_url=os.getenv("BASE_URL"),
#         api_key=os.getenv("GPT_4o_mini_KEY")),
#     "deepseek-reasoner": OpenAI(
#         api_key="sk-8f68830b4fb04ebda6267add4af148f3",
#         base_url="https://api.deepseek.com"),
#     "gpt-4o-2024-08-06": OpenAI(
#         base_url='https://openkey.cloud/v1',
#         api_key='sk-vQQVtY65hvKXajLVCe59759c33F34c79995eF96f6726E5A0'),
#     'Qwen3-32B': OpenAI(
#         api_key="DASHSCOPE_API_KEY",
#         base_url="http://70.181.3.224:9529/v1")
# }

# config=DataUtils.load_json("./config.json") if os.path.exists(project_func_map_path) else {}
# config["project_name"]=project_name
# config["project_path"]=project_path
# config["model_name"]=model_name
# config["client"]=client
# DataUtils.save_json("./config.json",config)

prompt = Prompt()


def get_judge_of_perimission_check(messages, model_name):
    chat_completion = client[model_name].chat.completions.create(
        messages=messages,
        temperature=0.0000001,
        model=model_name
    )
    response = chat_completion.choices[0].message.content

    # print("\033[31m" + response["is_privilege_check"] + "\033[0m")
    # return response["is_privilege_check"]
    response = split_answer(response)
    return response


def get_answer_from_llm(messages, model_name, resource, func_name):
    chat_completion = client[model_name].chat.completions.create(
        messages=messages,
        temperature=0.0000001,
        model=model_name
    )
    response = chat_completion.choices[0].message.content
    # print(response)
    if response == None:
        print(f'resource:{resource} func_name:{func_name} chat:{chat_completion}')
    # if resource=='Strategy' and func_name=='deleteStrategy':
    #    print(response)
    # LLM_org_response.append({"resource": org_resource[-1], "location": org_location[-1], "original answer": response})
    # print("\033[31m" + response + "\033[0m")
    try:
        json_response = split_answer(response)
        if json_response == None:
            print(f'resource:{resource} func_name:{func_name} split answer return None')
            print('\n' + response)
            json_response = json.loads(response[response.find('</think>') + 8:].strip())
        return json_response
        # print("\033[32m" + str(response) + "\033[0m")
    except Exception as e:
        print("\033[33m" + f"Error type: {type(e).__name__}, Error message: {str(e)}" + "\033[0m")
        print("\033[33m" + "Response content: " + str(response) + "\033[0m")
                               
        return []


def get_yes_or_no_answer_from_llm(messages, model_name):
    chat_completion = client[model_name].chat.completions.create(
        messages=messages,
        temperature=0.0000001,
        model=model_name
    )
    response = chat_completion.choices[0].message.content
    # LLM_org_response.append({"resource": org_resource[-1], "location": org_location[-1], "original answer": response})
    # print("\033[31m" + response + "\033[0m")
    return response


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

# split_answer("<think>```java ``` </think>```[]```")

def get_access_control_model(resource, func_name, code_snippet, call_chain_locs, call_chain_codes, insert_info=None):
    # print('here')
    extract_operation_list_prompt = prompt.extract_operation_list_prompt(resource, func_name, code_snippet,
                                                                         call_chain_locs, call_chain_codes)

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": extract_operation_list_prompt}
    ]
    operation_list = get_answer_from_llm(messages, model_name, resource, func_name)
    call_chain_down_locs = call_chain_locs[0]
    call_chain_down_codes = call_chain_codes[0]
                                                                 
    extended_call_chain_by_opType = []
    all_paths_of_bottom_func={}
    from AccessControl.get_callchain_by_op import extend_call_chain_by_opType
    for operation in operation_list:
        operation_type = operation["Operation Type"]
        operation_location = operation["Operation Location"]
                                                                         
        if operation_location in call_chain_locs[1] or operation_location==code_snippet["location"]:
            continue
        bottom_op_func_locs,path_of_func = extend_call_chain_by_opType(resource, operation_type, operation_location,
                                                          call_chain_down_locs, call_chain_down_codes)
                         
        for k,v in path_of_func.items():
            if k in all_paths_of_bottom_func.keys():
                all_paths_of_bottom_func[k].append(v)
            else:
                all_paths_of_bottom_func[k] = [v]
        extended_call_chain_by_opType.append({operation_type: bottom_op_func_locs})

    new_operation_list = []
                                            
    for opType_call_chain in extended_call_chain_by_opType:
        op_type = list(opType_call_chain.keys())[0]
        bottom_func_locs = opType_call_chain[op_type]
        bottom_func_codes = []
        for loc in bottom_func_locs:
            if loc in call_chain_locs[0]:
                bottom_func_codes.append(call_chain_codes[0][call_chain_locs[0].index(loc)])
                continue
            bottom_func_codes.append(project_func_map[loc]["code_snippet"])

        new_call_chain_locs = [call_chain_locs[0] + bottom_func_locs, call_chain_locs[1]]
        new_call_chain_codes = [call_chain_codes[0] + [{"location": loc, "code": code} for loc, code in
                                                       zip(bottom_func_locs, bottom_func_codes)], call_chain_codes[1]]
        extract_operation_type_prompt = prompt.extract_operation_type_prompt(resource, func_name, code_snippet,
                                                                             new_call_chain_locs, new_call_chain_codes,
                                                                             op_type)
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": extract_operation_type_prompt}
        ]
        res_operation_list = get_answer_from_llm(messages, model_name, resource, func_name)
        for i,op_info in enumerate(res_operation_list):
            op_info["Operation Type"]=op_type
            res_operation_list[i]=op_info
        new_operation_list += res_operation_list
    # print(new_operation_list)
    if new_operation_list==[]:
        new_operation_list=operation_list

           
    all_access_control_models=[]
    for operation in new_operation_list:
        new_call_chain_locs=[]
        new_call_chain_codes=[]
        operation_location=operation["Operation Location"]
                                                    
        if operation_location in list(all_paths_of_bottom_func.keys()):
            new_call_chain_down_locs=[]
            new_call_chain_down_codes=[]
                                         
            for path in all_paths_of_bottom_func[operation_location]:
                for loc in path:
                    new_call_chain_down_locs.append(loc)
            for loc in new_call_chain_down_locs:
                new_call_chain_down_codes.append(project_func_map[loc]["code_snippet"])
            if len(new_call_chain_down_locs)!=0:
                new_call_chain_down_locs=list(set(new_call_chain_down_locs))
            new_call_chain_locs=[call_chain_locs[0]+new_call_chain_down_locs, call_chain_locs[1]]
            new_call_chain_codes=[call_chain_codes[0]+[{"location": loc, "code": code} for loc, code in
                                                       zip(new_call_chain_locs, new_call_chain_down_codes)], call_chain_codes[1]]
                                                  
        else:
            new_call_chain_locs=call_chain_locs
            new_call_chain_codes=call_chain_codes
        extract_permission_requirements_prompt = prompt.extract_permission_requirements_prompt(resource, func_name,
                                                                                               code_snippet,
                                                                                               new_call_chain_locs,
                                                                                               new_call_chain_codes,
                                                                                               new_operation_list)
        external_knowledge_prompt = f"""
        Below you will find supplementary notes that clarify any special frameworks, annotations, or code fragments appearing in the provided call-chain:
        {insert_info}
        """

        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user",
             "content": extract_permission_requirements_prompt + '\n' + external_knowledge_prompt if insert_info != None else extract_permission_requirements_prompt}]

        access_control_models = get_answer_from_llm(messages, model_name, resource, func_name)
        if access_control_models == None or len(access_control_models) == 0:
            print(f'operation_list: {operation_list}')
            # print(f'resource:{resource} func_name:{func_name}')
            return []                   
        for model in access_control_models:
            if "Permission Requirements" in model:
                for i in range(len(model["Permission Requirements"])):
                    permission = model["Permission Requirements"][i]

                    for key in ["Relevant code snippet", "Relevant code Snippet", "Relevant Code snippet"]:
                        if key in permission:
                            permission["Relevant Code Snippet"] = permission.pop(key)
                            break

                    if "Relevant Code Snippet" in permission:

                        if permission["Relevant Code Snippet"] == "None":
                            for key in permission.keys():
                                permission[key] = 'None'
                        else:
                                                    
                            judge_code_prompt = prompt.judge_code_snippet([code_snippet] + call_chain_codes,
                                                                          permission['Relevant Code Snippet'])
                            messages = [
                                {"role": "system", "content": "You are a helpful assistant."},
                                {"role": "user", "content": judge_code_prompt}]
                            judge_res = get_yes_or_no_answer_from_llm(messages, model_name)

                            if judge_res == 'yes':
                                remove_None_privilege_check_operation = prompt.remove_None_privilege_check_operation(
                                    model["Relevant Code Snippet"], permission['Relevant Code Snippet'])
                                messages = [
                                    {"role": "system", "content": "You are a helpful assistant."},
                                    {"role": "user", "content": remove_None_privilege_check_operation}]
                                remove_res = get_judge_of_perimission_check(messages, model_name)     
                                # print("************************")
                                # print(remove_res)
                                # print("************************")
                                if remove_res["is_privilege_check"] == 'no':
                                    for key in permission.keys():
                                        permission[key] = 'None'

                            if judge_res == 'no':
                                for key in permission.keys():
                                    permission[key] = 'None'
                        model["Permission Requirements"][i] = permission
        all_access_control_models+=access_control_models
    return all_access_control_models

    # return {"operation_list": operation_list, "permission_requirement": access_control_model}


def process_path_info(path):
                      
    path = path.split("/")[1]
    path = path.split("/")[0]
    return path


def get_insert_info(corpus_path, code_item):
    insert_annotations_info = []
    corpus = DataUtils.load_json(corpus_path)
    corpus_annotations = []
    for info in corpus:
        corpus_annotations.append(list(info.keys())[0])
    callchain_annotations = code_item["annotation_down"] + code_item["annotation_up"]
    # print(callchain_annotations)
    for func_annotations in callchain_annotations:
        for func_annotation in func_annotations:
            for corpus_annotation in corpus_annotations:
                if corpus_annotation.lower() in func_annotation.lower():
                    for info in corpus:
                        if list(info.keys())[0] == corpus_annotation:
                            insert_annotations_info.append(info)
                    break
    print(insert_annotations_info)
    return insert_annotations_info


def find_exist(result: json, resource: str, location: str) -> bool:
    for item in result:
        if item.get("resource") is not None and item.get("location") is not None:
            if resource == item["resource"] and location == item["location"]:
                return True
    return False


def escape_quotes_in_data(data):
    """
    递归转义数据中的双引号
    如果是字符串，转义双引号
    如果是列表，递归处理每个元素
    如果是字典，递归处理每个值
    """
    if isinstance(data, str):
        return data.replace('"', '\\"')
    elif isinstance(data, list):
        return [escape_quotes_in_data(item) for item in data]
    elif isinstance(data, dict):
        return {key: escape_quotes_in_data(value) for key, value in data.items()}
    else:
        return data

def post_process_acm(access_control_models):
    processed_acm = []
    for func_res in access_control_models:
        print(func_res)
        new_func_res=func_res
        func_location=func_res['location']
        resource=func_res['resource']
        access_control_model=func_res['access_control_model']
        operate_locations={}
        operate_code_snippets={}
        remove_index=[]
        for i,each_operation in enumerate(access_control_model):
            operate_locations[each_operation['Operation Location']]=i
            operate_code_snippets[each_operation['Relevant Code Snippet']]=i
        for operate_loc in operate_locations.keys():
            code_type=operate_loc.replace('java:','')
            for code_snippet in operate_code_snippets.keys():
                                                       
                if code_type.lower() in code_snippet.lower():
                    remove_index.append(operate_code_snippets[code_snippet])
                                                   
                else:
                    operate_func_name=operate_loc.split(':')[1]
                    key_code_snippet=code_snippet
                    if '=' in code_snippet:
                        code_snippet=code_snippet.split('=')[1]
                    func_index=code_snippet.lower().find(operate_func_name.lower())
                    bracket_index=func_index+len(operate_func_name)
                    if func_index!=-1 and code_snippet[bracket_index]=='(' and func_index==0:
                        remove_index.append(operate_code_snippets[key_code_snippet])
        new_access_control_model=[]
        for i,each_operation in enumerate(access_control_model):
            if i not in remove_index:
                new_access_control_model.append(each_operation)
        new_func_res['access_control_model']=new_access_control_model
        processed_acm.append(new_func_res)
    return processed_acm

def pipeline():
    extracted_resources = DataUtils.load_json(resources_path)
    call_chains = DataUtils.load_json(call_chains_path)

    # if output_path exists, load it
    if os.path.exists(output_path):
        result = DataUtils.load_json(output_path)
    else:
        result = []

    for resource in tqdm(resource_list):
        if resource not in call_chains:
            continue
        for location in call_chains[resource]:
            if find_exist(result, resource, location):
                print(f"{resource} {location} exist, pass!")
                continue
            # try:
            if location!='SysDeptController.java:addSave':
               continue
            print(f'{resource}    {location}')
            if location.split(':')[1].lower().startswith("check") or (
                    'do' in location.split(':')[1].lower() and 'auth' in location.split(':')[1].lower()):
                continue

            code_item = call_chains[resource][location]
            # print(code_item)

            # insert_annotations_info=get_insert_info(corpus_path,code_item)
            insert_annotations_info = None
                                                                  
                                      
                              
            code_item["code_snippet"] = escape_quotes_in_data(code_item["code_snippet"])
            code_item["call_chain_down"] = escape_quotes_in_data(code_item["call_chain_down"])
            code_item["call_chain_up"] = escape_quotes_in_data(code_item["call_chain_up"])
            code_item["call_chain_code_down"] = escape_quotes_in_data(code_item["call_chain_code_down"])
            code_item["call_chain_code_up"] = escape_quotes_in_data(code_item["call_chain_code_up"])

            sink_func_code = {"location": location, "code": code_item["code_snippet"]}
            call_chain_locations = [code_item["call_chain_down"], code_item["call_chain_up"]]
            call_chain_codes = [code_item["call_chain_code_down"], code_item["call_chain_code_up"]]
            merge_loc_code_down = []
            merge_loc_code_up = []
            for loc, code in zip(call_chain_locations[0], call_chain_codes[0]):
                merge_loc_code_down.append({"location": loc, "code": code})
            for loc, code in zip(call_chain_locations[1], call_chain_codes[1]):
                merge_loc_code_up.append({"location": loc, "code": code})
            # for i, code in enumerate(call_chain_codes):
            #     call_chain_codes[i] = {"location": call_chain_locations[i], "code": code}

            model = get_access_control_model(resource, code_item["function_name"], sink_func_code,
                                             call_chain_locations,
                                             [merge_loc_code_down, merge_loc_code_up],
                                             insert_annotations_info)

            result.append({"resource": resource, "location": location, "access_control_model": model,
                           "path_info": process_path_info(code_item["full_path"]),
                           "full_path": code_item["full_path"]})
            DataUtils.save_json(output_path, result)

    access_control_models = DataUtils.load_json(output_path)
    processed_acm = post_process_acm(access_control_models)
    DataUtils.save_json(output_path, processed_acm)


                                
if __name__ == "__main__":
    pipeline()

