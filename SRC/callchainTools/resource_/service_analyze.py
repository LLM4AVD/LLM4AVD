# from utils import get_AST
import javalang
import os
MP_FUNC = [
        "save",
        "saveBatch",
        "saveOrUpdate",
        "saveOrUpdateBatch",
        "removeById",
        "removeByMap",
        "remove",
        "removeByIds",
        "updateById",
        "update",
        "updateBatchById",
        "getById",
        "listByIds",
        "getOne",
        "getMap",
        "getObj",
        "count",
        "list",
        "listMaps",
        "listObjs",
        "page",
        "pageMaps",
        "removeBatchByIds"
    ]

def extract_base_service_generic(cu: javalang.tree.CompilationUnit) -> (str, []):
    """
    从CompilationUnit中提取目标接口继承的BaseService泛型类名
    
    Args:
        cu: javalang解析后的CompilationUnit对象
        BaseClassName: 基类的名称，比如BaseService
        
    Returns:
        成功则返回BaseService的泛型类名（如"SysUserPost"），失败返回None

    Example:
    @Service
    @AllArgsConstructor
    public class SysJobLogServiceImpl extends ServiceImpl<SysJobLogMapper, SysJobLog> implements SysJobLogService {}
    输出 ("com.zheng.common.base.BaseServiceImpl, ["SysJobLogMapper", "SysJobLog"])
    因为java是单继承的，所有只会有一个继承类
    """
    
    base_class_name = ''
    templates = []
                                         
    for type_decl in cu.types:
                    
        if isinstance(type_decl, javalang.tree.ClassDeclaration):
                                       
            if type_decl.extends == None:
                continue
            base_class_name = type_decl.extends.name
            for extend in type_decl.extends:
                                                                  
                for ex in extend:
                    if ex and isinstance(ex, javalang.tree.ReferenceType):
                                                      
                        if not ex.arguments:
                            continue
                        for argument in ex.arguments:
                                                          
                            if isinstance(argument, javalang.tree.TypeArgument):
                                for c in argument.children:
                                    if isinstance(c, javalang.tree.ReferenceType) and "mapper" not in c.name.lower():
                                        templates.append(c.name) 
    if base_class_name == '':
        return '', []
             
    for import_item in cu.imports:
        if isinstance(import_item, javalang.tree.Import) and import_item.path.endswith(base_class_name):
            base_class_complete_name = import_item.path
             
    return base_class_complete_name, templates


def get_all_declare_fun(ast: javalang.tree.CompilationUnit) -> []:
    funcs = []
    for path, node in ast:
        if isinstance(node, javalang.tree.MethodDeclaration):
            funcs.append(node.name)
    return funcs

def extract_implemented_service(ast: javalang.tree.CompilationUnit) -> str:
    """
    从CompilationUnit中提取目标接口实现的Service类名
    
    Args:
        cu: javalang解析后的CompilationUnit对象
        
    Returns:
        成功则返回实现的Service类名（如"SysJobLogService"），失败返回None
    
    Example:
    @Service
    @AllArgsConstructor
    public class SysJobLogServiceImpl extends ServiceImpl<SysJobLogMapper, SysJobLog> implements SysJobLogService {
    """
    for type_decl in ast.types:
        if isinstance(type_decl, javalang.tree.ClassDeclaration):
            if type_decl.implements:
                for implement in type_decl.implements:
                    if isinstance(implement, javalang.tree.ReferenceType) and implement.name.endswith("Service"):
                        return implement.name
    return None

def get_base_service_generic(ast: javalang.tree.CompilationUnit) -> ([], []):
    
                                  
    mp_base_service_generic, funcs = extract_base_service_generic(ast)
    if mp_base_service_generic:
        return mp_base_service_generic, funcs
                                                                     
    """
    归提取继承的BaseService泛型类名
    """
    return None


def analyze_service(file_path: str, project_dir: str) -> ([], []):
    """
    分析service文件，提取所有操作实体
    return: 
    1: 提取继承的BaseService泛型类名
    2: 提取所有操作方法
    比如如果使用了mybatis plus框架，那么会自动生成一些函数，这些函数会被作为操作函数补充
    """
    with open(file_path, 'r') as file:
        service_java_code = file.read()
    try:
        service_ast  = javalang.parse.parse(service_java_code)
    except:
        return [], []
    base_class_complete_name, templates = extract_base_service_generic(service_ast)
    
                  
    if 'mybatisplus' in base_class_complete_name:
        return templates, MP_FUNC
    
    complete_path = ''
    target_suffix = f"{base_class_complete_name}".replace(".", "/") + ".java"
    for root, dirs, files in os.walk(project_dir):
        for file_name in files:
                                      
            full_path = os.path.join(root, file_name)
                                    
            rel_path = os.path.relpath(full_path, project_dir)
            
                                            
            if rel_path.endswith(target_suffix):
                complete_path = full_path
    if complete_path == '':
        return templates, []
    with open(complete_path, 'r') as file:
        java_code = file.read()
    base_ast  = javalang.parse.parse(java_code)
    funcs = get_all_declare_fun(base_ast)
    return templates, funcs

def get_service_interface(file_path: str) -> str:
    """
    提取实现的哪个service接口
    """
    with open(file_path, 'r') as file:
        java_code = file.read()
    try:
        ast  = javalang.parse.parse(java_code)
    except:
        return None
    return extract_implemented_service(ast)

if __name__ == "__main__":
    file_path = "/home/huxin/AccessControlSrc/evaluation/project/zheng-1ec8288/zheng-upms/zheng-upms-rpc-service/src/main/java/com/zheng/upms/rpc/service/impl/UpmsUserPermissionServiceImpl.java"
    base_service_generic, funcs = analyze_service(file_path, "/home/huxin/AccessControlSrc/evaluation/project/zheng-1ec8288")
    print(base_service_generic)
    print(funcs)