import pdb
import sys
import os
import anthropic

# Add project root directory to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from openai import OpenAI
# from my_callchain import get_call_chain
# from build import get_call_chain,get_resources
import json
# import javalang
import re
# from utils import get_call_chain
from utils.path_util import PathUtil
from utils.data_utils import DataUtils
# from AccessControl.prompt_templates_mall import Prompt
from AccessControl.prompt_templates import Prompt

resources_path = PathUtil.resource_data("youlai-mall-master_resources", "json")
call_chains_path = PathUtil.call_chain_data("youlai_call_chains_up_down_47_bugcase", "json")
output_path = PathUtil.output_data("youlai_acm_claude37_430_1", "json")

# model_name = "deepseek-reasoner"
model_name = "gpt-4o-mini"

# client = {
#     "gpt-4o-mini": OpenAI(
                                                
#         base_url='https://api.openai-proxy.org/v1',
#         api_key='sk-VtA7M1oskIqT0PjjcUbuj0YYz6QOpSayYNqHbx77ehA9A06k'),
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
    api_key='sk-vQQVtY65hvKXajLVCe59759c33F34c79995eF96f6726E5A0'),
    "claude3.7":anthropic.Anthropic(
    # defaults to os.environ.get("ANTHROPIC_API_KEY")
    base_url='https://openkey.cloud/v1',
    api_key="sk-vQQVtY65hvKXajLVCe59759c33F34c79995eF96f6726E5A0")
}

prompt = Prompt()


# org_resource=[]
# org_location=[]
# LLM_org_response=[]

# client = OpenAI(api_key="sk-55cab67284374205bbe3f622b51e79e1", base_url="https://api.deepseek.com")
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

        try_times=0
        chat_completion = requests.post(url, headers=headers, json=data).json()
        while 'choices' not in chat_completion.keys():
            print(f"Network problem, {try_times+1} try")
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
    try:
        response = split_answer(response)
        print("\033[32m" + str(response) + "\033[0m")
    except:
        print("\033[33m" + "Error: " + response + "\033[0m")
    return response


def get_yes_or_no_answer_from_llm(messages, model_name):
    chat_completion = client[model_name].chat.completions.create(
        messages=messages,
        temperature=0.0000001,
        model=model_name
    )
    response = chat_completion.choices[0].message.content
    # LLM_org_response.append({"resource": org_resource[-1], "location": org_location[-1], "original answer": response})
    print("\033[31m" + response + "\033[0m")
    return response

def split_answer(answer):
    match = re.search(r'```json(.*?)```', answer, re.DOTALL)
    if match:
        oplist_str = match.group(1).strip()
        operation_list = json.loads(oplist_str)
        return operation_list


# answer="""Based on the provided code snippet for the `editSave` function and the contextual functions, we can identify the operations performed on the `SysUser` resource. Here are the extracted operations:

# 1. **Operation Type**: **edit**
#    **Operation Description**: "Updating user information including roles and posts."
#    **Relevant Code Snippet**: `return toAjax(userService.updateUser(user));`

# 2. **Operation Type**: **read**
#    **Operation Description**: "Checking if the login name is unique."
#    **Relevant Code Snippet**: `else if (StringUtils.isNotEmpty(user.getPhonenumber()) && !userService.checkPhoneUnique(user))`

# 3. **Operation Type**: **read**
#    **Operation Description**: "Checking if the phone number is unique."
#    **Relevant Code Snippet**: `else if (StringUtils.isNotEmpty(user.getEmail()) && !userService.checkEmailUnique(user))`

# 4. **Operation Type**: **read**
#    **Operation Description**: "Checking if the email is unique."
#    **Relevant Code Snippet**: `else if (StringUtils.isNotEmpty(user.getEmail()) && !userService.checkEmailUnique(user))`

# 5. **Operation Type**: **remove**
#    **Operation Description**: "Deleting user-role associations."
#    **Relevant Code Snippet**: `userRoleMapper.deleteUserRoleByUserId(userId);`

# 6. **Operation Type**: **create**
#    **Operation Description**: "Creating new user-role associations."
#    **Relevant Code Snippet**: `insertUserRole(user.getUserId(), user.getRoleIds());`

# 7. **Operation Type**: **remove**
#    **Operation Description**: "Deleting user-post associations."
#    **Relevant Code Snippet**: `userPostMapper.deleteUserPostByUserId(userId);`

# 8. **Operation Type**: **create**
#    **Operation Description**: "Creating new user-post associations."
#    **Relevant Code Snippet**: `insertUserPost(user);`

# Now, we will format these operations in JSON format:

