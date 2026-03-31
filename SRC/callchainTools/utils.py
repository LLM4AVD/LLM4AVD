from functools import lru_cache
import javalang
import json
from javalang.tree import MethodDeclaration
import javalang.tree
from callchainTools.joern_extract_tool import (
    run_joern_analysis,
    run_joern_analysis_up,
    get_func_fullName,
    get_func_signature,
    get_interface_full_name,
    run_joern_analysis_inheritFunc,
    new_run_joern_analysis,
    get_joern_process,
)
import os
import pexpect

@lru_cache(maxsize=None)
def _get_AST_cached(file_path: str, mtime: float) -> javalang.tree.CompilationUnit:
    with open(file_path, 'r', encoding='utf-8') as file:
        java_code = file.read()
    try:
        tree = javalang.parse.parse(java_code)
        return tree
    except Exception as e:
        print(f"构建 AST  解析失败: {file_path} | 错误: {e}")
                                 
        return javalang.parse.parse("class __Empty__ {}")

def get_AST(file_path: str) -> javalang.tree.CompilationUnit:
    try:
        mtime = os.path.getmtime(file_path)
    except FileNotFoundError:
        print(f"文件未找到: {file_path}")
        return javalang.parse.parse("class __Empty__ {}")
    return _get_AST_cached(file_path, mtime)

def max_common_part_length(s1, s2):
    m = len(s1)
    n = len(s2)
    max_len = 0
    dp = [0] * (n + 1)
    for i in range(m):
        current = [0] * (n + 1)
        for j in range(n):
            if s1[i] == s2[j]:
                current[j+1] = dp[j] + 1
                if current[j+1] > max_len:
                    max_len = current[j+1]
            else:
                current[j+1] = 0
        dp = current
    return max_len

# print(max_common_part_length('return toAjax(userService.deleteUserByIds(ids));','code = "this.userService.deleteUserByIds(ids)",'))
# print(len('userService.deleteUserByIds(ids)'))

def find_relative_path(root_dir, target_filename):
    paths=[]
    for dirpath, dirnames, filenames in os.walk(root_dir):
        if target_filename in filenames:
                    
            relative_path = os.path.relpath(os.path.join(dirpath, target_filename), root_dir)
            paths.append(relative_path)
    return paths

                
def get_funcDecl_in_file(file_path):
    func_in_file=[]
    try:
        tree = get_AST(file_path)
                           
        for path, node in tree:
            if isinstance(node, javalang.tree.MethodDeclaration):
                # func_in_file.append((node.name,node))
                func_in_file.append(node.name)
        return func_in_file
    except Exception as e:
        return func_in_file

def get_func_start_line(file_path, function_name):
    try:
        tree = get_AST(file_path)
        
                           
        for path, node in tree:
            if isinstance(node, javalang.tree.MethodDeclaration):
                if node.name == function_name:
                                                  
                    start_line=node.position[0]
                    return start_line
    except Exception as e:
        return -1

@lru_cache(maxsize=None)
def get_code_snippet(file_path, function_name):
    try:
        tree = get_AST(file_path)
        
                           
        for path, node in tree:
            if isinstance(node, javalang.tree.MethodDeclaration):
                if node.name == function_name:
                                                  
                    start_line=node.position[0]
                    left_bracket=0
                    end_line=start_line
                    file1=open(file_path, 'r', encoding='utf-8')
                    lines=file1.readlines()
                    for line_num in range(start_line-1,len(lines)):
                        if '{' in lines[line_num]:
                            left_bracket+=lines[line_num].count('{')
                        if '}' in lines[line_num]:
                            left_bracket-=lines[line_num].count('}')
                            if left_bracket==0:
                                end_line=line_num+1
                                break
                    code_snippet=''
                    for line_num in range(start_line-1,end_line):
                        code_snippet+=lines[line_num]
                    return code_snippet
        return ''

    except FileNotFoundError:
        print(f"文件 {file_path} 未找到。")
        return ''


def get_func_params(file_path, function_name):
    try:
        tree = get_AST(file_path)
        param_list=[]

                           
        for path, node in tree:
            if isinstance(node, javalang.tree.MethodDeclaration):
                if node.name == function_name:
                               
                    method_params = None
                    if hasattr(node, 'parameters'):
                        method_params = node.parameters
                        # print(method_params)
                        params = []
                        for param in method_params:
                            param_ins = param.name
                            param_type = param.type.name
                            params.append((param_type,param_ins))
                        return params

    except FileNotFoundError:
        print(f"文件 {file_path} 未找到。")
        return None
    
