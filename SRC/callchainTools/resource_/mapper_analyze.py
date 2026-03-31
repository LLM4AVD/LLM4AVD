
from ast import arguments
from typing import Any
import javalang
import logging

def extract_base_mapper_generic(cu: javalang.tree.CompilationUnit) -> []:
    """
    从CompilationUnit中提取目标接口继承的BaseMapper泛型类名
    
    Args:
        cu: javalang解析后的CompilationUnit对象
        BaseClassName: 基类的名称，比如BaseMapper
    
    Returns:
        成功则返回BaseMapper的泛型类名（如"SysUserPost"），失败返回None
        
    Example:
    public interface SysDeptMapper extends BaseMapper<SysDept>
    输出 ["SysDept"]
    """
    result = []
                                         
    for type_decl in cu.types:
                    
        if isinstance(type_decl, javalang.tree.InterfaceDeclaration):
                                       
            if type_decl.extends == None:
                continue
            
            for extend in type_decl.extends:
                                                                  
                if extend and extend.arguments:
                    generic_arg = extend.arguments[0]
                                                  
                    if isinstance(generic_arg, javalang.tree.TypeArgument):
                        for c in generic_arg.children:
                            if isinstance(c, javalang.tree.ReferenceType):
                                result.append(c.name)
                  
        if isinstance(type_decl, javalang.tree.ClassDeclaration):
                                       
            if type_decl.extends == None:
                continue
            for extend in type_decl.extends:
                                                                  
                for ex in extend:
                    if ex and isinstance(ex, javalang.tree.ReferenceType):
                                                      
                        if not ex.arguments:
                            continue
                        for argument in ex.arguments:
                                                          
                            if isinstance(argument, javalang.tree.TypeArgument):
                                for c in argument.children:
                                    if isinstance(c, javalang.tree.ReferenceType) and "mapper" not in c.name.lower():
                                        result.append(c.name) 
             
    return result

def extract_interface_methods_types(cu: javalang.tree.CompilationUnit) -> dict:
    """
    遍历接口中定义的所有函数，提取入参/出参的非普通数据类型
    
    Args:
        cu: javalang解析后的CompilationUnit对象
    Returns:
        结构化结果字典：
        {
            "方法名": {
                "params": [{"name": 参数名, "type": 非普通类型名}],  # 无则为空列表
                "return_type": 非普通返回类型名  # 无则为None
            }
        }
        
    Example:
    接口定义：public interface SysDeptMapper {
        SysDept getDeptById(Long id);
        List<SysDept> listDept(SysDeptQuery query, int pageNum);
        void updateDept(SysDept dept);
    }
    输出：
    中间过程：["SysDept", List<SysDept>]
    最终输出 ["SysDept"], 去除掉Collection类的包装
    """
                            
    COMMON_TYPES = {
              
        "int", "long", "float", "double", "boolean", "char", "byte", "short",
             
        "Integer", "Long", "Float", "Double", "Boolean", "Character", "Byte", "Short",
                
        "String", "void", "Object", "BigDecimal", "Date", "LocalDateTime", "LocalDate",
        "List", "Optional", "Collection", "HashMap", "Map", "ConcurrentHashMap"
    }
    
             
    result = []
    
                                  
    for type_decl in cu.types:
                           
        if isinstance(type_decl, javalang.tree.InterfaceDeclaration):
                           
            for method in type_decl.methods:

                                                  
                if method.return_type:                  
                    return_types = _get_type_name(method.return_type)
                            
                    if return_types:
                        result.extend(set(return_types) - COMMON_TYPES)
                
                                                  
                if method.parameters:           
                    for param in method.parameters:
                                 
                        param_types = _get_type_name(param.type)
                                            
                        if param_types:
                            result.extend(set(param_types) - COMMON_TYPES)          
                       
    def _extract_inner_type(type_name):
        """
        递归提取最内层的泛型类型
        例如：List<Map<String, User>> -> User
        """
        while '<' in type_name and '>' in type_name:
                                   
            left_bracket = type_name.rfind('<')
                       
            right_bracket = type_name.index('>', left_bracket)
                       
            type_name = type_name[left_bracket + 1:right_bracket]
        return type_name

                    
    processed_result = []
    for type_name in result:
        inner_type = _extract_inner_type(type_name)
                              
        if inner_type and inner_type not in processed_result:
            processed_result.append(inner_type)
    
    return processed_result

def _get_type_name(type_node) -> []:
    """
    通用工具函数：提取javalang类型节点的名称（兼容泛型/嵌套类型）
    对齐你代码中TypeArgument/ReferenceType的处理逻辑
    """
    def _recur_get_type_name(type_node, return_type: [])->[]:
        """
        递归处理泛型类型，提取所有的类型名
        Example：List<List<EmailProviderV2Entity>>
        提取出来 ["List", "List", "EmailProviderV2Entity"]
        """
        arguments = type_node.arguments
        if arguments:
            for arg in arguments:
                if isinstance(arg, javalang.tree.TypeArgument):
                    for child in arg.children:
                        if isinstance(child, javalang.tree.ReferenceType):
                            _recur_get_type_name(child, return_type)
        return_type.append(type_node.name)
        
    try:
        if isinstance(type_node, javalang.tree.ReferenceType):
            return_type = []
            _recur_get_type_name(type_node, return_type)
            return return_type
        
                                  
        elif isinstance(type_node, javalang.tree.BasicType):
            return [type_node.name]
        
                                   
        else:
            return [str(type_node.name)] if hasattr(type_node, "name") else [str(type_node)]
    except Exception as e:
                         
        print(f"Error: Failed to extract type name from {type_node}: Error {e}")
        return []

def analyze_mapper(file_path: str)->[]:
    """
    分析mapper文件，提取所有操作实体
    """
    with open(file_path, 'r') as file:
        java_code = file.read()
    try:
        ast  = javalang.parse.parse(java_code)
    except Exception as e:
        logging.error(f"Error: Failed to parse mapper file {file_path}: Error {e}")
        return []
    resources = []
    resources.extend(extract_base_mapper_generic(ast))
    resources.extend(extract_interface_methods_types(ast))
    resources = list(set(resources))
    return resources

if __name__ == "__main__":
    file_path = "/home/huxin/AccessControlSrc/evaluation/project/PublicCMS-d73b833/publiccms-parent/publiccms-core/src/main/java/com/publiccms/logic/dao/cms/CmsCategoryAttributeDao.java"
    resources = analyze_mapper(file_path)
    print(resources)