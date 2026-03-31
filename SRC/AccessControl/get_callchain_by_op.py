import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from utils.path_util import PathUtil
from utils.data_utils import DataUtils
import javalang
from functools import lru_cache
from callchainTools.utils import get_callchain_down
from AccessControl.extract_access_control_model_op_param import model_name,client,project_name,project_path,get_answer_from_llm
import json
from collections import defaultdict

# config=DataUtils.load_json("./config.json") if os.path.exists("./config.json") else {}
# project_name=config["project_name"]
# project_path=config["project_path"]
# model_name=config["model_name"]
# client=config["client"]


cpg_path=f"../callchainTools/{project_name}_cpg.bin"


project_func_map_path=PathUtil.call_chain_data(f"{project_name}_func_map","json")
project_func_map=DataUtils.load_json(project_func_map_path) if os.path.exists(project_func_map_path) else {}



def find_filepath(file_name):
    for root,dirs,files in os.walk(project_path):
        for file in files:
            if file==file_name:
                return os.path.join(root,file)
    return None

# cpg_path=find_filepath(f"{project_name}_cpg.bin")

# def get_answer_from_llm(messages, model_name):
#     chat_completion = client[model_name].chat.completions.create(
#         messages=messages,
#         temperature=0.0000001,
#         model=model_name
#     )
#     response = chat_completion.choices[0].message.content
#     try:
#         format_response = json.loads(response)
#         return format_response
#         # print("\033[32m" + str(response) + "\033[0m")
#     except Exception as e:
#         print("\033[33m" + f"Error type: {type(e).__name__}, Error message: {str(e)}" + "\033[0m")
#         print("\033[33m" + "Response content: " + str(response) + "\033[0m")
                                 
#         return []

def get_callees(func_loc,func_code_snippet,resource,cpg_path):
    file_name=func_loc.split(':')[0]
    func_name=func_loc.split(':')[1]
    file_path=find_filepath(file_name)
    call_chain_down=get_callchain_down(project_path,project_name,file_path,func_name,resource,cpg_path)
    if call_chain_down==None or len(call_chain_down[0])==1 or call_chain_down==([],[],[]):
        return None
    callee_locs=call_chain_down[0][1:]
    callee_code_snippets=call_chain_down[1][1:]
    callee_annotations=call_chain_down[2][1:]

                                                
    if func_loc in project_func_map.keys():
        func_loc_callees=project_func_map[func_loc]["callees"] if project_func_map[func_loc]["callees"]!=None else []
        for callee_loc in callee_locs:
            if callee_loc not in func_loc_callees:
                project_func_map[func_loc]["callees"].append(callee_loc)
    else:
        project_func_map[func_loc]={"callers":[],"callees":callee_locs,"code_snippet":call_chain_down[1][0],"annotations":call_chain_down[2][0]}


    for callee_loc,callee_code_snippet,callee_annotation in zip(callee_locs,callee_code_snippets,callee_annotations):
                                                                                                                        
        if callee_loc in list(project_func_map.keys()):
            callers=project_func_map[callee_loc]["callers"]
            if func_loc in callers:
                continue
            else:
                project_func_map[callee_loc]["callers"].append(func_loc)
        else:
            project_func_map[callee_loc]={"callers":[func_loc],"callees":[],"code_snippet":callee_code_snippet,"annotations":callee_annotations}

        DataUtils.save_json(project_func_map_path,project_func_map)
        if callee_code_snippet=='':
            continue
        get_callees(callee_loc,callee_code_snippet,resource,cpg_path)

                 
os.environ["PATH"] = "/Users/huangzhuochen/bin/joern/joern-cli:" + os.environ["PATH"]

operation_desc={
    "find":"includes finding, getting, querying, selecting etc. Any operation of getting, searching ,accessing and "
           "returning an object is considered to be fall into this category",
    "create":"includes adding, saving, etc. new entries",
    "edit":"includes various editing operations such as updating, modifying, importing, etc.",
    "remove":"includes all delete operations"
}
def LLM_PROMPT(one_layer_of_callees,resource,operation_type):
    return f"""
            ### Task Description  
            I will provide you with a JSON dictionary that maps function identifiers to their source code.  
            Your job is to determine whether any of these functions performs **{operation_type}** operation on **{resource}**, where **{operation_type}** is defined as {operation_desc[operation_type]}.  
            
            If you decide that a function does indeed perform **{operation_type}** on **{resource}**, collect the dictionary key that identifies this function.  
            Return **all** such keys in a single list; if no function satisfies the requirement, return an empty list `[]`.
            
            ### Example Input  
            ```json
            {{"fileA:func_A": "code_A", "fileB:func_B": "code_B", "fileC:func_C": "code_C"}}
            ```
            
            ### Example Output (strictly follow this format without any extra text)  
            ```json
            ["fileA:func_A", "fileB:func_B"]
            ```
            
            Next, I will send you the actual dictionary to inspect:
            '''
            {one_layer_of_callees}
            '''
"""

