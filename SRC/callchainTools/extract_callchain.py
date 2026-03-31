from openai import OpenAI
# from my_callchain import get_call_chain
# from build import get_call_chain,get_resources
import json, jsonlines
import javalang
import os
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
accesscontrol_dir = os.path.abspath(os.path.join(current_dir, ".."))                       

                             
if accesscontrol_dir not in sys.path:
    sys.path.insert(0, accesscontrol_dir)

                                         
from callchainTools.utils import get_callchain_down, get_code_snippet, find_relative_path, get_call_chain_up,\
    get_annotations, get_funcDecl_in_file
from callchainTools.utils import get_callchain_down, get_code_snippet, find_relative_path, get_call_chain_up,\
    get_annotations, get_funcDecl_in_file
from tqdm import tqdm
from process_data import process_data
from joern_extract_tool import close_joern_process
import argparse
from utils.path_util import PathUtil
from utils.data_utils import DataUtils


def read_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        return data


# read_json('/home/fdse/hzc/LLM4VUL/scripts/resources/mall_resources.json')

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

# youlaicase
# resorce: SysUser
# location:SysUserController: deleteUsers

ruoyi_case = ['SysUserSysUserController.java: editSave', 'SysUserSysUserServiceImpl.java: importUser',
              'SysDeptSysDeptController.java: editSave'
    , 'SysRoleSysRoleController.java: editSave', 'SysUserSysUserController.java: remove',
              'SysUserSysUserController.java: authRole']


def parse_arguments():
             
    parser = argparse.ArgumentParser(description='设置项目相关路径参数')

             
    parser.add_argument('--project-name',
                        required=True,
                        help='项目名称，例如 prm-newest')

    parser.add_argument('--resources-path',
                        required=True,
                        help='资源文件路')

    parser.add_argument('--project-path',
                        required=True,
                        help='项目根目录路径')

    parser.add_argument('--cpg-path',
                        required=True,
                        help='cpg文件路径')

    parser.add_argument('--out-dir',
                        required=True,
                        help='输出目录路径')
    parser.add_argument('--resource_list', nargs='+', required=False,
                        help='资源列表；若不提供，则默认使用资源文件中全部 Resource')

          
    args = parser.parse_args()
    return args


