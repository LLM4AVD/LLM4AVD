import pexpect

import re
import os

# os.system("javasrc2cpg -J-Xmx10240m "+ "/home/fdse/hzc/LLM4VUL/RuoYi" + " --output cpg.bin")
# /home/fdse/bin/joern/joern-cli/javasrc2cpg -J-Xmx30208m /home/fdse/hzc/LLM4VUL/SpringBlade-master --output /home/fdse/workspace/SpringBlade/cpg.bin.zip
# javasrc2cpg -J-Xmx10240m /home/fdse/hzc/LLM4VUL/youlai-mall-master-buggy --output cpg.bin
# javasrc2cpg -J-Xmx10240m /home/fdse/hzc/LLM4VUL/mall-master-buggy --output cpg.bin
# javasrc2cpg -J-Xmx10240m /home/fdse/hzc/LLM4VUL/SpringBlade-master --output cpg.bin
# javasrc2cpg -J-Xmx10240m /home/fdse/hzc/LLM4VUL/my-shop-master --output cpg.bin
# pkill -f joern
# cpg.method.name("saveRole").caller.l  cpg.method.name("saveRole").filename.l



def remove_colors(input_list):
                                  
    color_code_pattern = re.compile(r'\x1b\[[0-9;]*m')
    
                
    cleaned_list = [color_code_pattern.sub('', item) for item in input_list]
    
    return cleaned_list

def split_cpg_call(calls_output):
    split_pos=[]
    for i in range(len(calls_output)):
        item=calls_output[i]
        if item.strip()=='Call(' :
            split_pos.append(i)
        if item==')':
            split_pos.append(i)
            break
    func_res=[]
    for i in range(1,len(split_pos)):
        func_res.append(calls_output[split_pos[i-1]:split_pos[i]])
    return func_res

def split_method_call(methods_output):
    split_pos=[]
    for i in range(len(methods_output)):
        item=methods_output[i]
        if item.strip()=='Method(' :
            split_pos.append(i)
        if item==')':
            split_pos.append(i)
            break
    func_res=[]
    for i in range(1,len(split_pos)):
        func_res.append(methods_output[split_pos[i-1]:split_pos[i]])
    return func_res

def split_location_call(locations_output):
    split_pos=[]
    for i in range(len(locations_output)):
        item=locations_output[i]
        if item.strip()=='NewLocation(' :
            split_pos.append(i)
        if '  )' == item :
            split_pos.append(i)
    func_res=[]
    for i in range(1,len(split_pos)):
        func_res.append(locations_output[split_pos[i-1]:split_pos[i]])
    return func_res



def run_joern_analysis(project_path,project_name,method_name,joern_process,cpg_input=False):
    try:
                     
        # if joern_process==None:
        #     joern_process = pexpect.spawn('joern')
        #     joern_process.expect('joern>', timeout=60)
        # os.system("javasrc2cpg -J-Xmx10240m "+ project_path + " --output cpg.bin")
        if not cpg_input:
                   
            import_cmd = f'importCpg("/home/fdse/hzc/LLM4VUL/scripts/{project_name}_cpg.bin")'
            joern_process.sendline(import_cmd)
            joern_process.expect('joern>', timeout=60)
        
                             
        joern_process.sendline(f'cpg.call("{method_name}").l')
        joern_process.expect('joern>', timeout=60)
        calls_output = joern_process.before.decode().splitlines()
        calls_output=remove_colors(calls_output)
        call_res=split_cpg_call(calls_output)
        
                                    
        joern_process.sendline(f'cpg.method.name("{method_name}").l')
        joern_process.expect('joern>', timeout=60)
        methods_output = joern_process.before.decode().splitlines()
        methods_output=remove_colors(methods_output)
        method_res=split_method_call(methods_output)
        
                  
        # joern_process.sendline('exit')
        # joern_process.close()
        
        return {
            'method_calls': call_res,
            'method_defs': method_res
        }
    except pexpect.exceptions.ExceptionPexpect as e:
        print(f"Error: {e}")
        return None

