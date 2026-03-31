"""
Manually find and annotate the documents most relevant to the large model for summarization. Not using BM25 RAG
"""

import pdb
import sys
import os
from RAG_rank import BM25_rank
# Add project root directory to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)
import openai
from tqdm import tqdm
from openai import OpenAI

import json
# import javalang
import re
# from utils import get_call_chain
from utils.path_util import PathUtil
from utils.data_utils import DataUtils
from AccessControl.prompt_templates import Prompt

summary_path = PathUtil.output_data("Annotation_summary", "json")


def annotation_summary(document_info):
    return f"""
    ### Task Description
    Below are the introductory documentation for an annotation. Based on this information, please answer two questions:
    **1.What Permission does this annotation perform?**
    Concisely summarize the permission-checking features that the annotation provides. 
    If the annotation performs multiple types of permission checks (e.g., whether the user has the required operation permission on the target resource, whether the user is an administrator, etc.), list **every** distinct check, do **not** omit any.
    **2.How is the check executed when the annotation is triggered?**
    Describe the **exact execution flow** of the permission check when the annotation is triggered.
    Describe as much as possible the annotation check **whether the user has permission to perform a certain action on a resource**
    For example, if the annotation has two attributes `resource` and `operation`, and when `resource=menu` and `operation=add`, the annotation inspects the user's token to verify that the current user is allowed to add a menu.
    ### Output Format
        The summary must be in the following JSON format:
        ```json
        {{
            "@annotation": 
                {{
                "Summary":"summary of the permission-checking features",
                "Execution Process":"execution flow of the annotation"
                }}
        }}
        ```
    ###Example Output
        ```json
        {{
            "@RequiresPermissions": 
                {{
                "Summary":"@RequiresPermissions annotations are a method-level permission control mechanism provided by Apache Shiro that declares the permissions required to call a method, usually a business interface or controller method. When applied on a method or class, Shiro checks the permissions of the current user before the method is executed: the method will only be executed if the current user is authenticated and their permission set contains a permission string specified by the comment (e.g., "user:create", "order:delete", etc.); Otherwise, Shiro will throw an UnauthorizedException or AuthorizationException to block unauthorized access. In this way, developers can implement refined access control in a declarative manner, decoupling permission logic from business logic, and enhancing system security and maintainability.",
                "Execution Process":"If @RequiresPermissions is used on a method or class, Shiro will check whether the current user has the corresponding permission before the method is executed, based on the permission representation in the comment. The method will only be executed if the user's permission collection contains the permission identification string, otherwise Shiro will throw an UnauthorizedException to prevent the user from doing so. For example, if you use @RequiresPermissions("order:delete") on a method or class, then when the user calls the method, Shiro checks whether the current user has the exact permission identifier "order:delete" before the method is executed, thus enabling access control to the "order deletion" feature."
                }}
        }}
        ```
    ### Note
    If you believe the provided content is **not** related to the specific annotation, output **only** the word `None` and do **not** add any extra text.
    

    ###Documentation
    Here is the introductory documentation:
    {document_info}

"""


client = {
    "gpt-4o-mini": OpenAI(
                                                                                      
        # base_url='https://api.openai-proxy.org/v1',
        base_url='https://openkey.cloud/v1',
        api_key=''),
    "deepseek-reasoner": OpenAI(api_key="", base_url="https://api.deepseek.com"),
    "gpt-4o-2024-08-06": OpenAI(
                                                                                      
        # base_url='https://api.openai-proxy.org/v1',
        base_url='https://openkey.cloud/v1',
        api_key=''),
    'Qwen3-32B': OpenAI(
        api_key="DASHSCOPE_API_KEY",
        base_url="http://70.181.3.224:9529/v1")
    # base_url="http://10.31.150.57:4000/v1")
}


def split_answer(answer):
    match = re.search(r'```json(.*?)```', answer, re.DOTALL)
    if match:
        oplist_str = match.group(1).strip()
        operation_list = json.loads(oplist_str)
        return operation_list


def get_answer_from_llm(messages, model_name, resource=None, func_name=None):
    chat_completion = client[model_name].chat.completions.create(
        messages=messages,
        temperature=0.0000001,
        model=model_name
    )
    response = chat_completion.choices[0].message.content
    #print(response)
    if response == None:
        print(f'resource:{resource} func_name:{func_name} chat:{chat_completion}')
    try:
        json_response = split_answer(response)
        if json_response == None:
            print(f'resource:{resource} func_name:{func_name} split answer return None')
            print('\n' + response)
            json_response = json.loads(response[response.find('</think>') + 8:].strip())
        return json_response
    except:
        print("\033[33m" + "Error: " + response + "\033[0m")


def summary_rag_res(document_info):
    annotation_path=PathUtil.output_data("Annotation_summary", "json")
    annotations=DataUtils.load_json(annotation_path)


    model_name = "Qwen3-32B"
    summary_annotation_prompt = annotation_summary(document_info)

    # pdb.set_trace()

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": summary_annotation_prompt}
    ]
    llm_summary = get_answer_from_llm(messages, model_name)
    print(f"llm_summary:{llm_summary}")
    if llm_summary!=None:
        #print("append")
        annotations.append(llm_summary)
        print(annotations)
        DataUtils.save_json(summary_path, annotations)

#RAG_res_path='./doc_info'
#file_list=[]
#for root, _,files in os.walk(RAG_res_path):
#    for name in files:
#        file_list.append(os.path.join(root,name))
#print(file_list)
#for file in file_list:
#    file_info=open(file,'r').read()
#    summary_rag_res(file_info)
search_data_path='./doc_info/JalorDoc.txt'
rank_res=BM25_rank(search_data_path)
for info in rank_res:
    summary_rag_res(info)