# file_path = '/home/fdse/hzc/LLM4VUL/RuoYi/ruoyi-admin/src/main/java/com/ruoyi/web/controller/system/SysRoleController.java'
# function_name = 'authDataScope'
# function_content = get_func_params(file_path, function_name)
def find_resource_related_params(params,resource):
    related_params=[]
    min_length=4                           
    for param in params:
        len1, len2 = len(param), len(resource)
        next_param=False
        if resource.lower() in param.lower():
            related_params.append(param)
            continue
    
                                     
        for i in range(len1 - min_length + 1):
            if next_param:
                break
            for l in range(min_length, len1 - i + 1):
                sub = param[i:i + l]
                if sub.lower() in resource.lower():
                    related_params.append(param)
                    next_param=True
                    break
    return related_params

# print(find_resource_related_params(['currentuser','use','sysuser'],'sysuser'))



def analyze_data_flow(file_path, function_name, resource):
    """
    解析 Java 代码，分析指定函数的参数数据流向。

    :param function_name: 需要分析的 Java 函数名
    :return: 列表，依次表示输入参数如何变化
    """
    tree = get_AST(file_path)
    data_flow = []          
    origin_params=[]                  
                    
    for _, node in tree.filter(javalang.tree.MethodDeclaration):
        if node.name == function_name:          
            if node.body==None:
                return []
            method_params = None
                                     
            if hasattr(node, 'parameters'):
                method_params = node.parameters
                # print(method_params)
                for param in method_params:
                    param_ins = param.name
                    # param_type = param.type.name
                    # params.append((param_type,param_ins))
                    origin_params.append(param_ins)
                                                             
            if origin_params==[]:
                return []
            data_flow.append(origin_params)          
            # for param_name in origin_params:
                          
                                                                       
            variable_map = find_resource_related_params(origin_params,resource)                  
                                                                                                       
            def analyze_one_stmt(one_stmt):
                if isinstance(one_stmt, javalang.tree.LocalVariableDeclaration):        
                    for declarator in one_stmt.declarators:
                        var_name = declarator.name
                                                    
                        """
                        1. 提取方法 / 类构造的参数（如 deptId）；
                        2. 检查参数是否在 variable_map（已确认的资源变量列表）中；
                        3. 若在：将新变量（listener）加入 variable_map，并返回该变量。
                        """
                        if declarator.initializer and (isinstance(declarator.initializer, javalang.tree.MethodInvocation) or isinstance(declarator.initializer,javalang.tree.ClassCreator)):
                                                                                                         
                            arg_names = [a.member if isinstance(a, javalang.tree.MemberReference) else str(a) for a in declarator.initializer.arguments]
                            if arg_names :
                                for arg in arg_names:
                                    if arg in variable_map:                                 
                                        variable_map.append(var_name)
                                        return var_name
                            if arg_names==[]:                                                     
                                if declarator.initializer.qualifier in variable_map:
                                    return var_name
                                                       
                                                                  
                                               
                                                                  
                        elif declarator.initializer in variable_map:                        
                            return var_name
                                                               
                        elif declarator.initializer and isinstance(declarator.initializer,javalang.tree.This):
                            for selector in declarator.initializer.selectors:
                                if isinstance(selector,javalang.tree.MethodInvocation):
                                    arg_names = [a.member if isinstance(a, javalang.tree.MemberReference) else str(a) for a in selector.arguments]
                                    if arg_names :
                                        for arg in arg_names:
                                            if arg in variable_map:                                 
                                                variable_map.append(var_name)
                                                return var_name
                        # elif declarator.initializer and isinstance(declarator.initializer,javalang.tree.ClassCreator):
                                                        
                                                       
                                                         
                                                
                                                                 
                elif isinstance(one_stmt, javalang.tree.ForStatement):               
                                                                             
                    if hasattr(one_stmt,"control") : 
                        if isinstance(one_stmt.control,javalang.tree.EnhancedForControl):
                            if one_stmt.control.iterable.member not in variable_map:
                                return None
                            declarators= one_stmt.control.var.declarators               
                            for declarator in declarators:
                                each_in_for=declarator.name
                                return each_in_for
                return None

            for stmt in node.body:
                if isinstance(stmt,javalang.tree.TryStatement):                            
                    try_body=stmt.block
                    catch_body=stmt.catches
                    finally_body=stmt.finally_block
                    for sub_stmt in try_body:
                        var=analyze_one_stmt(sub_stmt)
                        if var is not None:
                            data_flow.append(var)
                    if catch_body is not None:
                        for sub_stmt in catch_body:
                            var=analyze_one_stmt(sub_stmt)
                            if var is not None:
                                data_flow.append(var)
                    if finally_body is not None:
                        for sub_stmt in finally_body:
                            var=analyze_one_stmt(sub_stmt)
                            if var is not None:
                                data_flow.append(var)
                var=analyze_one_stmt(stmt)
                if var is not None:
                    data_flow.append(var)
                                                                                      
                #     for declarator in stmt.declarators:
                #         var_name = declarator.name
                #         if declarator.initializer and isinstance(declarator.initializer, javalang.tree.MethodInvocation):
                                                                
                #             arg_names = [a.member if isinstance(a, javalang.tree.MemberReference) else str(a) for a in declarator.initializer.arguments]
                                                                                      
                #                 variable_map[var_name] = variable_map[arg_names[0]]
                #                 data_flow.append(var_name)

                                                                                   
                                                                               
                #     if hasattr(stmt,"control") : 
                #         if isinstance(stmt.control,javalang.tree.EnhancedForControl):
                                                                                      
                #             for declarator in declarators:
                #                 each_in_for=declarator.name
                #                 data_flow.append(each_in_for)
            return data_flow          

    return []                 