def new_run_joern_analysis(project_path,project_name,caller_name,callee_name,caller_path,joern_process,cpg_input=False):
    try:
                     
        # if joern_process==None:
        #     joern_process = pexpect.spawn('joern')
        #     joern_process.expect('joern>', timeout=60)
        # os.system("javasrc2cpg -J-Xmx10240m "+ project_path + " --output cpg.bin")
        if not cpg_input:
                   
            import_cmd = f'importCpg("/home/fdse/hzc/LLM4VUL/scripts/{project_name}_cpg.bin")'
            joern_process.sendline(import_cmd)
            joern_process.expect('joern>', timeout=60)
        
                             
        joern_process.sendline(f'cpg.method.name("{caller_name}").where(_.file.name("{caller_path}")).call.name("{callee_name}").callee.l')
        joern_process.expect('joern>', timeout=60)
        calls_output = joern_process.before.decode().splitlines()
        calls_output=remove_colors(calls_output)
        call_res=split_method_call(calls_output)

        return call_res

    except pexpect.exceptions.ExceptionPexpect as e:
        print(f"Error: {e}")
        return None

# if __name__ == "__main__":
#     project_path = "/home/fdse/hzc/LLM4VUL/RuoYi"  
#     project_name="RuoYi"
#     method_name="deleteUserByIds"
#     results = run_joern_analysis(project_path,project_name,method_name)
#     if results:
#         print("CPG Calls:", results['calls'])
#         print("Method Names:", results['method_names'])
def split_map(map_output):
    start_connect=False
    map_str=''
    for s in map_output:
        if ')' == s.strip():
            start_connect=False
        if start_connect:
            map_str+=s.strip()
        if 'List(' in s:
            start_connect=True
    map_str=map_str.split('),')
    for i,str in enumerate(map_str):
        map_str[i]=str[1:].split(',')
    return map_str

    



def run_joern_analysis_inheritFunc(project_path,project_name,class_name,method_name,joern_process,cpg_input=False):
    try:
                     
        # if joern_process==None:
        #     joern_process = pexpect.spawn('joern')
        #     joern_process.expect('joern>', timeout=60)
        # os.system("javasrc2cpg -J-Xmx10240m "+ project_path + " --output cpg.bin")
        if not cpg_input:
                   
            import_cmd = f'importCpg("/home/fdse/hzc/LLM4VUL/scripts/{project_name}_cpg.bin")'
            joern_process.sendline(import_cmd)
            joern_process.expect('joern>', timeout=60)
        
                  
        joern_process.sendline(f'cpg.typeDecl.name("{class_name}").inheritsFromTypeFullName.l')
        joern_process.expect('joern>', timeout=60)
        cpg_output = joern_process.before.decode().splitlines()
        cpg_output=remove_colors(cpg_output)
        father_class=''
        for line in cpg_output:
            if '= List(' in line and (not line.strip().endswith('= List(')):
                index1=line.find('"')+1
                index2=line.find('"',index1+1)
                father_class=line[index1:index2]
                break
        # call_res=split_cpg_call(calls_output)
        
                                    
        joern_process.sendline(f'cpg.method.name("{method_name}").map(m => (m.fullName, m.typeDecl.name.toList.mkString(", "), m.file.name.toList.mkString(", "))).l')
        joern_process.expect('joern>', timeout=60)
        map_output = joern_process.before.decode().splitlines()
        map_output=remove_colors(map_output)
        map_res=split_map(map_output)
        
                  
        # joern_process.sendline('exit')
        # joern_process.close()
        
        return {
            'father_class': father_class,
            'map_res': map_res
        }
    except pexpect.exceptions.ExceptionPexpect as e:
        print(f"Error: {e}")
        return None
    


# joern_process=None
                        