# operation_cls_by_type=defaultdict(list)
# op_locs_in_op_list=[]
# for op_info in operation_list:
#     operation_cls_by_type.setdefault(op_info["Operation Type"],[]).append(op_info["Operation Location"])
#     op_locs_in_op_list.append(op_info["Operation Location"])


# for resource,locations in call_chains.items():
#     for location, call_chain in locations.items():
#         if location!='SysDeptController.java:addSave':
#             continue

# resource=""
                                                                                    
# operation_location=""
# operation_type=""
                  
# call_chain_down_locs=[]
# call_chain_down_codes=[]

def extend_call_chain_by_opType(resource,operation_type,operation_location,call_chain_down_locs,call_chain_down_codes):

    final_result_func_locs=[]
                          
    path_of_func = {}
                                                                           
    callers_loc_of_func = {}
    for call_chain_location_down,call_chain_code_down in zip(call_chain_down_locs,call_chain_down_codes):
        if call_chain_location_down == operation_location:                             
            call_chain_code_down=[call_chain_code_down]
            call_chain_location_down=[call_chain_location_down]
            while True:
                                                                

                             
                one_layer_of_callees = {}
                                        
                for loc, code in zip(call_chain_location_down, call_chain_code_down):
                    if loc not in list(project_func_map.keys()):
                        get_callees(loc, code, resource, cpg_path)
                    if loc not in list(project_func_map.keys()):
                        continue
                    for callee in project_func_map[loc]["callees"]:
                        one_layer_of_callees[callee]=project_func_map[callee]["code_snippet"]
                                    
                        if callee not in list(callers_loc_of_func.keys()):
                            callers_loc_of_func[callee]=[loc]
                        else:
                            callers_loc_of_func[callee].append(loc)
                if one_layer_of_callees=={}:
                    break
                prompt=LLM_PROMPT(one_layer_of_callees,resource,operation_type)
                messages = [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ]
                response=get_answer_from_llm(messages,model_name,resource,operation_location)
                if response==[]:
                                                                          
                    final_result_func_locs+=call_chain_location_down
                    for loc in call_chain_location_down:
                        path=[]
                        get_func_path(callers_loc_of_func, loc, path)
                        if loc in path_of_func.keys():
                            path_of_func[loc]=list(dict.fromkeys(path_of_func[loc]+path))
                        else:
                            path_of_func[loc]=list(dict.fromkeys(path))
                    break
                call_chain_location_down=[]
                call_chain_code_down=[]
                for func in one_layer_of_callees.keys():
                                                                     
                    if func not in response:
                        final_result_func_locs+=callers_loc_of_func[func]
                        path=[]
                        get_func_path(callers_loc_of_func,callers_loc_of_func[func],path)
                        if func in path_of_func.keys():
                            path_of_func[func]=list(dict.fromkeys(path_of_func[func]+path))
                        else:
                            path_of_func[func]=list(dict.fromkeys(path))
                    else:
                        call_chain_location_down.append(func)
                        call_chain_code_down.append(one_layer_of_callees[func])

    return final_result_func_locs,path_of_func


# callers_loc_of_func={
#     "b.java:B":["a.java:A"],
#     "d.java:D":["b.java:B","c.java:C"],
#     "c.java:C":["e.java:E"],
# }
def get_func_path(callers_loc_of_func,func,path):
    while func in list(callers_loc_of_func.keys()):
        path+=callers_loc_of_func[func]
        up_layer=callers_loc_of_func[func]
        for func in up_layer:
            get_func_path(callers_loc_of_func,func,path)


# res=[]
# get_func_path(callers_loc_of_func,"d.java:D",res)
# print(list(dict.fromkeys(res)))