"""
    在 指定的 function_name 中通过param_names寻找所有调用的函数（Callee），且这些函数的参数中包含 param_names 中的变量，或函数名或函
数所属的类实例化的对象内有资源相关的字符串
    返回两个列表，第一个列表存放直接继承自父类的函数，这类函数没有qualifier，如RuoYi：SysProfileController中的getSysUser，
"""
def find_function_calls_with_param(java_file_path, 
                                   function_name, 
                                   param_names,                     
                                   resource,
                                   func_in_file
                                   ):
                                                                                      
                                                        
    func_res=[[],[]]
    params=[]

    for name in param_names:
        if isinstance(name,list):             
            for n in name:
                params.append(n)
        else:
            params.append(name)           
    
    with open(java_file_path, 'r', encoding='utf-8') as file:
        code = file.read()
    lines = code.split('\n')
    
           
    tree = get_AST(java_file_path)
    
            
    target_method = None
    for path, node in tree.filter(MethodDeclaration):
        if node.name == function_name:
            if node.body==None:
                return func_res
            target_method = node
            break
    if not target_method:
        return func_res
    
                
                                              
    method_calls = []
    for path, node in target_method.filter(javalang.tree.MethodInvocation):
                                                                              
                                                 
        method_calls.append(node)
          
    res_func_log=[]
                    
    for call in method_calls:
                                                
        method_name=call.member if call.member is not None else ''
        method_qualifier=call.qualifier if call.qualifier is not None else ''
        if max_common_part_length(method_name.lower(),resource.lower())>=4 or resource.lower() in method_name.lower() or max_common_part_length(method_qualifier.lower(),resource.lower())>=4:
            if (call.qualifier,call.member) not in res_func_log:
                    if call.qualifier!='':
                        func_res[1].append((call,call.member,lines[call.position[0]-1].strip()))
                        res_func_log.append((call.qualifier,call.member))
                        continue
                    else:                                 
                        func_res[0].append((call,call.member,lines[call.position[0]-1].strip()))
                        res_func_log.append((call.qualifier,call.member))
                        continue
        
        argument_list=call.arguments
        for argument in argument_list:
            if isinstance(argument,javalang.tree.MemberReference):
                if argument.member in params or max_common_part_length(argument.qualifier.lower(),resource.lower())>=4:
                    if (call.qualifier,call.member) not in res_func_log:
                        if call.qualifier!='':
                            func_res[1].append((call,call.member,lines[call.position[0]-1].strip()))
                            res_func_log.append((call.qualifier,call.member))
                            break
                        else:                                 
                            func_res[0].append((call,call.member,lines[call.position[0]-1].strip()))
                            res_func_log.append((call.qualifier,call.member))
                            break
            if isinstance(argument,javalang.tree.MethodInvocation):
                if argument.qualifier in params or max_common_part_length(argument.qualifier.lower(),resource.lower())>=4:
                    if (call.qualifier,call.member) not in res_func_log:
                        if call.qualifier!='':
                            func_res[1].append((call,call.member,lines[call.position[0]-1].strip()))
                            res_func_log.append((call.qualifier,call.member))
                            break
                        else:                                 
                            func_res[0].append((call,call.member,lines[call.position[0]-1].strip()))
                            res_func_log.append((call.qualifier,call.member))
                            break
    return func_res


# find_function_calls_with_param('/home/fdse/hzc/LLM4VUL/RuoYi/ruoyi-system/src/main/java/com/ruoyi/system/service/impl/SysUserServiceImpl.java','importUser',[('List<SysUser>','userList')])

# def find_function_calls_with_param_recursive(java_file_path, 
#                                    function_name, 
                                                                     
#                                    ):
#     func_res=[]
#     params=[]
            
#     # for name in param_names:
#     #     params.append(name[1])

            
#     for name in param_names:
                                                