def run_joern_analysis_up(project_path,project_name,method_name,joern_process,cpg_input=False):
    try:
                     
        # if joern_process==None:
        #     joern_process = pexpect.spawn('joern')
        #     joern_process.expect('joern>', timeout=60)
        # os.system("javasrc2cpg -J-Xmx10240m "+ project_path + " --output cpg.bin")
               
        if not cpg_input:
            import_cmd = f'importCpg("/home/fdse/hzc/LLM4VUL/scripts/{project_name}_cpg.bin")'
            joern_process.sendline(import_cmd)
            joern_process.expect('joern>', timeout=60)
        
                             
        joern_process.sendline(f'cpg.call.name("{method_name}").location.toList')
        joern_process.expect('joern>', timeout=60)
        calls_output = joern_process.before.decode().splitlines()
        calls_output=remove_colors(calls_output)
        called_res=split_location_call(calls_output)

                  
        # joern_process.sendline('exit')
        # joern_process.close()
        
        return called_res
    except pexpect.exceptions.ExceptionPexpect as e:
        print(f"Error: {e}")
        return None

# run_joern_analysis_up("/home/fdse/hzc/LLM4VUL/RuoYi","RuoYi","importUser")

def get_func_fullName(project_path,
                      project_name,
                      file_path,            
                      function_name,
                      joern_process,
                      cpg_input=False):
    try:
                     
        # if joern_process==None:
        #     joern_process = pexpect.spawn('joern')
        #     joern_process.expect('joern>', timeout=60)
        # os.system("javasrc2cpg -J-Xmx10240m "+ project_path + " --output cpg.bin")
        if not cpg_input:
                   
            import_cmd = f'importCpg("/home/fdse/hzc/LLM4VUL/scripts/{project_name}_cpg.bin")'
            joern_process.sendline(import_cmd)
            joern_process.expect('joern>', timeout=60)
        
                                    
        joern_process.sendline(f'cpg.method.name("{function_name}").l')
        joern_process.expect('joern>', timeout=60)
        methods_output = joern_process.before.decode().splitlines()
        methods_output=remove_colors(methods_output)
        method_res=split_method_call(methods_output)
        # print(method_res)
        
                  
        # joern_process.sendline('exit')
        # joern_process.close()

        target_method=[]
        for method in method_res:
            for line in method:
                if "filename =" in line:
                    index1=line.find('\"')
                    index2=line.find('\"',index1+1)
                    extracted_file_path=line[index1+1:index2]
                    if extracted_file_path in file_path:
                        target_method=method
                        for each_line in target_method:
                            if "fullName = " in each_line:
                                index1=each_line.find('\"')
                                index2=each_line.find('\"',index1+1)
                                return each_line[index1+1:index2]
        return ''
                        
        
    except pexpect.exceptions.ExceptionPexpect as e:
        print(f"Error: {e}")
        return ''
    

# get_func_fullName('/home/fdse/hzc/LLM4VUL/RuoYi','RuoYi','a','importUser')



def get_func_signature(project_path,
                      project_name,
                      file_path,            
                      function_name,
                      joern_process,
                      cpg_input=False):
    try:
                     
        # if joern_process==None:
        #     joern_process = pexpect.spawn('joern')
        #     joern_process.expect('joern>', timeout=60)
        # os.system("javasrc2cpg -J-Xmx10240m "+ project_path + " --output cpg.bin")
               
        if not cpg_input:
            import_cmd = f'importCpg("/home/fdse/hzc/LLM4VUL/scripts/{project_name}_cpg.bin")'
            joern_process.sendline(import_cmd)
            joern_process.expect('joern>', timeout=60)
        
                                    
        joern_process.sendline(f'cpg.method.name("{function_name}").l')
        joern_process.expect('joern>', timeout=60)
        methods_output = joern_process.before.decode().splitlines()
        methods_output=remove_colors(methods_output)
        method_res=split_method_call(methods_output)
        # print(method_res)
        
                  
        # joern_process.sendline('exit')
        # joern_process.close()

        target_method=[]
        for method in method_res:
            for line in method:
                if "filename =" in line:
                    index1=line.find('\"')
                    index2=line.find('\"',index1+1)
                    extracted_file_path=line[index1+1:index2]
                    if extracted_file_path in file_path:
                        target_method=method
                        for each_line in target_method:
                            if "signature = " in each_line:
                                index1=each_line.find('\"')
                                index2=each_line.find('\"',index1+1)
                                return each_line[index1+1:index2]
        return ''
                        
        
    except pexpect.exceptions.ExceptionPexpect as e:
        print(f"Error: {e}")
        return ''
    