# ```json
# [
#     {"Operation type": "edit", "Operation description": "Updating user information including roles and posts.", "Relevant code snippet": "return toAjax(userService.updateUser(user));"},
#     {"Operation type": "read", "Operation description": "Checking if the login name is unique.", "Relevant code snippet": "else if (StringUtils.isNotEmpty(user.getPhonenumber()) && !userService.checkPhoneUnique(user))"},
#     {"Operation type": "read", "Operation description": "Checking if the phone number is unique.", "Relevant code snippet": "else if (StringUtils.isNotEmpty(user.getEmail()) && !userService.checkEmailUnique(user))"},
#     {"Operation type": "read", "Operation description": "Checking if the email is unique.", "Relevant code snippet": "else if (StringUtils.isNotEmpty(user.getEmail()) && !userService.checkEmailUnique(user))"},
#     {"Operation type": "remove", "Operation description": "Deleting user-role associations.", "Relevant code snippet": "userRoleMapper.deleteUserRoleByUserId(userId);"},
#     {"Operation type": "create", "Operation description": "Creating new user-role associations.", "Relevant code snippet": "insertUserRole(user.getUserId(), user.getRoleIds());"},
#     {"Operation type": "remove", "Operation description": "Deleting user-post associations.", "Relevant code snippet": "userPostMapper.deleteUserPostByUserId(userId);"},
#     {"Operation type": "create", "Operation description": "Creating new user-post associations.", "Relevant code snippet": "insertUserPost(user);"}
# ]
# ```

# This JSON array captures all the operations performed on the `SysUser` resource within the `editSave` function."""
# print(split_answer(answer))
# answer='{"a":"b{c=a;}"}'
# a=split_answer(answer)

# file_path = '/home/fdse/hzc/LLM4VUL/RuoYi/ruoyi-admin/src/main/java/com/ruoyi/web/controller/demo/controller/DemoOperateController.java'
# function_name = 'importUser'

# case1:
# resorce: SysUser
# location:SysUserController: editsave
# case2:
# resorce: SysUser
# location:SysUserServiceImpl: importUser
# case3：
# resorce: SysDept
# location:SysDeptController: editSave
# case4：
# resorce: SysRole
# location:SysRoleController: editSave
# case5：
# resorce: SysUser
# location:SysUserController: remove
# case6：
# resorce: SysUser
# location:SysUserController: authRole


def get_access_control_model(resource, func_name, code_snippet, call_chains, call_chain_code):
    extract_operation_list_prompt = prompt.extract_operation_list_prompt(resource, func_name, code_snippet,
                                                                                  call_chains, call_chain_code)

    # pdb.set_trace()

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": extract_operation_list_prompt}
    ]
    operation_list = get_answer_from_llm(messages, model_name)

    extract_permission_requirements_prompt = prompt.extract_permission_requirements_prompt(resource, func_name,
                                                                                           code_snippet, call_chains,
                                                                                           call_chain_code,
                                                                                           operation_list)

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": extract_permission_requirements_prompt}]

    access_control_models = get_answer_from_llm(messages, 'claude3.7')


    try:
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
                            judge_code_prompt = prompt.judge_code_snippet( [code_snippet] + call_chain_code, permission['Relevant Code Snippet'])
                            messages = [
                                {"role": "system", "content": "You are a helpful assistant."},
                                {"role": "user", "content": judge_code_prompt}]
                            judge_res = get_yes_or_no_answer_from_llm(messages, model_name)
                            if judge_res == 'no':
                                for key in permission.keys():
                                    permission[key] = 'None'
                        model["Permission Requirements"][i] = permission
    except Exception as e:
        print(e)
        print(access_control_models)


    return access_control_models

    # return {"operation_list": operation_list, "permission_requirement": access_control_model}


def pipeline():
    extracted_resources = DataUtils.load_json(resources_path)
    call_chains = DataUtils.load_json(call_chains_path)

    # if output_path exists, load it
    if os.path.exists(output_path):
        result = DataUtils.load_json(output_path)
    else:
        result = []



            
    # resource_list = list(call_chains.keys())
    resource_list = ['Role','User']
    # location = "SysUserController.java:importData"
    # flag = 0
    for resource in resource_list:
        for location in call_chains[resource]:
            # try:
                # if location != "SysUserServiceImpl.java:changeStatus":
                #     continue
                if "check" in location:
                    continue    
                # if flag == 0:
                #     continue   
                # if not(resource=='SysDept' and location=='SysDeptController.java:treeDataExcludeChild'):
                #     continue
                # org_resource.append(resource)
                # org_location.append(location)
                code_item = call_chains[resource][location]
                model = get_access_control_model(resource, code_item["function_name"], code_item["code_snippet"],
                                                 [code_item["call_chain_down"] ,code_item["call_chain_up"] ],

                                                 [code_item["call_chain_code_down"],code_item["call_chain_code_up"]])
                result.append({"resource": resource, "location": location, "access_control_model": model})
                DataUtils.save_json(output_path, result)
            # except:
            #     print("\033[33m" + "Error: " + resource + " " + location + "\033[0m")
    # DataUtils.process_data(result,output_path)
    # # DataUtils.save_json(output_path,new_result)
    # DataUtils.save_json(original_path,LLM_org_response)


                                
if __name__ == "__main__":
    pipeline()