#             for n in name:
#                 params.append(n)
#         else:
                                            
    
#     with open(java_file_path, 'r', encoding='utf-8') as file:
#         code = file.read()
#     lines = code.split('\n')
    
             
#     tree = javalang.parse.parse(code)
    
              
#     target_method = None
#     for path, node in tree.filter(MethodDeclaration):
#         if node.name == function_name:
#             target_method = node
#             break
#     if not target_method:
#         return {}
    
                  
#     method_calls = []
#     for path, node in target_method.filter(javalang.tree.MethodInvocation):
                                                                                                                                               
#     for call in method_calls:
#         argument_list=call.arguments
#         for argument in argument_list:
#             if isinstance(argument,javalang.tree.MemberReference):
#                 if argument.member in params:
#                     if (call,call.member,lines[call.position[0]-1].strip()) not in func_res:
#                         func_res.append((call,call.member,lines[call.position[0]-1].strip()))
#                         break
#     return func_res
    
                                                                                                                                                                            
# result = find_function_calls_with_param("/home/fdse/hzc/LLM4VUL/RuoYi/ruoyi-admin/src/main/java/com/ruoyi/web/controller/system/SysUserController.java", "remove", "ids")
# print(result)    

                                   
def get_filepath_by_func_name(project_path,project_name,function_name,cpg_path):#function_name:[MethodInvocation,func_name,code]
    func_name=function_name[1]         
    # if func_name!='equals':
    #     return ''
    func_code_line=function_name[2]          
    joern_process = get_joern_process(cpg_path)
    joern_res=run_joern_analysis(project_path,project_name,func_name,joern_process,cpg_path,True)
    func_signature=''
    func_full_name=''
    func_called_col_number=function_name[0].position[1]
    
                                  
    for func_called in joern_res['method_calls']:                
        for line in func_called:
            # if 'code = ' in line:
            #     length=max_common_part_length(line,func_code_line)
            #     if length>len(func_name)+2:
            #         for t_line in func_called:
            #             if 'signature =' in t_line:
            #                 if t_line.endswith(','):
            #                     t_line=t_line[:-1]
            #                 func_signatures.append((t_line,length))
            #             if "methodFullName = " in t_line:
            #                 index1=t_line.find('\"')
            #                 index2=t_line.find('\"',index1+1)
            #                 func_full_names.append((t_line[index1+1:index2],length))
            #         break
            if 'columnNumber =' in line:
                if line=='    columnNumber = None,':
                    continue
                column_num=line[line.find("value = ")+len('value = '):-2]
                column_start=int(column_num)
                if column_start==func_called_col_number:
                    for t_line in func_called:
                        if 'signature =' in t_line:
                            if t_line.endswith(','):
                                t_line=t_line[:-1]
                            func_signature=t_line
                        if "methodFullName = " in t_line:
                            index1=t_line.find('\"')
                            index2=t_line.find('\"',index1+1)
                            func_full_name=t_line[index1+1:index2]
                    break
    
    # if func_signatures==[]:
    #     return ''
    # max_length=-1 
    # func_signature=''
    # for sig in func_signatures:
    #     if sig[1]>max_length:
    #         max_length=sig[1]
    #         func_signature=sig[0]
    # if func_full_names==[]:
    #     return ''
    # max_length=-1 
    # func_full_name=''
    # for i in range(len(func_full_names)):
    #     full_name=func_full_names[i]
    #     sig=func_signatures[i]
    #     if full_name[1]>max_length:
    #         max_length=full_name[1]
    #         func_full_name=full_name[0]
    #         func_signature=sig[0]

                
    called_func_info=''
    signature_legal_funcs=[]          
    target_package_name=''
    for func_def in joern_res['method_defs']:
        sub_file_path=''
        line_start=''
        line_end=''
        column_start=''
        column_end=''
        same_sig=True
        package_name=''
        joern_func_fullname=''
        isExternal=False
        isAbstract=False
        for line in func_def:
            if "code = " in line and (" abstract " in line or "abstract " in line or " abstract" in line):                            
                isAbstract=True
                break
            if "filename = " in line:
                sub_file_path=line[line.find('"')+1:line.find(',')-1]
                package_name=sub_file_path.split('/')[0]
                sub_file_path=project_path+'/'+sub_file_path
            if 'lineNumber =' in line:
                if line=='    lineNumber = None,':
                    continue
                line_num=line[line.find("value = ")+len('value = '):-2]
                line_start=int(line_num)
            if 'lineNumberEnd =' in line:
                if line_start=='':
                    continue
                line_end=int(line[line.find("value = ")+len('value = '):-2])
            if 'columnNumber =' in line:
                if line=='    columnNumber = None,':
                    continue
                column_num=line[line.find("value = ")+len('value = '):-2]
                column_start=int(column_num)
            if 'columnNumberEnd =' in line:
                if column_start=='':
                    continue
                column_end=int(line[line.find("value = ")+len('value = '):-2])
            if 'signature =' in line:
                if line != func_signature:                   
                    same_sig=False
                    break
                                                                                                                                         
            if 'fullName =' in line:
                joern_func_fullname=line[line.find('"')+1:line.find(',')-1]
                if func_full_name in line:                                                                                               
                    target_package_name=package_name
            if 'isExternal =' in line:
                if 'true' in line:
                    isExternal=True
                    break
        if isExternal or isAbstract:
            continue
        if same_sig:
            signature_legal_funcs.append((sub_file_path,line_start,line_end,column_start,column_end,package_name,joern_func_fullname))                                                                    
        
    
    
    if len(signature_legal_funcs)==0:
            return ''
                       
    for func in signature_legal_funcs:
        if func[5]!=target_package_name and target_package_name!='':
            signature_legal_funcs.remove(func)
    if len(signature_legal_funcs)==0:
            return ''
    
                
    for func in signature_legal_funcs:
        if func[6]==func_full_name:
            called_func_info=func
            return called_func_info

                                                           
    func_row_span=[]
    func_col_span=[]
    for func in signature_legal_funcs:
        func_row_span.append(func[2]-func[1])
        func_col_span.append(func[4]-func[3])
    row_max=max(func_row_span)
    if func_row_span.count(row_max)==1:
        index=func_row_span.index(row_max)
        called_func_info=signature_legal_funcs[index]
    else:
        col_max=max(func_col_span)
        index=func_col_span.index(col_max)
        called_func_info=signature_legal_funcs[index]

    return called_func_info                           


