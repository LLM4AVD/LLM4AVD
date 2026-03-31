import javalang
from typing import List, Dict, Any

def get_class_field(ast: javalang.tree.CompilationUnit) -> Dict[str, str]:
    """
    private final GenFieldTypeMapper fieldTypeMapper;
    resturn: {"fieldTypeMapper": "GenFieldTypeMapper"}
    """
    res = {}
    try:
        for path, node in ast:
            if isinstance(node, javalang.tree.FieldDeclaration):
                node_type = node.type.name
                node_name = node.declarators[0].name
                res[node_name] = node_type
        return res
    except Exception as e:
                                   
        print(f"遍历函数声明/方法调用时出错：{e}")
        return {}
                


def get_funcDecl_call_in_file(ast: javalang.tree.CompilationUnit) -> List[Dict[str, Any]]:
    """
    遍历CompilationUnit中所有的函数（方法）声明，并提取每个函数内部的所有方法调用
    
    Args:
        ast: javalang解析后的CompilationUnit对象
    
    Returns:
        结构化列表，每个元素包含方法声明信息和内部方法调用：
        [
            {
                "method_name": 方法名,          # 如 "getDeptById"
                "method_decl": 方法声明节点,     # MethodDeclaration对象（保留原节点，方便后续扩展）
                "method_calls": [               # 该方法内的所有方法调用
                    {
                        "call_name": 调用的方法名,   # 如 "queryById"
                        "call_owner": 调用所属对象/类名, # 如 "baseMapper"（无则为None）
                        "call_node": 调用节点        # MethodInvocation对象（保留原节点）
                        "call_type": 调用所属类名
                    },
                    ...
                ]
            },
            ...
        ]
    """
    class_field = get_class_field(ast)
    func_info_list = []
    try:
                                              
        for path, node in ast:
            if isinstance(node, javalang.tree.MethodDeclaration):
                            
                method_info = {
                    "method_name": node.name,
                    "method_decl": node,                       
                    "method_calls": []
                }
                
                                                            
                                                   
                for _, child_node in node:
                    if isinstance(child_node, javalang.tree.MethodInvocation):
                                     
                        call_owner = _get_call_owner(child_node)
                        if call_owner not in class_field:
                            continue
                        call_info = {
                                              
                            "call_name": child_node.member,
                                                                                       
                            "call_owner": call_owner,
                                                   
                            "call_node": child_node,
                            "call_type": class_field[call_owner]
                        }
                        method_info["method_calls"].append(call_info)
                
                               
                func_info_list.append(method_info)
        
        return func_info_list
    
    except Exception as e:
                                   
        print(f"遍历函数声明/方法调用时出错：{e}")
        return func_info_list

def _get_call_owner(call_node: javalang.tree.MethodInvocation) -> str:
    """
    辅助函数：提取方法调用的所属对象/类名（如 obj.method() 中的 obj）
    """
    try:
                                  
        if not call_node.qualifier:
            return None
        
                                        
        if isinstance(call_node.qualifier, javalang.tree.ReferenceType):
            return call_node.qualifier.name
                                                    
        elif isinstance(call_node.qualifier, javalang.tree.MemberReference):
            return call_node.qualifier.member
                                                            
        else:
            return str(call_node.qualifier)
    except Exception:
        return None


def analyze_controller_callchain_down(file_path: str):
    with open(file_path, 'r') as file:
        java_code = file.read()
    try:
        ast  = javalang.parse.parse(java_code)
    except Exception as e:
        print(f"解析文件 {file_path} 时出错：{e}")
        return []
    func_in_file = get_funcDecl_call_in_file(ast)
    return func_in_file


if __name__ == '__main__':
    file_path = '/home/huxin/AccessControlSrc/project/pig/pig-visual/pig-codegen/src/main/java/com/pig4cloud/pig/codegen/controller/GenTableController.java'
    func_in_file = analyze_controller_callchain_down(file_path)
    print(func_in_file)
    
    