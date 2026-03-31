import json
import os
import re

from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path
import argparse
import sys
import logging
logging.basicConfig(
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),         
        logging.FileHandler('app.log', encoding='utf-8')                     
    ],
    format='%(asctime)s - %(levelname)s - %(message)s'
)
                                             
for name in list(logging.Logger.manager.loggerDict.keys()):
    logging.getLogger(name).setLevel(logging.WARNING)
                        
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                             
if project_root not in sys.path:
    sys.path.append(project_root)

                 
from resource_.mapper_analyze import analyze_mapper
from resource_.controller_analyze import analyze_controller_callchain_down
from resource_.service_analyze import analyze_service, get_service_interface
          
current_file = Path(__file__).resolve()
env_file = current_file.parent / "../.env"
load_dotenv(env_file.resolve())
                                      
client = {
    "gpt-4o-mini": OpenAI(
        api_key=os.getenv("GPT_4o_mini_KEY"),
        base_url=os.getenv("BASE_URL"),
    )
}
# client = {
#     "gpt-4o-mini": OpenAI(
                                            
#     # base_url='https://api.openai-proxy.org/v1',
#     base_url='https://openkey.cloud/v1',
#     api_key='sk-9wLmg9ZiMNdRQHhd27Ce07200fE74eE4Ae1c813701B49a3f'),
#     "deepseek-reasoner": OpenAI(api_key="sk-8f68830b4fb04ebda6267add4af148f3", base_url="https://api.deepseek.com")
# }

def parse_arguments():
             
    parser = argparse.ArgumentParser(description='设置项目相关路径参数')
    
             
    parser.add_argument('--project-name', 
                       required=True, 
                       help='项目名称，例如 prm-newest')
    
    parser.add_argument('--root-dir', 
                       required=True, 
                       help='项目文件夹路径')
    
    parser.add_argument('--output-dir', 
                       required=True, 
                       help='结果的输出目录')
    
          
    args = parser.parse_args()
    return args

project_name = None
root_dir = None
output_dir = None


