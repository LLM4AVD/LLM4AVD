import javalang
import os
from utils.path_util import PathUtil
from utils.data_utils import DataUtils
import re

def camel_to_snake(name: str) -> str:
                        
    s1 = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', name)
                       
    s2 = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s1)
    return s2.lower()

def snake_to_camel(snake_case_string):
   words = snake_case_string.split('_')
   camel_case_string = words[0].lower() + ''.join(word.title() for word in words[1:])
   return camel_case_string

def parse_java_code(java_code_path):
    with open(java_code_path,"r",encoding="utf-8") as f:
        java_code=f.read()

    tree = javalang.parse.parse(java_code)

    class_name=""
    members=set()
    for path, node in tree.filter(javalang.tree.ClassDeclaration):
        class_name=node.name.lower()

        for field in node.fields:
            for declarator in field.declarators:
                member_name=declarator.name
                if '_' not in member_name:
                    snake_case_name=camel_to_snake(member_name)
                    camel_case_name=member_name
                else:
                    camel_case_name=snake_to_camel(member_name)
                    snake_case_name=member_name
                members.add(camel_case_name)
                members.add(snake_case_name)
    return class_name,members

def get_db_pattern_from_java_code(java_code_dir_path):
    db_patterns={}
    for root, dirs, files in os.walk(java_code_dir_path):
        for file in files:
            if file.endswith(".java"):
                class_name,members=parse_java_code(os.path.join(root, file))
                db_patterns[class_name]=members
    return db_patterns

if __name__ == '__main__':
    project_name=''
    db_path='/Users/huangzhuochen/IdeaProjects/JeecgBoot/jeecg-boot/jeecg-module-system/jeecg-system-biz/src/main/java/org/jeecg/modules/system/entity'
    output_path=PathUtil.output_data(project_name + '_database_pattern', "json")
    res=get_db_pattern_from_java_code(db_path)
    DataUtils.save_json(output_path,res)