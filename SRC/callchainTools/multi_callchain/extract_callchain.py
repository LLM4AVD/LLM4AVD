from openai import OpenAI
# from my_callchain import get_call_chain
# from build import get_call_chain,get_resources
import json,jsonlines
import javalang
import os
import re
import pexpect
from utils import get_callchain_down,get_code_snippet,find_relative_path,get_call_chain_up,get_annotations,get_funcDecl_in_file,get_func_start_line
from tqdm import tqdm
from process_data import process_data



def read_json(path):
    with open(path,'r',encoding='utf-8') as f:
        data=json.load(f)
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

ruoyi_case=['SysUserSysUserController.java: editSave','SysUserSysUserServiceImpl.java: importUser','SysDeptSysDeptController.java: editSave'
          ,'SysRoleSysRoleController.java: editSave','SysUserSysUserController.java: remove','SysUserSysUserController.java: authRole']

def get_call_chain(project_path,resources_path,project_name,result_path,sink_path):
    extracted_result=read_json(resources_path)
    resource_cnt=0
    start=False
    sink_location=[]
    project_callchains=[]
    for res in tqdm(extracted_result):
        resource=res['Resource']
        # if resource!='User':
        #     resource_cnt+=1
        #     continue
        # if resource not in ["DefUser","DefArea","DefDict"]:
        #     resource_cnt+=1
        #     continue
        # if resource not in ['SysUser','SysRole','SysDept']:
        #     resource_cnt+=1
        #     continue
        resource_cnt+=1
        # if cnt<48:
        #     continue
        print(f"{resource_cnt}/{len(extracted_result)}")
                          
        sink_points=res['location']
        file_names=[]
        func_names=[]
        for point in sink_points:
            if point.count(':')==0:
                continue
            index=sink_points.index(point)
            point=point.split(':')
            file_name=point[0].strip()        
            func_name=point[1].strip()    
            # if file_name=='SysDeptServiceImpl' and func_name=='checkDeptDataScope' and resource=='SysUser' :
            #     start=True
            # if start==False:
            #     continue
            if file_name=='SysDeptServiceImpl' and func_name=='checkDeptDataScope' and resource=='SysDept' :
                start=True
            if start==False:
                continue
            # if resource == 'User' and file_name!='ApiOrderController':
            #     continue
            if not file_name.endswith('.java'):
                file_name=file_name+'.java'
            if 'test' in file_name.lower():
                continue
            # if not (file_name=='PmsBrandController.java' and func_name=='getBrandPage' and resource=='PmsBrand'):
            #     continue
            # if func_name!='logout':
            #     continue
            # if (resource+file_name+': '+func_name) not in six_case:
            #     continue
            file_names.append(file_name)
            func_names.append(func_name)

            abs_file_path=''
            relative_path=''
            paths=find_relative_path(project_path,file_name)
            if len(paths)==1:
                relative_path=paths[0]
                abs_file_path=project_path+'/'+paths[0]
            else:
                for path in paths:
                    if func_name in get_funcDecl_in_file(project_path+'/'+path):
                        abs_file_path=project_path+'/'+path
                        relative_path=path
                        break
            # print(sink_points)

            if '/test/' in abs_file_path:
                continue
            code_snippet=get_code_snippet(abs_file_path,func_name)
            if code_snippet==None or code_snippet=='':
                # f_err1.write(json.dumps({'resource':resource,'file_name':file_name,'func_name':func_name})+'\n')
                continue
            start_line=get_func_start_line(abs_file_path,func_name)
            
            layer_0={'resource':resource,'file_path':abs_file_path,'func_name':func_name,'code':code_snippet,'annotation':get_annotations(abs_file_path,start_line)}
            
            continue_down=True
            continue_up=True
            danger_func_name=func_name
                
            layer1_down={}
            layer1_up={}
            call_chain_down=get_callchain_down(project_path,project_name,abs_file_path,danger_func_name,resource)
            if call_chain_down==None:         
                continue
            if call_chain_down==([],[],[]):
                continue_down=False
            else:
                layer1_down={danger_func_name:{'call_chain_down':[call_chain_down[0],call_chain_down[1]],'annotation':call_chain_down[-1]}}
            call_chain_up=get_call_chain_up(project_path,project_name,abs_file_path,danger_func_name)
            if call_chain_up==([],[],[]):
                continue_up=False
            else:
                layer1_up={danger_func_name:{'call_chain_up':call_chain_up[:2],'annotation':call_chain_up[-1]}}
                
            layer2_down={}
            if continue_down:
                layer2_down_sink_funcs=layer1_down[danger_func_name]['call_chain_down'][0]
                for func in layer2_down_sink_funcs:
                    file_path=func.split(':')[0]
                    func_name=func.split(':')[1]
                    call_chain_down=get_callchain_down(project_path,project_name,file_path,func_name,resource)
                    if call_chain_down==([],[],[]):
                        continue
                                             
                    layer2_down[func]={'call_chain_down':[call_chain_down[0],call_chain_down[1]],'annotation':call_chain_down[-1]}
            
            layer2_up={}
            if continue_up:
                layer2_up_sink_funcs=layer1_up[danger_func_name]['call_chain_up'][0]
                for func in layer2_up_sink_funcs:
                    file_path=func.split(':')[0]
                    func_name=func.split(':')[1]
                    call_chain_up=get_call_chain_up(project_path,project_name,file_path,func_name)
                    if call_chain_up==([],[],[]):
                        continue
                    layer2_up[func]={'call_chain_up':call_chain_up[:2],'annotation':call_chain_up[-1]}
            
                
            layer3_down={}
            layer3_up={}
            for func_name in layer2_down.keys():
                layer3_down_sink_funcs=layer2_down[func_name]['call_chain_down'][0]
                for func in layer3_down_sink_funcs:
                    file_path=func.split(':')[0]
                    func_name=func.split(':')[1]
                    call_chain_down=get_callchain_down(project_path,project_name,file_path,func_name,resource)
                    if call_chain_down==([],[],[]):
                        continue
                    layer3_down[func]={'call_chain_down':[call_chain_down[0],call_chain_down[1]],'annotation':call_chain_down[-1]}                         
            for func_name in layer2_up.keys():
                layer3_up_sink_funcs=layer2_up[func_name]['call_chain_up'][0]
                for func in layer3_up_sink_funcs:
                    file_path=func.split(':')[0]
                    func_name=func.split(':')[1]
                    call_chain_up=get_call_chain_up(project_path,project_name,file_path,func_name)
                    if call_chain_up==([],[],[]):
                        continue
                    layer3_up[func]={'call_chain_up':call_chain_up[:2],'annotation':call_chain_up[-1]}

                  
            # layer4_down={}
            # layer4_up={}
            # for func_name in layer3_down.keys():
            #     layer4_down_sink_funcs=layer3_down[func_name]['call_chain_down'][1:]
            #     for func in layer4_down_sink_funcs:
            #         file_path=func.split(':')[0]
            #         func_name=func.split(':')[1]
            #         call_chain_down=get_callchain_down(project_path,project_name,file_path,func_name,resource)
                                                                                                                                         
            # for func_name in layer3_up.keys():
            #     layer4_up_sink_funcs=layer3_up[func_name]['call_chain_up'][1:]
            #     for func in layer4_up_sink_funcs:
            #         file_path=func.split(':')[0]
            #         func_name=func.split(':')[1]
            #         call_chain_up=get_call_chain_up(project_path,project_name,file_path,func_name)
            #         layer4_up[func]={'call_chain_up':call_chain_up[:2],'annotation':call_chain_up[-1]}
            # extract_res={'resource':resource,'location':f'{file_name}:{func_name}','call_chain_up':up_call_chain,'call_chain_down':call_chain_info}
            project_callchains.append({'layer0':layer_0,'layer1_down':layer1_down,'layer2_down':layer2_down,'layer3_down':layer3_down,'layer1_up':layer1_up,'layer2_up':layer2_up,'layer3_up':layer3_up})

            with open(result_path,'w',encoding='utf-8') as f:
                json.dump(project_callchains, f, indent=4, ensure_ascii=False)
            print(f"extract callchain of {point}, {index+1}/{len(sink_points)}")
            # print(extract_res)

def main():
    project_name='RuoYi'
    resources_path=f'/home/fdse/hzc/LLM4VUL/scripts/resources/{project_name}_resources.json'
    # project_path='/home/fdse/whl/project/RuoYi_case'
    project_path='/home/fdse/hzc/LLM4VUL/RuoYi'
    res_path=f'/home/fdse/hzc/LLM4VUL/scripts/callchains/{project_name}/multi_up_res_callchains_625.json'
    sink_path=f'/home/fdse/hzc/LLM4VUL/scripts/callchains/{project_name}/{project_name}_sink_locations.json'
    get_call_chain(project_path,resources_path,project_name,res_path,sink_path)

    # up_down_path=f'/home/fdse/hzc/LLM4VUL/scripts/callchains/{project_name}/{project_name}_call_chains_up_down_616.json'
    # sink_locations=[]
    # for item in jsonlines.Reader(open(sink_path, 'r')):
    #     sink_locations=item['paths']
    # process_data(down_path,up_path,up_down_path,sink_locations)



if __name__ == "__main__":
    main()