def get_call_chain(project_path, resources_path, project_name, down_path, up_path, sink_location_path, resource_list,
                   cpg_path, project_func_map_path):
    down_res = open(down_path, 'a')
    up_res = open(up_path, 'a')
    extracted_result = read_json(resources_path)
    if os.path.exists(project_func_map_path):
        project_func_map = DataUtils.load_json(project_func_map_path)
    else:
        project_func_map = {}
    resource_cnt = 0
    start = False
    sink_location = []
    fail_loc = []
    for res in tqdm(extracted_result):
        resource = res['Resource']
        # if resource!='User':
        #     resource_cnt+=1
        #     continue
        if resource not in resource_list:
            resource_cnt += 1
            continue

        resource_cnt += 1
        # if cnt<48:
        #     continue
        print(f"{resource_cnt}/{len(extracted_result)}")
                           
        # example: SysMessageController: queryPageList
        sink_points = res['location']
        file_names = []
        func_names = []
        for point in sink_points:
            if point.count(',') > 0 or point.count(':') == 0:
                continue
            index = sink_points.index(point)
            print(f"\n start extract {point}")
            point = point.split(':')
            file_name = point[0].strip()          
            func_name = point[1].strip()

            if file_name == '' or func_name == '':
                continue

            if not file_name.endswith('.java'):
                file_name = file_name + '.java'
            if 'test' in file_name.lower() or 'mapper' in file_name.lower():
                continue
            #if not (file_name=='HouseMagService.java' and func_name=='isHouseEditable'):
            #     continue
            file_names.append(file_name)
            func_names.append(func_name)

            abs_file_path = ''
            relative_path = ''
            paths = find_relative_path(project_path, file_name)                   
            if len(paths) == 1:
                relative_path = paths[0]
                abs_file_path = project_path + '/' + paths[0]
            else:
                for path in paths:
                    if func_name in get_funcDecl_in_file(project_path + '/' + path):
                        abs_file_path = project_path + '/' + path
                        relative_path = path
                        break
            print(paths)
                    
            if '/test/' in abs_file_path:
                continue

            code_snippet = get_code_snippet(abs_file_path, func_name)
            if code_snippet == None or code_snippet == '':
                # f_err1.write(json.dumps({'resource':resource,'file_name':file_name,'func_name':func_name})+'\n')
                continue

            call_chain_down = get_callchain_down(project_path, project_name, abs_file_path, func_name, resource,
                                                 cpg_path)
            call_chain_up = get_call_chain_up(project_path, project_name, abs_file_path, func_name, cpg_path)
            #print(call_chain_up)
            #if call_chain_down==None or call_chain_up==None:
            #    fail_loc.append({"location":f'{resource}:{file_name}:{func_name}'})
            #    with open(fail_path,'w') as f:
            #        f.write(json.dumps(fail_loc,ensure_ascii=False)+'\n')
            #    continue

            if call_chain_down == None and call_chain_up == None:
                continue

                             
            location = file_name + ':' + func_name
            if location in list(project_func_map.keys()):
                func_callees = project_func_map[location]["callees"] if project_func_map[location][
                                                                            "callees"] is not None else []
                func_callers = project_func_map[location]["callers"] if project_func_map[location][
                                                                            "callers"] is not None else []
                func_code_snippet = project_func_map[location]["code_snippet"]
                if func_code_snippet == None or func_code_snippet == '':
                    project_func_map[location]["code_snippet"] = code_snippet
                if project_func_map[location]["annotations"] == None or project_func_map[location]["annotations"] == []:
                    project_func_map[location]["annotations"] = call_chain_down[-1][
                        0] if call_chain_down != None and call_chain_down != ([], [], []) else [[""]]
                for callee_loc in (
                        call_chain_down[0][1:] if call_chain_down != ([], [], []) and call_chain_down != None else []):
                    if callee_loc not in func_callees:
                        project_func_map[location]["callees"].append(callee_loc)
                for caller_loc in (call_chain_up[0] if call_chain_up != ([], [], []) and call_chain_up != None else []):
                    if caller_loc not in func_callers:
                        project_func_map[location]["callers"].append(caller_loc)
            else:
                project_func_map[location] = {"callees": call_chain_down[0][1:] if call_chain_down != None and len(call_chain_down[0])>1 else [], "callers": call_chain_up[0] if call_chain_up != (
                    [], [], []) and call_chain_up != None else [], "code_snippet": code_snippet,
                                              "annotations": call_chain_down[-1][0] if call_chain_down != None and len(call_chain_down[0])>1 else []}

                                                                                          
            if call_chain_down != ([], [], []) and call_chain_down != None and len(call_chain_down[0])>1:
                for loc, code, annotation in zip(call_chain_down[0][1:], call_chain_down[1][1:],
                                                 call_chain_down[2][1:]):
                    if loc not in project_func_map.keys():
                        project_func_map[loc] = {"callers": [location], "callees": [], "code_snippet": code,
                                                 "annotations": annotation}
                    else:
                        if location not in (
                                project_func_map[loc]["callers"] if project_func_map[loc]["callers"] != None else []):
                            project_func_map[loc]["callers"].append(location)
                        if project_func_map[loc]["code_snippet"] != code:
                            project_func_map[loc]["code_snippet"] = code
                        if project_func_map[loc]["annotations"] != annotation:
                            project_func_map[loc]["annotations"] = annotation

                                                      
            if call_chain_up != ([], [], []) and call_chain_up != None:
                for loc, code, annotation in zip(call_chain_up[0], call_chain_up[1], call_chain_up[2]):
                    if loc not in project_func_map.keys():
                        project_func_map[loc] = {"callers": [], "callees": [location], "code_snippet": code,
                                                 "annotations": annotation}
                    else:
                        if location not in project_func_map[loc]["callees"]:
                            project_func_map[loc]["callees"].append(location)
                        if project_func_map[loc]["code_snippet"] != code:
                            project_func_map[loc]["code_snippet"] = code
                        if project_func_map[loc]["annotations"] != annotation:
                            project_func_map[loc]["annotations"] = annotation
            DataUtils.save_json(project_func_map_path, project_func_map)

            extract_down_res = {'resource': resource, 'location': f'{file_name}:{func_name}',
                                'call_chain_down': call_chain_down[:2] if call_chain_down != None and call_chain_down[
                                    0] != [] else [[""], [""]],
                                'annotation': call_chain_down[-1] if call_chain_down != None and call_chain_down[
                                    0] != [] else [[""]]}
            extract_up_res = {'resource': resource, 'location': f'{file_name}:{func_name}',
                              'call_chain_up': call_chain_up[:2] if call_chain_up != None and call_chain_up[
                                  0] != [] else [[""], [""]],
                              'annotation': call_chain_up[-1] if call_chain_up != None and call_chain_up[0] != [] else [
                                  [""]]}
            # extract_res={'resource':resource,'location':f'{file_name}:{func_name}','call_chain_up':up_call_chain,'call_chain_down':call_chain_info}
            down_res.write(json.dumps(extract_down_res, ensure_ascii=False) + '\n')
            down_res.flush()
            up_res.write(json.dumps(extract_up_res, ensure_ascii=False) + '\n')
            up_res.flush()

            sink_location.append(project_path.split('/')[-1] + '/' + relative_path)
            print(f"extract callchain of {point}, {index + 1}/{len(sink_points)}")
    with open(sink_location_path, 'w') as f:
        json.dump({"paths": sink_location}, f, indent=4, ensure_ascii=False)
    return sink_location


def main():
    args = parse_arguments()
    project_name = args.project_name
    resources_path = args.resources_path
    project_path = args.project_path
    resource_list = args.resource_list
    cpg_path = args.cpg_path

    out_dir = args.out_dir

    if not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)                

    down_path = f"{out_dir}/{project_name}_call_chains_down.json"
    up_path = f"{out_dir}/{project_name}_call_chains_up.json"
    sink_location_path = f"{out_dir}/{project_name}_sink.json"
    up_down_path = f"{out_dir}/{project_name}_call_chains_up_down.json"
    project_func_map_path = PathUtil.call_chain_data(f"{project_name}_func_map", "json")

    if os.path.exists(down_path):
        os.remove(down_path)
    if os.path.exists(up_path):
        os.remove(up_path)
    if os.path.exists(sink_location_path):
        os.remove(sink_location_path)
                                                   
    if resource_list is None:
        try:
            data = read_json(resources_path)
            resource_list = [str(item.get('Resource', '')).strip() for item in data if item.get('Resource')]
        except Exception as e:
            print(f"读取资源列表失败: {e}")
            resource_list = []

    sink_locations = get_call_chain(
        project_path,
        resources_path,
        project_name,
        down_path,
        up_path,
        sink_location_path,
        resource_list,
        cpg_path,
        project_func_map_path
    )

    process_data(down_path, up_path, up_down_path, sink_locations)
                   
    try:
        close_joern_process()
    except Exception:
        pass
    #process_data(down_path,up_path,up_down_path,sink_location_path)


if __name__ == "__main__":
    main()