def get_annotations(file_path,start_line):
    annotations=[]
    annotation_start=0
    annotation_end=start_line+1
    with open(file_path,'r')as f:
        lines=f.readlines()
        if start_line>len(lines):                                                 
            return []
        start_index=start_line-1
        for i in range(len(lines)-1,-1,-1):
            if i >= start_index:
                continue
            if lines[i].strip().startswith('*/') or lines[i].strip().startswith('/*') or lines[i].strip().startswith('//') or lines[i].strip().startswith('}') or lines[i].strip().startswith('}') or lines[i].strip().endswith(';'):
                annotation_start=i+1
                break
        for i in range(annotation_start,annotation_end):
            if lines[i].strip().startswith('@'):
                if i+1<annotation_end and lines[i+1].strip().startswith('@'):       
                    annotations.append(lines[i].strip())
                if i==annotation_end-1 and lines[i].strip().startswith('@'):
                    annotations.append(lines[i].strip())
                if i+1<annotation_end and not lines[i+1].strip().startswith('@'):      
                    end=i
                    annotation=lines[end].strip()
                    while end+1 < annotation_end and not lines[end+1].strip().startswith('@'):
                        end+=1
                        annotation+=lines[end].strip()
                    annotations.append(annotation)
        return annotations


          
def get_callchain_by_resource_recursive(project_path,
                                        project_name,
                                        file_path,                  
                                        function_name,         
                                        call_chain,
                                        code_snippet_chain,
                                        dst_file):
    call_chain.append(function_name)

                                                                                 
    code_snippet=''
    if isinstance(file_path,list):
        code_snippet=get_code_snippet(file_path[0],function_name)
        file_path=file_path[0]
    else:
        code_snippet=get_code_snippet(file_path,function_name)

    code_snippet_chain.append(code_snippet)

    resource_params=analyze_data_flow(file_path,function_name)
    if resource_params==[]:
        with open(dst_file,'a') as f:
            f.write(json.dumps({"callchain":call_chain,"code_snippet_chain":code_snippet_chain})+'\n')
        return 
    functions=find_function_calls_with_param(file_path,function_name,resource_params)                     
    if len(functions)==0:
        with open(dst_file,'a') as f:
            f.write(json.dumps({"callchain":call_chain,"code_snippet_chain":code_snippet_chain})+'\n')
    for func in functions:
        # if func[1]=='contains':
        #     a=1
        new_file_path=get_filepath_by_func_name(project_path,project_name,func)
        def check_file_paths(file_paths):
            legal_paths=[]
            for path in file_paths:
                if '<empty>' in path or path=='':
                    continue
                else:
                    legal_paths.append(path)
            return legal_paths
        legal_paths=check_file_paths(new_file_path)
        if legal_paths==[]:
            continue
        get_callchain_by_resource_recursive(project_path,project_name,legal_paths,func[1],call_chain,code_snippet_chain,dst_file)
    call_chain.pop()
    code_snippet_chain.pop()