import json


# val res2: List[String] = List(
#   "com.baomidou.mybatisplus.extension.service.impl.ServiceImpl",
#   "com.youlai.system.service.SysUserService"
# )

# val res1: List[String] = List("java.lang.Object", "com.fengdu.service.SysRoleService")

def get_interface_name(method_output):
    for i in range(len(method_output)):
        item=method_output[i].strip()
        if 'List[String] = List(' in item:
            if item.endswith('= List('):
                interface_item=method_output[i+2]
                index1=interface_item.find('"')
                index2=interface_item.find('"',index1+1)
                return interface_item[index1+1:index2]
            else:
                index1=item.find(', "')+3
                index2=item.find('"',index1+1)
                return item[index1:index2]
            # index1=item.find('List(')+4
            # index2=item.find('\")',index1+1)
            # if index2==-1:
            #     return ''
            # item='['+item[index1+1:index2+1]+']'
            # item=json.loads(item)
            # return item[-1]
    return ''


def get_decl_fullName(method_output):
    for i in range(len(method_output)):
        item=method_output[i]
        if 'fullName =' in item:
            index1=item.find('\"')
            index2=item.find('\"',index1+1)
            return item[index1+1:index2]
    return ''

def get_interface_full_name(project_path,project_name,implement_file_path,implement_func_name,func_full_name,joern_process,cpg_input=False):
    try:
        class_name=func_full_name.split(':')[0].split('.')[-2]        

                     
        # if joern_process==None:
        #     joern_process = pexpect.spawn('joern')
        #     joern_process.expect('joern>', timeout=60)
        # os.system("javasrc2cpg -J-Xmx10240m "+ project_path + " --output cpg.bin")
        if not cpg_input:
                   
            import_cmd = f'importCpg("/home/fdse/hzc/LLM4VUL/scripts/{project_name}_cpg.bin")'
            joern_process.sendline(import_cmd)
            joern_process.expect('joern>', timeout=60)
        
                                    
        joern_process.sendline(f'cpg.typeDecl("{class_name}").inheritsFromTypeFullName.l')
        joern_process.expect('joern>', timeout=60)
        methods_output = joern_process.before.decode().splitlines()
        methods_output=remove_colors(methods_output)
        interface_name=get_interface_name(methods_output)
        if interface_name=='':
            return ''

        joern_process.sendline(f'cpg.typeDecl.fullNameExact("{interface_name}").method.name("{implement_func_name}").location.l')
        joern_process.expect('joern>', timeout=60)
        methods_output = joern_process.before.decode().splitlines()
        methods_output=remove_colors(methods_output)
        decl_full_name=get_decl_fullName(methods_output)

                  
        # joern_process.sendline('exit')
        # joern_process.close()

        return decl_full_name


    except pexpect.exceptions.ExceptionPexpect as e:
        print(f"Error: {e}")
        return ''
 

# get_interface_full_name("/home/fdse/hzc/LLM4VUL/RuoYi","RuoYi",'/home/fdse/hzc/LLM4VUL/RuoYi/ruoyi-system/src/main/java/com/ruoyi/system/service/impl/SysDeptServiceImpl.java','selectDeptList')
    