def call_Qwen3_32B(prompt):
    try:
        response = client.chat.completions.create(
            model="Qwen3-32B",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error occurred: {e}"

def call_gpt_4o_mini(prompt):
    try:
        response = client["gpt-4o-mini"].chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error occurred: {e}"

              
def extract_resources_from_response(response):
                        
    match = re.search(r'"""(.*?)"""', response, re.DOTALL)
    match_2 = re.search(r'```json(.*?)```', response, re.DOTALL)
    if match or match_2:
        if match_2:
            resources_str = match_2.group(1)
        if match:
                         
            resources_str = match.group(1)

                         
        resource_entries = resources_str.split(';')

                    
        resources = []
        # print(resource_entries)
        for entry in resource_entries:
            # print("entry",entry)
            resource_data = {}
                                           
            pattern = r'"Resource": "(.*?)",\s*"location": "(.*?)"'
            matches = re.search(pattern, entry.strip())
            if matches:
                resource_data["Resource"] = matches.group(1)
                resource_data["location"] = matches.group(2)
                resources.append(resource_data)
        return resources
    else:
        return []


                  
def write_resources_to_json(resources,existing_resources, from_llm: bool = True):

    if from_llm:
                
        for resource_data in resources:
            resource_name = resource_data["Resource"]
            location = resource_data["location"]
            location = re.sub(r'\(.*$', '', location)


                               
            found = False
            for existing_resource in existing_resources:
                if existing_resource["Resource"] == resource_name:
                    found = True
                                         
                    if location not in existing_resource["location"]:
                        existing_resource["location"].append(location)
                    break

                                   
            if not found:
                existing_resources.append({
                    "Resource": resource_name,
                    "location": [location]                 
                })
    else:
        for resource_data in resources:
            resource_name = resource_data["Resource"]
            for location in resource_data["location"]:
                
                                   
                found = False
                for existing_resource in existing_resources:
                    if existing_resource["Resource"] == resource_name:
                        found = True
                                             
                        if location not in existing_resource["location"]:
                            existing_resource["location"].append(location)
                        break

                                       
                if not found:
                    existing_resources.append({
                        "Resource": resource_name,
                        "location": [location]                 
                    })
        
        
    with open(os.path.join(output_dir, 'service_resources.json'), 'w', encoding='utf-8') as json_file:
        json.dump(existing_resources, json_file, ensure_ascii=False, indent=4)
    return existing_resources



            
def get_files_with_keywords(root_dir, keywords):
    matching_files = []
                      
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
                                             
            # print(filename.lower())
            if any(keyword in filename.lower() for keyword in keywords) and 'test' not in filename.lower() and filename.endswith('.java'):
                           
                file_path = os.path.join(dirpath, filename)
                matching_files.append(file_path)
    return matching_files


        
def read_file_content(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return None


def generate_and_send_prompt(code, file):
    max_count = 3         
    
    if code:
        prompt = f'''
Please analyze the following code snippet and identify the resources within it. Resources refer to protected data entities in the system, including but not limited to database tables, variables, etc. These resources are typically accessed through interaction between the frontend and backend. Please note:
1. Variables in the service layer and mapper layer are not considered resources to be identified.
2. The resource names should be in the form of a single, standardized word, such as SysJob, Role.
3. Finally, output the names of the identified resources along with the file and function they are located in. The format should be: {{"Resource": "Resource1 name", "location": "Filename: Function name"}};{{ "Resource": "Resource2 name", "location": "Filename: Function name"}}.
**Important**:Neither the value of key "Resource" nor the value of key "Location" can be empty. That is,it is not allowed to include {{"Resource":""}} or{{"Location":""}} in the output!!!
4. All member functions in the file where the resources appear must be identified, with no omissions.
5. The file name should be in a single word, standardized form, without qualifiers or suffixes. For example, com.xxx.SysJobLogServiceImpl and SysJobLogServiceImpl.java are not valid; it should be SysJobLogServiceImpl.
6. Do not modify any of the extracted resource names in any way. For example, do not remove the suffix "Entity" from GenTemplateGroupEntity.
7. The final output should be enclosed in `"""`, like """output""" .

***Code snippet***:
"""
{code}
"""
'''
        for count in range(max_count):
            result = call_gpt_4o_mini(prompt)
            match = re.search(r'"""(.*?)"""', result, re.DOTALL)
            match_2 = re.search(r'```json(.*?)```', result, re.DOTALL)
            if match or match_2:
                print(f"The {count} Result for file {file}:\n{result}\n")
                return result
            else:
                continue
    else:
        print(f"No Code file {file}")
        return None

def get_resources():
    """
    使用llm从项目目录中提取所有资源
    """
                            
                                                                          
    keywords = ['serviceimpl', 'service']            
    files = get_files_with_keywords(root_dir, keywords)
    existing_resources = []
    error_file = []
    error_file_json = os.path.join(output_dir, 'service_resources_error_file.json')
    read_file_json = os.path.join(output_dir, 'service_resources_read_file.json')
    count_max = 3

    if files:
        print(f"Found {len(files)} matching files.")
        # print(files)
        for file in files:
            # for count in range(count_max):
            code = read_file_content(file)
            if "public interface" in code or "abstract class" in code or "public @interface" in code:
                continue
            result = generate_and_send_prompt(code, file)
            print('file', file)
            if result is None:
                print(f"None file {file}")
                error_file.append(file)
                continue
            resources = extract_resources_from_response(result)
            print('resources', resources)

                                
            if resources:
                write_resources_to_json(resources,existing_resources)
            else:
                print("No resources found in the response.")
            add_resources, funcs = analyze_service(file, root_dir)
            
            for add_resource in add_resources:
                add_resource_data = {"Resource": add_resource, "location": []}
                for func in funcs:
                    add_resource_data["location"].append(f"{file.split('/')[-1].split('.')[0]}: {func}")
                write_resources_to_json([add_resource_data], existing_resources, from_llm=False)
    else:
        print("No matching files found.")

                   

    with open(error_file_json, 'w', encoding='utf-8') as json_file:
        json.dump(error_file, json_file, ensure_ascii=False, indent=4)

    with open(read_file_json, 'w', encoding='utf-8') as json_file:
        json.dump(files, json_file, ensure_ascii=False, indent=4)
        
    return existing_resources


# def mapper2entity():
def get_Serveice2serviceImpl() -> dict:
    """
    从项目目录中提取所有serviceimpl的实现的service接口
    example:
    public class SysOperLogServiceImpl implements ISysOperLogService
    {
        "ISysOperLogService": "SysOperLogServiceImpl",
        "ISysJobLogService": "SysJobLogServiceImpl"
    }
    """
    keywords = ['serviceimpl']            
    files = get_files_with_keywords(root_dir, keywords)
    serviceImpl2Service = {}
    for file in files:
        service_interface = get_service_interface(file)
        if service_interface:
            serviceImpl2Service[file.split('/')[-1].split('.')[0]] = service_interface
            serviceImpl2Service[service_interface] = file.split('/')[-1].split('.')[0]
    return serviceImpl2Service

def get_mappers_entity():
    """
    从项目目录中提取所有mapper的操作实体
    """
    keywords = ['mapper', 'repository', "dao"]            
    mapper_files = get_files_with_keywords(root_dir, keywords)
    mapper_resources = []
    for mapper_file in mapper_files:
        mapper_resources.extend(analyze_mapper(mapper_file))
        
    mapper_resources = list(set(mapper_resources))
    return mapper_resources

def resource_merge(service_resources, mapper_resources):
    """
    合并service和mapper的资源
    规则。
    如果mapper中的资源在service中不存在，标记为漏报
    如果mapper中的资源在service中有常见的别名，比如添加了entity，DTO，VO等后缀名，进行合并
    如果是mapper中不存在的资源，直接舍弃
    """
    service_resources_dict = {}
    for resource in service_resources:
        service_resources_dict[resource['Resource']] = resource['location']
        
    result = []
    for mapper_resource in mapper_resources:
        entity = {"Resource": mapper_resource, "location": []}
        if mapper_resource in service_resources_dict:
            entity["location"].extend(service_resources_dict[mapper_resource])
        if mapper_resource + 'Entity' in service_resources_dict:
            entity["location"].extend(service_resources_dict[mapper_resource + 'Entity'])
        if mapper_resource + 'DTO' in service_resources_dict:   
            entity["location"].extend(service_resources_dict[mapper_resource + 'DTO'])
        if mapper_resource + 'VO' in service_resources_dict:
            entity["location"].extend(service_resources_dict[mapper_resource + 'VO'])
            
        entity["location"] = list(set(entity["location"]))
        result.append(entity)
    return result

def get_controller_resources(merged_resources):
    """
    遍历controller，寻找每个controller可以操作哪些资源
    """
                                                
    location_resource = {}
    for entity in merged_resources:
        for location in entity["location"]:
            location_lower = location.lower()
            if location_lower not in location_resource:
                location_resource[location_lower] = []
                                            
            if isinstance(entity["Resource"], list):
                location_resource[location_lower].extend(entity["Resource"])
            else:
                               
                location_resource[location_lower].append(entity["Resource"])
                
                               
    Serveice2serviceImpl = get_Serveice2serviceImpl()
    controller_resources = {}
    keywords = ['controller']            
    controller_files = get_files_with_keywords(root_dir, keywords)
    for controller_file in controller_files:
        func_in_file = analyze_controller_callchain_down(controller_file)
        for fun in func_in_file:
            controller_fun = fun['method_name']
            controller_name = controller_file.split('/')[-1].split('.')[0]
            for ctrl_inner_func in fun['method_calls']:
                call_name = ctrl_inner_func['call_name']
                call_type = ctrl_inner_func['call_type']
                location = f"{call_type}: {call_name}".lower()
                resources = location_resource.get(location, [])
                                          
                for resource in resources:
                    if resource not in controller_resources:
                        controller_resources[resource] = []
                    controller_resources[resource].append(f"{controller_name}: {controller_fun}")
                location = f"{call_type}Impl: {call_name}".lower()
                resources = location_resource.get(location, [])
                                          
                for resource in resources:
                    if resource not in controller_resources:
                        controller_resources[resource] = []
                    controller_resources[resource].append(f"{controller_name}: {controller_fun}")
                         
                location = f"{Serveice2serviceImpl.get(call_type, call_type)}: {call_name}".lower()
                resources = location_resource.get(location, [])
                                          
                for resource in resources:
                    if resource not in controller_resources:
                        controller_resources[resource] = []
                    controller_resources[resource].append(f"{controller_name}: {controller_fun}")
              
    final_controller_resources = []
    for resource, locations in controller_resources.items():
            
        locations_ = list(set(locations))
        entity = {"Resource": resource, "location": locations_}
        final_controller_resources.append(entity)
    return final_controller_resources

def main():
    global project_name, root_dir, output_dir
    args = parse_arguments()
    project_name = args.project_name
    root_dir = args.root_dir
    output_dir = args.output_dir
                  
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    service_resources_file = os.path.join(output_dir, "service_resources.json")
                      
    if os.path.exists(f"{service_resources_file}"):
        with open(f"{service_resources_file}", 'r', encoding='utf-8') as f:
            service_resources = json.load(f)
    else:
        service_resources = get_resources()
        with open(f"{service_resources_file}", 'w', encoding='utf-8') as f:
            json.dump(service_resources, f, ensure_ascii=False, indent=2)
        print(f"Resources have been written to {service_resources_file}")
    
                     
    mapper_resources_file = os.path.join(output_dir, "mapper_resources.json")
    mapper_resources = get_mappers_entity()
    with open(f"{mapper_resources_file}", 'w', encoding='utf-8') as f:
        json.dump(mapper_resources, f, ensure_ascii=False, indent=2)
    print(f"Mapper resources have been written to {mapper_resources_file}")
    
                              
    merged_resources = resource_merge(service_resources, mapper_resources)
    merged_resources_file = os.path.join(output_dir, "merged_resources.json")
    with open(f"{merged_resources_file}", 'w', encoding='utf-8') as f:
        json.dump(merged_resources, f, ensure_ascii=False, indent=2)
    print(f"Merged resources have been written to {merged_resources_file}")
    
                                         
    final_resources = get_controller_resources(merged_resources)
    final_resources_file = os.path.join(output_dir, "final_resources.json")
    with open(f"{final_resources_file}", 'w', encoding='utf-8') as f:
        json.dump(final_resources, f, ensure_ascii=False, indent=2)
    print(f"Final resources have been written to {final_resources_file}")
    

if __name__ == "__main__":
    main()