def list_annotation2str(annotation):
    code_annotation=''
    for an in annotation:
        code_annotation+=an+'\n'
    return code_annotation

def get_annotation_by_funcName(file_path,funcname):
    file=open(file_path, 'r', encoding='utf-8')
    java_code = file.read()
    try:
                                          
        tree = javalang.parse.parse(java_code)
    except:
        return []
                       
    for path, node in tree:
        if isinstance(node, javalang.tree.MethodDeclaration):
            if node.name == funcname:
                start_line=node.position[0]
                return get_annotations(file_path,start_line)
    return []


def get_filepath_by_inherit_func_name(project_path,project_name,class_name,caller_name,caller_path,function_name,cpg_path):
    func_name=function_name[1]         
    # if func_name!='equals':
    #     return ''
    func_code_line=function_name[2]          
    joern_process = get_joern_process(cpg_path)
    joern_res=run_joern_analysis_inheritFunc(project_path,project_name,class_name,func_name,joern_process,cpg_path,True)
    abs_filepath=''
    father_calss=joern_res['father_class'].split('.')[-1]
    type_decls=joern_res['map_res']
    for decl in type_decls:
        if decl[1][1:-1]==father_calss:
            abs_filepath=project_path+'/'+decl[2][1:-1]
            break
    if abs_filepath=='':
        called_info=new_get_filepath_by_func_name(project_path,project_name,caller_name,caller_path,function_name,cpg_path)
        if not called_info or isinstance(called_info, str) or len(called_info)==0:
            return abs_filepath
        abs_filepath=called_info[0]
    return abs_filepath

           
def get_callchain_down(project_path,
                              project_name,
                              file_path,                  
                              function_name,              
                              resource,      
                              cpg_path,
                              ):
    '''
    return tuple(list[list[funcA,funcB],list[funcA,funcC]....],list[list[codeA,codeB],list[codeA,codeC]...])
    '''
    func_in_file=get_funcDecl_in_file(file_path)                    
    code_snippet=get_code_snippet(file_path,function_name)
    # params=get_func_params(file_path,function_name)
    resource_params=analyze_data_flow(file_path,function_name,resource)
                                      
    #     return ([function_name],[code_snippet])

    functions=find_function_calls_with_param(file_path,function_name,resource_params,resource,func_in_file)                     
                                                                                

    call_chains=[function_name]
    code_snippets=[code_snippet]
    annotations=[]
    annotations.append(get_annotation_by_funcName(file_path,function_name))
    if resource_params==[] and functions==[[],[]]:                                  
        return (call_chains,code_snippets,annotations)

    code_snippets[0]=list_annotation2str(annotations[0])+code_snippets[0]
    caller_path=file_path[len(project_path)+1:]
    caller_name=function_name
    for func in functions[0]:
                       
        if func[0].qualifier=='' and func[1] in func_in_file:
            code=get_code_snippet(file_path,func[1])
            start_line=get_func_start_line(file_path,func[1])
            annotation=get_annotations(file_path,start_line)
            annotations.append(annotation)
            code_snippets.append(list_annotation2str(annotation)+code)
            call_chains.append(file_path.split('/')[-1]+':'+func[1])
            continue
        class_name=file_path.split('/')[-1].split('.')[0]
        called_func_info=get_filepath_by_inherit_func_name(project_path,project_name,class_name,caller_name,caller_path,func,cpg_path)
        code=get_code_snippet(called_func_info,func[1])
        if code=='':
            continue
        start_line=get_func_start_line(called_func_info,func[1])
        annotation=get_annotations(called_func_info,start_line)
        annotations.append(annotation)

        code_snippets.append(list_annotation2str(annotation)+code)
        call_chains.append(called_func_info.split('/')[-1]+':'+func[1])

                       
    for func in functions[1]:
        # called_func_info=get_filepath_by_func_name(project_path,project_name,func,cpg_path)
        called_func_info=new_get_filepath_by_func_name(project_path,project_name,caller_name,caller_path,func,cpg_path)
        if len(called_func_info)==0:            
            continue
        
        code=get_code_snippet(called_func_info[0],func[1])         
        if code=='':
            continue
        annotation=get_annotations(called_func_info[0],called_func_info[1])         
        annotations.append(annotation)

        code_snippets.append(list_annotation2str(annotation)+code)
        call_chains.append(called_func_info[0].split('/')[-1]+':'+func[1])
    
    
    return (call_chains,code_snippets,annotations)


def get_call_chain_up(project_path,
                        project_name,
                        file_path,                  
                        function_name,               
                        cpg_path
                        ):
    joern_process = get_joern_process(cpg_path)
                            
    up_functions=run_joern_analysis_up(project_path,cpg_path,function_name,joern_process,True)
    if up_functions==[]:
        return ([],[],[])
            
    new_up_functions=[]
    label=[]
    for func in up_functions:
        for line in func:
            if 'methodFullName' in line:
                if line.strip() not in label:
                    new_up_functions.append(func)
                    label.append(line.strip())
                    break
                else:
                    break
    up_functions=new_up_functions

    func_signature=get_func_signature(project_path,project_name,file_path,function_name,joern_process,cpg_path,True)

    if func_signature=='':
        return ([],[],[])

    func_fullName=get_func_fullName(project_path,project_name,file_path,function_name,joern_process,cpg_path,True)
    func_interface_fullName=get_interface_full_name(project_path,project_name,file_path,function_name,func_fullName,joern_process,cpg_path,True)
    func_label=[]
    signature_as_label=False
    if func_fullName==func_interface_fullName:
        signature_as_label=True
        func_label=[func_signature,func_signature]
    else:
        if func_interface_fullName=='':
            func_label=[func_fullName,func_fullName]                
        else:
            func_label=[func_fullName,func_interface_fullName]                      
    up_call_chain=[]
    up_code_snippet=[]
    annotations=[]
    get_up_info=False
    for up_function in up_functions:
        func_name=''                   
        func_file_path=''                        
        method_fullName_th=0
        for var in up_function:
            if "filename = " in var:
                index1=var.find('\"')
                index2=var.find('\"',index1+1)
                func_file_path=var[index1+1:index2]
            if "methodShortName =" in var:
                index1=var.find('\"')
                index2=var.find('\"',index1+1)
                func_name=var[index1+1:index2]
                # func_file_path=get_filepath_by_func_name(project_path,project_name,func_name)
            if func_name!='' and func_file_path!='':
                break
        for line in up_function:
            if 'signature =' in line and signature_as_label :
                if (func_label[0] in line or func_label[1] in line):                  
                    up_call_chain.append(func_file_path.split('/')[-1]+':'+func_name)
                    up_code_snippet.append(get_code_snippet(project_path+'/'+func_file_path,func_name))
                    break
            if 'methodFullName =' in line and not signature_as_label:
                method_fullName_th+=1                                                                                
                if method_fullName_th==2:
                    if (func_label[0] in line or func_label[1] in line):                  
                        up_call_chain.append(func_file_path.split('/')[-1]+':'+func_name)
                        annotation=get_annotation_by_funcName(project_path+'/'+func_file_path,func_name)
                        up_code_snippet.append(list_annotation2str(annotation)+get_code_snippet(project_path+'/'+func_file_path,func_name))
                        annotations.append(annotation)
                        get_up_info=True
                        break
                                                                                                     
    if not get_up_info:
        for up_function in up_functions:
            func_name=''                   
            func_file_path=''                        
            method_fullName_th=0
            for var in up_function:
                if "filename = " in var:
                    index1=var.find('\"')
                    index2=var.find('\"',index1+1)
                    func_file_path=var[index1+1:index2]
                if "methodShortName =" in var:
                    index1=var.find('\"')
                    index2=var.find('\"',index1+1)
                    func_name=var[index1+1:index2]
                    # func_file_path=get_filepath_by_func_name(project_path,project_name,func_name)
                if func_name!='' and func_file_path!='':
                    break
            for line in up_function:
                if 'signature =' in line and signature_as_label :
                    if (func_label[0] in line or func_label[1] in line):                  
                        up_call_chain.append(func_file_path.split('/')[-1]+':'+func_name)
                        up_code_snippet.append(get_code_snippet(project_path+'/'+func_file_path,func_name))
                        break
                if 'methodFullName =' in line and not signature_as_label:
                    method_fullName_th+=1                                                                                
                    if method_fullName_th==2:
                        package_part=line.split(':')[0]
                        signature_part=line.split(':')[1]
                        index1=signature_part.find('>(')
                        index2=signature_part.find(')',index1+1)
                        params_num=signature_part[index1+2:index2]
                        if (func_label[0].split(':')[0] in package_part or func_label[1].split(':')[0] in package_part) and 'unresolvedsignature' in signature_part.lower() and int(params_num)==len(func_signature.split(',')):                  
                            up_call_chain.append(func_file_path.split('/')[-1]+':'+func_name)
                            annotation=get_annotation_by_funcName(project_path+'/'+func_file_path,func_name)
                            up_code_snippet.append(list_annotation2str(annotation)+get_code_snippet(project_path+'/'+func_file_path,func_name))
                            annotations.append(annotation)
                            get_up_info=True
                            break


    return (up_call_chain,up_code_snippet,annotations)



# get_call_chain_up('/home/fdse/hzc/LLM4VUL/RuoYi','RuoYi','/home/fdse/hzc/LLM4VUL/RuoYi/ruoyi-system/src/main/java/com/ruoyi/system/service/impl/SysUserServiceImpl.java','importUser')

    

        
# print(get_callchain_by_resource('/home/fdse/hzc/LLM4VUL/RuoYi','RuoYi','/home/fdse/hzc/LLM4VUL/RuoYi/ruoyi-system/src/main/java/com/ruoyi/system/service/impl/SysUserServiceImpl.java','importUser','user'))  

import re

def parse_string_to_dict(s):
                    
    s_clean = s.strip('{} ')
                            
    pairs = re.split(r',\s*(?=[^:]+:)', s_clean)
    result = {}
    for pair in pairs:
                        
        key_value = pair.split(':', 1)
        if len(key_value) == 2:
            key = key_value[0].strip()
            value = key_value[1].strip()
            result[key] = value
    return result

# import jsonlines
# f=open('/home/fdse/hzc/LLM4VUL/scripts/new_case6.json','a')
# # for item in jsonlines.Reader(f):
# #     for model in item['access control model']:
# #         if model=={}:
# #             continue
# #         print(model['Operator'])
# for item in jsonlines.Reader(open('/home/fdse/hzc/LLM4VUL/scripts/case6.json','r')):
#     new_model=[]
#     for model in item['access control model']:
#         new_model.append(parse_string_to_dict(model))
#     item['access control model']=new_model
#     f.write(json.dumps(item)+'\n')
#     f.flush()
      
# test_str = "{Resource: SysDept, Operator: SysUser, Operation Description: Retrieve department details, Operation Type: read, Permission Requirements: Admin or Dept-specific access}"
# print(parse_string_to_dict(test_str))


def new_get_filepath_by_func_name(project_path,project_name,caller_name,caller_path,function_name,cpg_path):#function_name:[MethodInvocation,func_name,code]
    callee_name=function_name[1]         
    # if func_name!='equals':
    #     return ''
    func_code_line=function_name[2]          
    joern_process = get_joern_process(cpg_path)
    joern_res=new_run_joern_analysis(project_path,project_name,caller_name,callee_name,caller_path,joern_process,cpg_path,True)
    func_signature=''
    func_called_col_number=function_name[0].position[1]
    signature_legal_funcs=[]

                              
    if joern_res is None:
        return ''

    for func_def in joern_res:
        sub_file_path=''
        line_start=''
        line_end=''
        column_start=''
        column_end=''
        same_sig=True
        package_name=''
        joern_func_fullname=''
        isExternal=False
        isAbstract=False
        for line in func_def:
            if "code = " in line and (" abstract " in line or "abstract " in line or " abstract" in line):                            
                isAbstract=True
                break
            if "filename = " in line:
                sub_file_path=line[line.find('"')+1:line.find(',')-1]
                package_name=sub_file_path.split('/')[0]
                sub_file_path=project_path+'/'+sub_file_path
            if 'lineNumber =' in line:
                if line=='    lineNumber = None,':
                    continue
                line_num=line[line.find("value = ")+len('value = '):-2]
                line_start=int(line_num)
            if 'lineNumberEnd =' in line:
                if line_start=='':
                    continue
                line_end=int(line[line.find("value = ")+len('value = '):-2])
            if 'columnNumber =' in line:
                if line=='    columnNumber = None,':
                    continue
                column_num=line[line.find("value = ")+len('value = '):-2]
                column_start=int(column_num)
            if 'columnNumberEnd =' in line:
                if column_start=='':
                    continue
                column_end=int(line[line.find("value = ")+len('value = '):-2])
                                                                                                                                         
            if 'fullName =' in line:
                joern_func_fullname=line[line.find('"')+1:line.find(',')-1]
            if 'isExternal =' in line:
                if 'true' in line:
                    isExternal=True
                    break
        if isExternal or isAbstract:
            continue
        if same_sig:
            signature_legal_funcs.append((sub_file_path,line_start,line_end,column_start,column_end,package_name,joern_func_fullname))                                                                    
        
    
    
    if len(signature_legal_funcs)==0:
            return ''
    
                                                           
    func_row_span=[]
    func_col_span=[]
    for func in signature_legal_funcs:
        func_row_span.append(func[2]-func[1])
        func_col_span.append(func[4]-func[3])
    row_max=max(func_row_span)
    if func_row_span.count(row_max)==1:
        index=func_row_span.index(row_max)
        called_func_info=signature_legal_funcs[index]
    else:
        col_max=max(func_col_span)
        index=func_col_span.index(col_max)
        called_func_info=signature_legal_funcs[index]

    return called_func_info                           
