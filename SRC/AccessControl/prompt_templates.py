import copy
import json
operation_desc = {
    "find": "includes finding, getting, querying, selecting etc. Any operation of getting, searching ,accessing and "
            "returning an object is considered to be fall into this category",
    "create": "includes adding, saving, etc. new entries",
    "edit": "includes various editing operations such as updating, modifying, importing, etc.",
    "remove": "includes all delete operations"
}

operation_example={
    "find":"""
    Here is an example output of extracted **find** operation:
    ### Example Output:
            ```json
            [
                {{
                    "Operation Description": "Getting user info from the system by userId.",
                    "Relevant Code Snippet": "userMapper.getUserById(userId);"
                    "Operation Location": "UserService.java:getUser"
                    "Parameters": ["userId"],
                    "Object": "user"
                    "Object Description": "The user information"
                }}
            ]```
    """,
    "create":"""
    Here is an example output of extracted **create** operation:
    ### Example Output:
            ```json
            [
                {{
                    "Operation Description": "Inserting a new user into the system after validation.",
                    "Relevant Code Snippet": "userMapper.insertUserById(userId,newUserInfo);"
                    "Operation Location": "UserService.java:insertUser"
                    "Parameters": ["userId","newUserInfo"],
                    "Object": "user"
                    "Object Description": "The user to be inserted"
                }}
            ]```
    """,
    "edit":"""
    Here is an example output of extracted **edit** operation:
    ### Example Output:
            ```json
            [
                {{
                    "Operation Description": "Updating user info into the system.",
                    "Relevant Code Snippet": "userMapper.updateUserById(userId,updateUserInfo);"
                    "Operation Location": "UserService.java:updateUser"
                    "Parameters": ["userId","updateUserInfo"],
                    "Object": "user"
                    "Object Description": "The user to be updated"
                }}
            ]```
    """,
    "remove":"""
    Here is an example output of extracted **remove** operation:
    ### Example Output:
            ```json
            [
                {{
                    "Operation Description": "remove a user from the system.",
                    "Relevant Code Snippet": "userMapper.removeUserById(userId);"
                    "Operation Location": "UserService.java:removeUser"
                    "Parameters": ["userId"],
                    "Object": "user"
                    "Object Description": "The user to be removed"
                }}
            ]```
    """
}

class Prompt:

    def judge_code_snippet(self, callchain, relevant_code):
        return f"""
                Does the following code snippet A appear in the code snippet B?
                1. **Note**:
                   It is allowed for some differences between the two pieces of code that do not affect the semantics, such as redundant or missing spaces or line breaks between code A and code B, in which case we still assume that code A appears in code B
                2. **output format**：
                   You just need to answer "yes" or "no", and don't add any extra words that will affect next steps

                Here is the code snippet A:
                {relevant_code}

                Here is the code snippet B:
                {callchain}
        """

    def classify_func_by_role(self, func_name, code_snippet, call_chains, call_chain_code):
        call_chain_down = call_chains[0]
        call_chain_up = call_chains[1]
        call_chain_code_down = call_chain_code[0]
        call_chain_code_up = call_chain_code[1]
        return f"""
        In a Java web project, users accessing the system can typically be divided into administrator users and regular users.
        Accordingly, some function interfaces will have restrictions based on user roles. 
        For example, some function interfaces are only callable by administrator users, while others are accessible by any user.
        **Task Description:**
        Based on the understanding above, I will provide you with a segment of function code from Java web,
         as well as other functions in the call chain of that function, namely the caller or callee of that function. 
         Your task is to determine whether this function is only allowed to be called by administrator users. 
         If so, please answer yes. If other users can also call it, or if you cannot answer based on this information, please answer no.

        **output format**：
        You just need to answer "yes" or "no", and don't add any extra words that will affect next steps


        Here is the code snippet of function {func_name} from a Java web project:
        '''
        {code_snippet}
        '''

        The contextual functions called by {func_name} are as follows:
        '''
        {call_chains[0] if len(call_chains[0]) > 0 else [
            f"The function {func_name} does not call other functions"]}
        '''

        The contextual functions that call {func_name} are as follows:
        '''
        {call_chains[1] if len(call_chains[1]) > 0 else [
            f"The function {func_name} does not called by other functions"]}
        '''

        Here are code snippet of functions which called by {func_name}:
         '''
         {call_chain_code[0] if len(call_chain_code[0]) > 0 else f"The function {func_name} does not call other functions"}
         '''

        Here are code snippet of functions that call {func_name}:
         '''
         {call_chain_code[1] if len(call_chain_code[1]) > 0 else f"The function {func_name} does not called by other functions"}
         '''

        """

    def remove_None_privilege_check_operation(self, relevant_code, permission_check_code_relevant):
        return f"""
        ### Task Description:
               You will be provided with two code snippets:
               1."code snippet A": A code segment for privilege check may be a function call, an annotation, or a control logic, etc.
               2."code snippet B": The operation of this code segment belongs to one of the following: create, delete, update, or query.
               Your task is to determine whether Code Segment A is a privilege check. If it is, further determine whether it is a privilege check for Code Segment B.
                If code snippet A is a privilege check, please answer "yes" or "no" based on whether the code snippet A is a privilege check for code snippet B.
                If code snippet A is not a privilege check, please answer "no".


        ### Output Format:
                The output must be valid JSON as shown below:
                ```json
                {{
                     "The function of code snippet A": A brief summary of the functionality of code snippet A.
                     "The function of code snippet B": A beirf summary of the functionality of code snippet B.
                     "is_privilege_check": "<yes or no>"
                }}
                ```

        *** Note:
                If code snippet A is a simple query, update, or other operations based on certain parameters, it does not count as a permission check. For example, userService.queryList(params); is not a permission check; it is merely a query operation based on the params parameter.
                Here is the input code snippet A and B:
                '''
                "code snippet A":{permission_check_code_relevant}
                '''
                "code snippet B":{relevant_code}

    """

    def reduce_false_positives_prompt(self, func_name, code_snippet, call_chains, call_chain_code, missing_permission):
        call_chain_down = call_chains[0]
        call_chain_up = call_chains[1]
        call_chain_code_down = call_chain_code[0]
        call_chain_code_up = call_chain_code[1]

        return f"""
    ### Task Description: 
    Given the provided code snippet and its surrounding context, your task is to determine whether the reported "missing permission" for the code snippet is a false positive. Specifically, if the code snippet does not actually require the permission checks indicated by the "missing permission," it should be classified as a false positive. Conversely, if the permission checks are indeed necessary, it is not a false positive.
    If the check in "missing permission" is false positive, please answer "yes"; otherwise, answer "no".And give your reason.


    ### Criteria for judgment:
    1.The missing permission should only be considered if the operation associated with the missing permission is truly similar to the operation in the current case. If they are not similar, then the missing permission is a false alarm.
    2.As long as the code context contains permission equivalent to "missing permission," it is a false alarm.


    ### Note:
        1.The code context refers to locating the function to which the given code snippet belongs and obtaining the contextual information of that function.
        2.The code context includes the function itself and the functions that call it, as well as the functions called by it.
        3.The code snippet is in the {func_name} function.

    ### Output Format:
        The output must be valid JSON as shown below:
        ```json
        {{
                "is_false_positive": "<yes or no>"
                "The reason": "<The reason why it is a false positive or not>"
        }}
        ```

    Here is the content of the code snippet and its operation description.
        '''
        {code_snippet}
        '''

    The contextual functions called by {func_name} are as follows:
        '''
        {call_chains[0] if len(call_chains[0]) > 0 else [
            f"The function {func_name} does not call other permission-related functions"]}
        '''

    The contextual functions that call {func_name} are as follows:
        '''
        {call_chains[1] if len(call_chains[1]) > 0 else [
            f"The function {func_name} does not called by other permission-related functions"]}
        '''

    Here are code snippet of functions which called by {func_name}:
         '''
         {call_chain_code[0] if len(call_chain_code[0]) > 0 else f"The function {func_name} does not call other permission-related functions"}
         '''

    Here are code snippet of functions that call {func_name}:
         '''
         {call_chain_code[1] if len(call_chain_code[1]) > 0 else f"The function {func_name} does not called by other permission-related functions"}
         '''


    Here is the content of the missing permissions and its operation description.
        '''
        {missing_permission}
        '''


    """

    def summarize_permissions_prompt(self, all_permission):
        return f"""
         ### Task Description
         You will receive a list containing multiple permission check (Permission Requirements) objects with the same format. Each object contains the following fields:
           ```
        {{
          "Description": "<clear and specific access control requirement>",
          "Details": "<detailed description of the specific code behavior of the permission check>",
          "Relevant Code Snippet": "<code enforcing permission checks>",
          "Detailed Code Snippet": "<expanded code showing the implementation of the permission check function or API>"
        }}
        ```
        All objects in this list belong to the same category of permission checks, and they are semantically and syntactically similar or consistent in terms of code.
        Your task is to analyze what kind of permission verification or security control this category of permission checks performs overall and provide a concise summary (about 30 words).

        ### Notes
        1.The summary should be clear and accurate, expressing the essential purpose of this category of permission checks in terms of access control.
        2.Avoid simply repeating the content of the Description field; instead, summarize based on the code details.

        ### Output Format
        The summary must be in the following JSON format:
        ```json
        {{
        "permission_description": "<用一句话准确描述这一类权限检查的目的和逻辑>"
        }}
        ```
        """

    def remove_duplicate_permission_permissions_prompt(self, all_permission):
        return f"""
            ### Task Description

            You will receive a list containing multiple permission checks (Permission Requirements), each with the following fields:

            ```json
            {{
    "Description": "<clear and specific access control requirement>",
                "Details": "<detailed description of the specific code behavior of the permission check>",
                "Relevant Code Snippet": "<code enforcing permission checks>",
                "Detailed Code Snippet": "<expanded code showing the implementation of the permission check function or API>"
            }}
            ```

            Your task is to perform a semantic analysis of these permission checks and categorize those with the same functionality. The code snippets in "Relevant Code Snippet" and "Detailed Code Snippet" are from a Java web project using the Spring and Shiro frameworks, and they are related to permission checks. Please deeply understand the authorization logic behind the code and then make judgments based on the functionality of the permission checks, grouping items with the same functional permission checks together.

            ### Judgement Rules

            You can determine whether the input permission checks are similar or identical based on the following rules:

            1. If two permission checks have similar logic or perform the same function, even if their descriptions or code implementations differ, they can be considered similar.

            ### Output Format

            1. The output format is a JSON array, where each element represents a category (i.e., a group of semantically consistent or similar permission checks).
            2. Each category is an array containing multiple permission check objects from the original input.
            3. The content of the permission checks in the output must be identical to the input, with no rewriting or merging.
            4. If a permission check is not consistent with any other permission checks, it should be placed in a separate category.
            5. The total number of permission checks in the output should be the same as in the input to be correct.

            The output format must be valid json as shown below:

            ```json
            [
                [
                    {{
                        "Description": "...",
                        "Details": "...",
                        "Relevant Code Snippet": "...",
                        "Detailed Code Snippet": "..."
                    }},
                    {{
                        "Description": "...",
                        "Details": "...",
                        "Relevant Code Snippet": "...",
                        "Detailed Code Snippet": "..."
                    }}
                ],
                [
                    {{
                        "Description": "...",
                        "Details": "...",
                        "Relevant Code Snippet": "...",
                        "Detailed Code Snippet": "..."
                    }},
                    {{
                        "Description": "...",
                        "Details": "...",
                        "Relevant Code Snippet": "...",
                        "Detailed Code Snippet": "..."
                    }}
                ]
            ]
            ```            
        """

    def detect_most_complete_access_control_model(self, access_control_models):
        return f"""
                ### Task Description: 
                    You will be given a JSON object that includes:  
                    - a target `resource`,  
                    - an `operation_type` to be performed on that resource,  
                    - and a list of `access_control_model` entries describing how permission is enforced at different code locations.

                    Your task is to analyze all `access_control_model` entries and identify the one with the **most comprehensive permission requirements** for executing the specified operation.

                ### Evaluation Criteria:
                    Please evaluate each entry's completeness based on the following criteria:

                    1. **Number of Permission Checks**: Does the entry involve multiple steps of permission validation, such as authentication, role/permission checks, and data-level constraints?
                    2. **Clarity and Richness of Descriptions**: Are the `Description` and `Details` fields specific, well-explained, and do they clearly describe the purpose and scope of the permission?
                    3. **Multiplicity of Permission Requirements**: Are there multiple permission rules listed under `Permission Requirements`, indicating a more thorough access control scheme?

                ### Output Format
                    Return `access_control_model` entry (unchanged from the input), and **add** a `justification` field explaining why this entry is the most comprehensive, based on the criteria above.
                    The output must be valid JSON as shown below:
                    ```json
                    [
                        {{
                            "location": "<location>",
                            "Operation Description": "<description of the operation>",
                            "Relevant Code Snippet": "<main code snippet>",
                            "Object": "<target object>",
                            "Object Description": "<description of the object>",
                            "Permission Requirements": [
                                {{
                                    "Description": "<summary of the permission requirement>",
                                    "Details": "<detailed explanation of how permission is enforced>",
                                    "Relevant Code Snippet": "<the function or code that checks the permission>",
                                    "Detailed Code Snippet": "<full implementation or logic of the permission check>"
                                }}
                                // possibly more entries here
                            ],
                            "justification": "<your explanation of why this entry is the most comprehensive, based on the criteria above>"
                        }}
                    ]
                    ```

                ***Note:***
                Here is the input access control model:
                '''
                {access_control_models}
                '''

                """

    def detect_lack_of_permission_check(self, most_complete_access_control_model, access_control_models):
        return f"""
        ### Task Description: 
            You will be provided with two access_control_model JSON structures:
            1."most_complete_access_control_model": the most comprehensive and complete version, containing all necessary permission checks.
            2."access_control_model": a model that needs to be analyzed for potentially missing permission checks.
             Your task is to:  
            1.Identify whether the access control checks in the model under inspection are missing any permission checks compared to the most_complete_access_control_model.
            2.If any permission checks are missing, list all the Permission Requirements that are present in the complete model but not in the one being analyzed.

        ### Output Format：
            The output must be valid JSON as shown below:
            ```json
            [ 
                {{
                    "Description": "<clear and specific access control requirement>", 
                    "Details": "<detailed description of the specific code behavior of the permission check>", 
                    "Relevant Code Snippet": "<code enforcing permission checks>",
                    "Detailed Code Snippet": "<expanded code showing the implementation of the permission check function or API>" 
                }}
            // possibly more entries here 
            ]
            ```
            If there are no missing permission requirements, return an empty array like this:
            ```json
            []
            ```
        ***Note:***
        Here is the most complete access control model:
        '''
        {most_complete_access_control_model}
        '''

        Here is the access control model:
        '''
        {access_control_models}
        '''

        """

    """
    这段函数是在“构造发给大模型的指令（Prompt）”，要求模型从给定函数代码及其上下文中，提取对指定资源的所有操作信息，并按固定 JSON 格式返回。核心点如下：
    目标:
        让模型分析函数 func_name 的代码片段以及上下文调用关系，找出对资源 resource 的操作。
    要提取的内容:
        操作类型 Operation Type：限定为 read / create / edit / remove 四类。
        操作描述 Operation Description：更细粒度的自然语言说明。
        相关代码片段 Relevant Code Snippet：在 func_name 内执行操作的具体代码。
        对象 Object 及其说明 Object Description：操作作用的对象及来源说明。
    约束与排除"
        只统计实际的资源操作；各种“检查类”逻辑（校验、唯一性检查、是否存在、权限范围检查等）明确排除。
        重点聚焦在当前函数 func_name 的实现；上下文函数（上下游调用链）仅用于理解语义，不作为提取代码片段的来源。
        只关注资源 resource，避免提取对其他资源的操作。
    上下文信息注入:
        code_snippet：当前函数代码。
        call_chains：下游被调用函数列表与上游调用者列表，用于辅助理解。
        call_chain_code：上下文函数的代码片段，用作参考。
    输出格式:
        要求严格输出为 JSON 数组，每个元素含固定字段，示例也在提示中给出。
    
    """
    def extract_operation_list_prompt(self, resource, func_name, code_snippet, call_chains, call_chain_code):
        call_chain_down = call_chains[0]
        call_chain_up = call_chains[1]
        call_chain_code_down = call_chain_code[0]
        call_chain_code_up = call_chain_code[1]

        return f"""
                    **CRITICAL**: Ensure ALL Parameters in your JSON output are properly escaped to avoid parsing errors. 
                    Unescaped quotation marks in Parameters will cause JSONDecodeError.
                    
                    Please analyze the following code snippet of function {func_name} along with the provided function call snippet to identify all operations performed on the resource {resource}. Extract the operation type, operation description, and the relevant code snippet that executes the operation. Please pay attention to the following points:  

                    1. **Operation Type**: All resource operations fall into one of the following four categories. You need to determine which type of operation is performed on the resource:  
                       - **find** (includes finding, getting, querying, selecting etc. Any operation of getting, searching ,accessing and returning an object is considered to be fall into this category)  
                       - **create** (includes adding, saving, etc. new entries)  
                       - **edit** (includes various editing operations such as updating, modifying, importing, etc.)  
                       - **remove** (includes all delete operations)  

                    2. **Operation Description**: A more detailed description of the operation performed on the resource, not just the operation type. For example, "Updating user password and role information."  

                    3. **Relevant Code Snippet**: The specific code snippet within the given context where the operation is executed.  

                    4. **Operation location**: When you extract an operation and its relevant code from a function, also record the **original location information** that accompanies the function in the provided context.  
                        Use the exact location string as given **never invent or alter filenames or function names**.

                    5. **Parameters**: Based on the extracted **Relevant Code Snippet** that performs the operation:  
                        - If the operation is carried out by calling a function, extract the arguments passed to that function and return them as a **list**.  
                        - If the operation is not implemented via a function call, or the function takes no arguments, return an empty list [].

                    6. **Note**: Operations that should be included: These are the types of operations mentioned in the first point such as finding, creating, editing, and removing that may be performed on the resource {resource}.
                       Operations that should be excluded: Any form of checking operations, such as verifying data scope, checking user entities, determining the existence of an item, or ensuring uniqueness, should not be included.
                       The **find** category of operations serve as the basis for the other three categories of operations. When extracting the other three operations, carefully check whether there is a "find" operation in the code.
                       Additionally, we focus exclusively on the operations performed on Resource {resource}. Operations involving other types of resources within the function should not be extracted, as doing so could lead to misinterpretation or confusion in subsequent steps.


                   7. **Important**: 
                        You must extract operations not only from the current function but also from its surrounding code context. The final output operation list **must** include at least the folllowing two parts:
                        **Part 1** - operations from the current function {json.dumps(code_snippet["location"])}(mandatory):
                        You should identify all operations with corresponding source code snippets performed on the target resource inside the current function.
                        **Part 2** - operations performed in related functions within the provided code context(callers and callees):
                        You should examine every function that calls the current function, and every function that the current function calls to see whether any of them performs an operation on the same resource.
                        A list is considered complete only when both parts are present!!!

                    8. **CRITICAL JSON FORMATTING RULE**: Parameters list elements MUST be properly escaped to comply with JSON format:
                       - If any parameter contains quotation marks, escape ALL internal quotation marks with backslashes (\" → \\\")
                       - If the parameter itself contains string literals with quotation marks, escape them appropriately
                       - **MANDATORY EXAMPLES**:
                         * "%"+search+"%" → "\\\"%\\\"+search+\\\"%\\\""
                         * "text with \"quotes\"" → "text with \\\"quotes\\\""
                       - **FAILURE TO ESCAPE WILL CAUSE JSON PARSING ERRORS**
                    
                    9. **MANDATORY OUTPUT FORMAT**: 
                    ```json
                    [
                      {{
                        "Operation Type": "<operation type>", 
                        "Operation Description": "<detailed operation description>", 
                        "Relevant Code Snippet": "<code snippet>",
                        "Operation Location": "<file name: function name>",
                        "Parameters": "<parameters list - MUST BE PROPERLY ESCAPED>",
                        "Object": "<object of the operation>",
                        "Object Description": "<detailed description of the object (pay attention to the source of the object)>"
                      }}
                    ]```

                    ### Example Output (Note the proper escaping):
                        ```json
                        [
                            {{
                                "Operation Type": "create",
                                "Operation Description": "Inserting a new user into the system after validation.",
                                "Relevant Code Snippet": "userMapper.insertUser(userId);",
                                "Operation Location": "UserService.java:insertUser",
                                "Parameters": ["userId", "\\\"%\\\"+search+\\\"%\\\""],
                                "Object": "user",
                                "Object Description": "The user to be inserted"
                            }}
                        ]
                        ```


                    Here is the code snippet of function {func_name}:
                     '''
                     {json.dumps(code_snippet)}\n
                     '''

                    The contextual functions called by {func_name} are as follows:
                    '''
                    {json.dumps(call_chains[0]) if len(call_chains[0]) > 0 else json.dumps([
            f"The function {func_name} does not call other permission-related functions"])}
                    '''

                    The contextual functions that call {func_name} are as follows:
                    '''
                    {json.dumps(call_chains[1]) if len(call_chains[1]) > 0 else json.dumps([
            f"The function {func_name} does not called by other permission-related functions"])}
                    '''

                    Here are code snippets of contextual functions:
                     '''
                     {json.dumps(call_chain_code)}
                     '''
                    """

    def extract_operation_type_prompt(self, resource, func_name, code_snippet, call_chains, call_chain_code,
                                      operation_type):
        call_chain_down = call_chains[0]
        call_chain_up = call_chains[1]
        call_chain_code_down = call_chain_code[0]
        call_chain_code_up = call_chain_code[1]

        return f"""
                    Please analyze the following code snippet of function {func_name} along with the provided function call snippet to identify {operation_type} operation performed on the resource {resource}. Extract the operation type, operation description, the relevant code snippet that executes the operation and parameters of the function that performs the operation. Please pay attention to the following points:  

                    1. **{operation_type.upper()} Operation**: 
                        The definition of {operation_type} operation is as follows:{operation_desc[operation_type.lower()]}

                    2. **Operation Description**: A more detailed description of the operation performed on the resource, not just the operation type. For example, "Updating user password and role information."  

                    3. **Relevant Code Snippet**: The specific code snippet within the given context where the operation is executed.  

                    4. **Operation location**: When you extract an operation and its relevant code from a function, also record the **original location information** that accompanies the function in the provided context.  
                        Use the exact location string as given **never invent or alter filenames or function names**.

                    5. **Parameters**: Based on the extracted **Relevant Code Snippet** that performs the operation:  
                        - If the operation is carried out by calling a function, extract the arguments passed to that function and return them as a **list**.  
                        - If the operation is not implemented via a function call, or the function takes no arguments, return an empty list ```json[]```.

                    6. **Note**: 
                        Operations that should be excluded: Any form of checking operations, such as verifying data scope, checking user entities, determining the existence of an item, or ensuring uniqueness, should not be included.
                        Additionally, we focus exclusively on the operations performed on Resource {resource}. Operations involving other types of resources within the function should not be extracted, as doing so could lead to misinterpretation or confusion in subsequent steps.
                        


                   7. **Important**: 
                        You must extract operations not only from the current function but also from its surrounding code context. The final output operation list **must** include at least the folllowing two parts:
                        **Part 1** - {operation_type} operation from the current function {code_snippet["location"]}(mandatory):
                        You should identify all operations with corresponding source code snippets performed on the target resource inside the current function.
                        **Part 2** - {operation_type} operation performed in related functions within the provided code context(callers and callees):
                        You should examine every function that calls the current function, and every function that the current function calls to see whether any of them performs {operation_type} operation on the same resource.
                        A list is considered complete only when both parts are present!!!

                    8. The final output should be in JSON format, following this structure(Do not add any other text to avoid affecting subsequent steps!!!):
                    
                    ```json
                    [
                      {{
                        "Operation Description": "<detailed operation description>", 
                        "Relevant Code Snippet": "<code snippet>",
                        "Operation Location": "<file name: function name>",
                        "Parameters": "<parameters list>",
                        "Object": "<object of the operation>",
                        "Object Description": "<detailed description of the object (pay attention to the source of the object)>"
                      }}
                    ]```

                    {operation_example[operation_type.lower()]}


                    Here is the code snippet of function {func_name}:
                     '''
                     {code_snippet}\n
                     '''

                    The contextual functions called by {func_name} are as follows:
                    '''
                    {call_chains[0] if len(call_chains[0]) > 0 else [
            f"The function {func_name} does not call other permission-related functions"]}
                    '''

                    The contextual functions that call {func_name} are as follows:
                    '''
                    {call_chains[1] if len(call_chains[1]) > 0 else [
            f"The function {func_name} does not called by other permission-related functions"]}
                    '''

                    Here are code snippets of contextual functions:
                     '''
                     {call_chain_code}
                     '''
                    """

    """
        这个函数用于“构造提示词给大模型”，让模型基于某个函数的代码与其上下文，对“已有的操作列表”逐项补充对应的“权限检查要求”。要点如下：
        输入:
            resource: 目标资源名
            func_name: 当前函数名
            code_snippet: 当前函数的代码
            call_chains: 下游/上游函数列表（辅助理解上下文）
            call_chain_code: 上下文函数的代码片段
            operation_list: 已经抽取出的资源操作清单（类型/描述/代码/对象等）
        要求模型完成的事:
            针对 operation_list 里的每一条操作，分析它“实际需要的权限检查”，并把这些检查以结构化 JSON 形式填入该操作的 Permission Requirements 字段。
            强调只抽取“权限检查相关代码”，不要重复操作本身的代码；若无可用检查代码，要求填 "None" 占位以保持 JSON 合法。
            权限检查可能来自三类常见形式：函数调用接口、注解、控制逻辑；但也提示模型不要局限于这三类。
            允许在上下文函数（调用者/被调用者）里查找与本操作相关的权限检查，并将其实现细节展开到 Detailed Code Snippet。
        重要约束:
            仅关注对当前 resource 的权限检查，避免混入其他资源的权限。
            输出必须是“扩展后的原操作列表”且严格符合指定 JSON 结构，保证可机读。
        输出格式:
            要求严格输出为 JSON 数组，每个元素含固定字段，示例也在提示中给出。
    """

    def extract_permission_requirements_prompt(self, resource, func_name, code_snippet, call_chains, call_chain_code,
                                               operation_list):
        call_chain_down = call_chains[0]
        call_chain_up = call_chains[1]
        call_chain_code_down = call_chain_code[0]
        call_chain_code_up = call_chain_code[1]

        return f"""
    ### Task Description: 
    Analyze the following code snippet and its contextual function calls to determine the required permissions for each operation in the provided operation list operating on the resource `{resource}`(output only the permissions that actually exist in the code snippet or its context).

    ### Instructions:

    1. **Understanding the Operation List:**  
       Each operation entry contains the following fields:  
       - **Operation Type**: One of the four categories — `find`, `create`, `remove`, or `edit`.  
       - **Operation Description**: A detailed explanation of the operation beyond its type.  
       - **Relevant Code Snippet**: The specific code segment within the function `{func_name}` where the operation is executed. 
       - **Parameters**: A list of the parameters of the function that performs the operation.  

    2. **Permission Requirement Analysis:**  
       - For each operation in the list, analyze **ALL** required permission conditions based on its **operation type, description, and relevant code snippet**.  
       - Consider the **context** of the code snippet to determine any implicit or explicit permission checks.  

    3. **Permission Extraction Criteria:**  
       The extracted permission requirements must be **clear, concise, and specific**. Each permission requirement must include:  
       - **Description**: A short, explicit statement describing the necessary access control conditions before performing the operation.  
       - **Details**: A detailed description of the permission check, describe the specific code behavior of the check, if the check is an api call, describe the specific implementation logic of the api.  
       - **Relevant Code Snippet**: The specific lines of code that enforce the permission check.The code that checks permissions may be a function that checks for a certain permission, an annotation for checking permissions, a control logic for checking permissions, and so on.
       - **Detailed Code Snippet**: If the **Relevant Code Snippet** contains a function or API call (e.g., `checkPermission(user)`), then extract the **actual implementation details** of this function from the provided call chain or surrounding code. This ensures a deeper understanding of how permissions are enforced. 

    4. **Important:**
       Focusing on the permission checks that are done before the operation on the {resource}. Be sure to avoid extracting permission checks related to other resources! Some permission checks may also appear within contextual functions, so in addition to focusing on the code of the {func_name} itself, it is also necessary to analyze its contextual code
       Don't repeat the code snippet in the operation list!!!! Only extract the code related to permission checks. If there is no relevant code for the permission requirements, return {None} in the relevant code snippet field.
       Pay attention to extracting the permission check code for each specific operation, distinguish different permission checks for different operations, and avoid duplication or omission.
       When extracting permission code, please carefully compare whether the code appears in the following functions,do not extract code snippets outside of the code for them: f {[func_name] + call_chain_down + call_chain_up}

    5.**Note:**
        It is very important that the Relevant/Detailed Code Snippet in the extracted Permission Requirements must actually exist in the given code!!!
        It can be assumed that the permission checks that appear in the caller function are still valid for the callee function. Therefore, when there are operations on {resource} in the callee, the permission checks from the caller should also be extracted.
        In addition to permission checks, we also pay attention to **other types of checks**, such as those for uniqueness, consistency, and existence.

    6.**Forms of Permission Checks**:
    Permission checks can take on a variety of forms. Here, we introduce three of the more common types. However, remember that this does not mean there are only three forms of permission checks. When encountering other types of permission checks, they must also be identified!

    - **Function Call Interface**: This involves directly calling a function. Based on the input parameters, the internal logic of these functions will implement the corresponding permission checks. These functions typically accept parameters such as user IDs, resource IDs, user tokens, etc.

    - **Annotations**: This is a common approach in aspect-oriented programming. When defining a function, corresponding permission annotations are specified. Each time the function is called, the annotation logic is also invoked to check user permissions, ensuring that the function can only be called if the current user has the permissions specified in the annotation.

    - **Control Logic**: This involves using control statements, such as `if` statements, to check user permissions before performing specific operations on a resource. For example, it might check whether the user is an admin or whether the user owns the resource in question.

    7. **Output Format:**  
       The final output should **extend the original operation list** by appending the extracted permission requirements.  
       For the same operation, it is possible to check its permissions in multiple places in the code, so there can be multiple permission requirements for an operation list.
       The output format must be **valid JSON**, following this structure:  

       ```json
       [
           {{
               "Operation Type": "<operation type>",
               "Operation Description": "<detailed operation description>",
               "Relevant Code Snippet": "<code snippet>",
               "Operation Location": "<file name: function name>",
               "Parameters": "<parameters list>",
               "Object": "<object of the operation>",
               "Object Description": "<detailed description of the object>",
               "Permission Requirements": [
                    {{
                    "Description": "<clear and specific access control requirement>",
                    "Details": "<detailed description of the specific code behavior of the permission check>",
                    "Relevant Code Snippet": "<code enforcing permission checks>",
                    "Detailed Code Snippet": "<expanded code showing the implementation of the permission check function or API>"
                   }}
                ]
           }}
       ]```

       If no extracted "Permission Requirements" are found,return all fields within "Permission Requirements" as None to ensure the JSON format is correct.The output format must be **valid JSON**, following this structure: 

        ```json
       [
           {{
                "Operation Type": "<operation type>",
               "Operation Description": "<detailed operation description>",
               "Relevant Code Snippet": "<code snippet>",
               "Operation Location": "<file name: function name>",
               "Parameters": "<parameters list>",
               "Object": "<object of the operation>",
               "Object Description": "<detailed description of the object>",
               "Permission Requirements": [
                    {{
                    "Description": "None",
                    "Details": "None",
                   "Relevant Code Snippet": "None",
                   "Detailed Code Snippet": "None"
                   }}
                ]
           }}
       ]```

    ### Example:

    ***Input (Operation list):***
    [
        {{
            "Operation Type": "edit",
            "Operation Description": "Updating existing user information after validation.",
            "Relevant Code Snippet": "userMapper.updateUser(userId);"
            "Operation Location": "UserService.java:updateUser",
            "Parameters": ["userId"],
            "Object": "user"
            "Object Description": "The user to be updated"
        }}
    ]

    ***Expected Output:***
    ```json
    [
        {{
            "Operation Type": "edit",
            "Operation Description": "Updating existing user information after validation.",
            "Relevant Code Snippet": "userMapper.updateUser(userId);",
            "Operation Location": "UserService.java:updateUser",
            "Parameters": ["userId"],
            "Object": "user",
            "Object Description": "The user to be updated",
            "Permission Requirements": [
                {{
                "Description": "Requires permission to check if the user is allowed to update the user information.",
                "Details": "Ensure the UserID is not empty and cannot modify the admin information",
                "Relevant Code Snippet": "Function that check permissions",
                "Detailed Code Snippet": "specific code of the function"
                }},
                {{
                "Description": "Requires permission to edit existing role information.",
                "Details": "The permission check is enforced by the @PreAuthorize annotation in the calling method, which ensures that the user has the necessary permissions to perform the edit operation on roles.",
                "Relevant Code Snippet": "Annotation that check permissions",
                "Detailed Code Snippet": "specific code of the annotation"
                }},
                {{
                "Description": "Requires permission to edit existing role information.",
                "Details": "The permission check is enforced by the .eq(input_id,target_id) control logic in the calling method, which ensures that the input id is consistent with the target object's  id which will be manipulated in the database.",
                "Relevant Code Snippet": "control logic that check permissions",
                "Detailed Code Snippet": "specific code of the control logic"
                }}
            ]
        }}
    ]```

    ***Note:***

    Here is the code snippet of function {func_name}:
         '''
         {code_snippet}
         '''

    The contextual functions called by {func_name} are as follows:
        '''
        {call_chains[0] if len(call_chains[0]) > 0 else [
            f"The function {func_name} does not call other permission-related functions"]}
        '''

    The contextual functions that call {func_name} are as follows:
        '''
        {call_chains[1] if len(call_chains[1]) > 0 else [
            f"The function {func_name} does not called by other permission-related functions"]}
        '''

    Here are code snippet of functions which called by {func_name}:
         '''
         {call_chain_code[0] if len(call_chain_code[0]) > 0 else f"The function {func_name} does not call other permission-related functions"}
         '''

    Here are code snippet of functions that call {func_name}:
         '''
         {call_chain_code[1] if len(call_chain_code[1]) > 0 else f"The function {func_name} does not called by other permission-related functions"}
         '''

    Here is the operation list:
         '''
        {operation_list}
         ''' 
         """

    def detect_diff_access_control_models(self, resource, access_control_models):
        return f"""
### Task Description
Analyze the provided access control models for the resource `{resource}` to identify potential access control vulnerabilities.

### Input Data Structure
Each access control model contains the following components:
- **Location**: The source code location (file and function) where the access control is implemented
- **Operator**: The entity performing operations on the resource
- **Operation Description**: Detailed description of the operation being performed
- **Permission Requirements**: Specific permissions needed to execute the operation

### Analysis Requirements

Compare all provided access control models to identify whether there are some access control models performing the same operation but with different permission requirements. This consistency may lead to potential authentication vulnerabilityes. Output the access control models that lack critical permissions and may lead to vulnerabilities.

### Important Considerations:
1. **Identify a "baseline" access control model**:
   - Select the most **comprehensive** access control model (i.e., the one with the most permission checks) as the baseline.
   - Compare other models against this baseline to detect missing permissions.
2. **Filter out trivial cases**:
    - If **all fields in the "Permission Requirements" of Input Data are `None`**, ignore this entry **unless all other access control models also have `None` permissions**.
    - Focus on **entries where "Permission Requirements" contain meaningful security checks**.

### Output Format
If no model is missing critical permissions, return `{{None}}`.

If inconsistencies (the access control model which missing critical permissions compared with other access control models) are detected, provide a detailed analysis in the following JSON format:
```json
[
    {{
        "resource": "<resource name>",
        "location": "<file:function>",
        "operation_type": "<operation type>",
        "Operation Description": "<detailed operation description>",
        "Relevant code snippet": "<code snippet>",
        "Permission Requirements": [{{
           "Description": "<clear and specific access control requirement>",
           "Details": "<detailed description of the specific code behavior of the permission check>",
           "Relevant Code Snippet": "<code enforcing permission checks>",
           "Detailed Code Snippet": "<code enforcing permission checks>"
        }}],
        "Cause Analysis": {{
            "Missing Permissions": "<list the specific missing permissions and describe the details of the missing permissions>",
            "Code Snippet of Missing Permissions": "<The missing permission check code compared to other access control models where the fields are **not None**>",
            "Cause": "<explain in detail why it leads to potential vulnerabilities>"
        }}
    }}
]
```

### Example Analysis

***Input***
[
    {{
        "resource": "SysRole",
        "operation_type": "edit",
        "access_control_model": [
            {{
                "location": "SysUserServiceImpl.java:updateUser",
                "Operation Description": "Updating user information.",
                "Relevant code snippet": "return userMapper.updateUser(user);",
                "Permission Requirements": [{{
                    "Description": "Requires permission to update user information and validate user permissions.",
                    "Relevant Code Snippet": "checkUserAllowed(user.getUserId());"
                }}]
            }},
            {{
                "location": "SysUserServiceImpl.java:resetUserPwd",
                "Operation Description": "Updating user information, specifically the user's password and other related details.",
                "Relevant code snippet": "public int updateUserInfo(SysUser user) {{\n        return userMapper.updateUser(user);\n    }}",
                "Permission Requirements": [{{
                    "Description": "Requires permission to edit user accounts and validate user data.",
                    "Relevant Code Snippet": "checkUserAllowed(user); "
                }},
                {{
                    "Description": "Requires permission to validate user data.",
                    "Relevant Code Snippet": "checkUserDataScope(user.getUserId());"

                }}]
            }},
            {{
                "location": "SysUserServiceImpl.java:changeStatus",
                "Operation Description": "Updating user information, including managing user roles and posts by deleting existing associations and re-adding them.",
                "Relevant code snippet": "public int updateUser(SysUser user) {{\n    Long userId = user.getUserId();\n    // 删除用户与角色关联\n    userRoleMapper.deleteUserRoleByUserId(userId);\n    // 新增用户与角色管理\n    insertUserRole(user.getUserId(), user.getRoleIds());\n    // 删除用户与岗位关联\n    userPostMapper.deleteUserPostByUserId(userId);\n    // 新增用户与岗位管理\n    insertUserPost(user);\n    return userMapper.updateUser(user);\n}}",
                "Permission Requirements": [{{
                    "Description": "Requires permission to edit user accounts",
                    "Relevant Code Snippet": "checkUserAllowed(user); "
                }},
                {{
                    "Description": "Requires permission to validate user data scope",
                    "Relevant Code Snippet": "checkUserDataScope(user.getUserId());"}},
                {{
                    "Description": "Requires permission to validate role and post data scope",
                    "Relevant Code Snippet": "roleService.checkRoleDataScope(user.getRoleIds()); postService.checkPostDataScope(user.getPostIds());"}}
                ]
            }}

        }}]
    ]

    ***Expected Output:***
    [
        {{
            "resource": "SysRole",
            "location": "SysUserServiceImpl.java:updateUser", 
            "operation_type": "edit",
            "Operation Description": "Updating user information.",
            "Relevant code snippet": "return userMapper.updateUser(user);",
            "Permission Requirements": [{{
                    "Description": "Requires permission to update user information and validate user permissions.",
                    "Relevant Code Snippet": "checkUserAllowed(user.getUserId());"
                }}],
            "Cause Analysis": 
            {{
                "Missing Permissions": "The access control model lacks checkUserDataScope validation which is required to verify the user has appropriate data scope permissions before allowing updates",
                "Code Snippet of Missing Permissions": "checkUserDataScope(user.getUserId());",
                "Cause": "Missing checkUserDataScope validation leads to unauthenticated access to user data"
            }}
        }}

    ]

**Access Control Models**:
'''
{access_control_models}
'''
"""

    def detect_access_control_vulnerabilities(self, resource, code_snippet, call_chain_code, access_control_models):
        return f"""
    Please analyze the following code snippet to check whether there are authentication-related vulnerabilities in operations involving the resource {resource}. Pay special attention to the following aspects:

1. Based on the provided access control model, check whether the required permissions for these operations are correctly enforced in the code.  
2. Identify any operations that lack proper authentication, potentially leading to unauthorized access or actions.  
3. If no authentication-related vulnerabilities are detected, return `"{{None}}"`.  
4. If any authentication-related vulnerabilities are found,The output format must be **valid JSON**, following this structure: 

'''json
[
    {{
        "Resource": "<resource name>",
        "Operation Type": "<operation type>",
        "Operation Description": "<detailed operation description>",
        "Relevant code snippet": "<code snippet>",
        "Permission Requirements": {{
            "Description": "<specific access control requirements>",
            "Relevant Code Snippet": "<permission enforcement code>"
        }},
        "Vulnerability": "<potential authentication vulnerability cause>",
        "Fix Recommendation": "<fix recommendation>"
    }}
]
'''

**Code Snippet**:  
'''
{code_snippet}
''' 

**Relevant Context**:
'''
{call_chain_code}
'''

**Access Control Model**:  
'''
{access_control_models}
'''

"""

    def has_equivalent_operation_prompt(self, model, missing_permission_requirements):

        acm_operation_description = model["Operation Description"]
        acm_relevant_code_snippet = model["Relevant Code Snippet"]

        # acm_permission_requirements = model["Permission Requirements"]
        #
        # acm_permission_requirements = copy.deepcopy(acm_permission_requirements)
        #
        # for item in acm_permission_requirements:
        #     item.pop("Description", None)
        #     item.pop("Details", None)

                                             
        operation_missing_permission_requirements = copy.deepcopy(missing_permission_requirements)
        pr_missing_permission_requirements = copy.deepcopy(missing_permission_requirements)

        for item in operation_missing_permission_requirements:
            item.pop("Operation Description", None)
            item.pop("Permission Requirements", None)
                                            
            if "Relevant Code Snippet" in item:
                item["Operation Relevant Code Snippet"] = item.pop("Relevant Code Snippet")

        for item in pr_missing_permission_requirements:
            item.pop("Operation Description", None)
            item.pop("Relevant Code Snippet", None)
            permission = item.get("Permission Requirements")
            if permission:
                permission.pop("Description", None)                     
                permission.pop("Details", None)                 

        # print("*" * 100)
        # print(operation_missing_permission_requirements)
        # print("*" * 100)

        return f"""
                ###Input Description
                You will now receive an access control model containing the following fields:
                    - "Operation Relevant Code Snippet"：The code snippet relevant to the operation.
                Additionally, a "missing permission" item will be provided, including:
                    - "Operation Relevant Code Snippet"：The code snippet relevant to the operation corresponding to the missing permission.

                ###Task Description
                Your task is to complete the following judgment:
                **Operation Equivalence Judgment**
                 Determine whether the operation in the access control model (based on the "Operation Relevant Code Snippet") is equivalent to the operation corresponding to a missing permission item (also based on the "Operation Relevant Code Snippet").
                     - If the operations are functionally the same or very similar, please fill in "yes" in the "is_operation_equivalent" field in the output; otherwise, fill in "no".
                     - In the "reason_for_is_operation_equivalent" field, provide the rationale for your judgment.

                ### Judgment Criteria (Please base your reasoning on these criteria)

                - Whether the operation descriptions express the same or similar intent (e.g., "read user data" and "access user information").

                ###Output Format
                The output must be in valid JSON format, as shown below:
                ```json
                {{
                  "is_operation_equivalent": "<yes or no>"
                  "reason_for_is_operation_equivalent": "<reason for is_operation_equivalent>"
                }}
                ```

                **Current Access Control Model Operation:**
                ```
                {{
                "Operation Relevant Code Snippet":\n {acm_relevant_code_snippet},
                }}
                ```

                **Operation in Missing Permission:**
                {{
                    {operation_missing_permission_requirements}
                }}

                """

    def has_permission_in_call_chain_prompt(self, model, missing_permission_requirements, call_chain_code):
        acm_operation_description = model["Operation Description"]
        acm_relevant_code_snippet = model["Relevant Code Snippet"]
        acm_permission_requirements = model["Permission Requirements"]

        acm_permission_requirements = copy.deepcopy(acm_permission_requirements)

        for item in acm_permission_requirements:
            item.pop("Description", None)
            item.pop("Details", None)

                                             
        operation_missing_permission_requirements = copy.deepcopy(missing_permission_requirements)
        pr_missing_permission_requirements = copy.deepcopy(missing_permission_requirements)

        for item in operation_missing_permission_requirements:
            item.pop("Operation Description", None)
            item.pop("Permission Requirements", None)
                                            
            if "Relevant Code Snippet" in item:
                item["Operation Relevant Code Snippet"] = item.pop("Relevant Code Snippet")

        for item in pr_missing_permission_requirements:
            item.pop("Operation Description", None)
            item.pop("Relevant Code Snippet", None)
            permission = item.get("Permission Requirements")
            if permission:
                permission.pop("Description", None)                     
                permission.pop("Details", None)                 

        return f"""
        ###Input Description
        You will receive the following two parts of information:
        **Call Chain Context**: This represents a sequence of function calls, where each function may involve resource access or permission-related operations.
        **Permission Set**: A collection of permission items, each describing an action and the resource it involves.
        ###Task Description
        Your task is to:
        Check each permission in the permission set to determine whether it is used or reflected in the call chain context.
        If a permission is used or reflected in the call chain context or it's an irrelevant permission, output "yes" and explain the specific reason (e.g., "In function X, there is an operation Y, which is constrained by permission Z"). Otherwise, output "no".
       
        ###Important
        1.	Semantic Equivalence (Reflected Checks)
        A permission check is considered reflected if its security intent is already enforced elsewhere in the call chain, even if the implementation differs. This includes explicit authorization functions, conditional logic, or implicit guarantees provided by access patterns (e.g., resource IDs derived from the authenticated user). If the same security property (such as role validation, ownership enforcement, or scope restriction) is already ensured, the absence of an explicit check does not introduce a vulnerability.
	    2.	Call-Chain Propagation
        Permission checks performed in a caller function may propagate to callee functions. If a callee is only reachable after a successful authorization check in its caller, and no unguarded invocation paths exist, then the callee does not need to repeat the same check.        
        3. Irrelevant Permission (Refined Definition)
        Sometimes, a permission check present in the permission set may appear unrelated to the current function if one only compares the operation type or the resource type. However, determining whether a permission is truly irrelevant requires careful analysis of the semantic intent of the permission check, not just its surface-level operation or resource association.
        A permission check can be considered irrelevant only if its enforcement logic has no security impact on the current function, even when absent from the call chain.
        In particular:
            •	A permission check is irrelevant if it enforces an operation-specific constraint (e.g., delete, remove, update) on a different resource, and its logic does not express a general security invariant that applies across resources or operations.
            •	A permission check is not irrelevant (i.e., still required), even when the resource or operation differs, if the check enforces a general ownership, identity, or access-scope constraint, such as:
                •	Verifying that the current logged-in user ID matches the owner ID of the target resource.
                •	Ensuring the operation is restricted to the same tenant, project, organization, or user scope.
                •	Enforcing access boundaries that are independent of the specific resource type or operation semantics.
        
        Only permission checks whose logic neither constrains identity, ownership, scope, nor affects the authorization outcome of the current function should be treated as irrelevant permissions.
        
        ###Additional
        We consider that every operation on a resource must fall into **exactly one** of the following four categories:
        {operation_desc}
        
        ###Output Format
        The output must be in valid JSON format, as shown below:
        ```json
        [
            {{
              "has_equivalent_permission_in_call_chain": "<yes or no>",
              "is_irrelevant_permission":"<yes or no>",
              "reason": "<reason for has_equivalent_permission_in_call_chain_or_irrelevant_permission>"
            }}
        ]
        ```
        
        ###Here are the call chain context and permission set
         **Call Chain Context:**
        ```
        {call_chain_code}
        ```

        **Permission Set:**
        ```
        {pr_missing_permission_requirements}
        ```

        """

    def has_equivalent_permission_prompt(self, model, missing_permission_requirements):
        acm_operation_description = model["Operation Description"]
        acm_relevant_code_snippet = model["Relevant Code Snippet"]
        acm_permission_requirements = model["Permission Requirements"]

        acm_permission_requirements = copy.deepcopy(acm_permission_requirements)

        for item in acm_permission_requirements:
            item.pop("Description", None)
            item.pop("Details", None)

                                             
        operation_missing_permission_requirements = copy.deepcopy(missing_permission_requirements)
        pr_missing_permission_requirements = copy.deepcopy(missing_permission_requirements)

        for item in operation_missing_permission_requirements:
            item.pop("Operation Description", None)
            item.pop("Permission Requirements", None)
                                            
            if "Relevant Code Snippet" in item:
                item["Operation Relevant Code Snippet"] = item.pop("Relevant Code Snippet")

        for item in pr_missing_permission_requirements:
            item.pop("Operation Description", None)
            item.pop("Relevant Code Snippet", None)
            permission = item.get("Permission Requirements")
            if permission:
                permission.pop("Description", None)                     
                permission.pop("Details", None)                 

        return f"""
                ###Input Description
                You will now receive an access control model containing the following fields:
                    - "Permission Requirements"：The permissions currently defined in this model, including the fields "Relevant Code Snippet" and "Detailed Code Snippet". These two fields describe the code snippets related to the permissions in the access control model and the detailed code snippets for the permission requirements, respectively.
                Additionally, a "missing permission" item will be provided, which includes:
                    - "Permission Requirements"：The permissions defined in the missing permission item, including the fields "Relevant Code Snippet" and "Detailed Code Snippet". These two fields describe the code snippets related to the missing permissions and the detailed code snippets for the permission requirements, respectively.

                ###Task Description
                Your task is to complete the following judgment:
                **Equivalent Permission Judgment**
                Determine whether the permissions in the current access control model (based on Relevant Code Snippet and Detailed Code Snippet) are functionally equivalent to any of the permissions in the "missing permission" (based on Relevant Code Snippet and Detailed Code Snippet).
                     - If there is a functionally equivalent permission item, fill in "yes" in the "has_equivalent_permission" field in the output.
                     - If there is no such equivalent permission, fill in "no".
                     - In the "reason_for_has_equivalent_permission" field, provide the rationale for your judgment.

                ### Judgment Criteria (Please base your reasoning on these criteria)
                #### For "Permission Equivalence Judgment":
                - Whether the permission names or semantics are highly similar or related;
                - Whether the functions described by the permissions can achieve the operations required by the missing permission;
                - Whether there is an inclusion relationship (e.g., the current permission includes a subset or superset of the functions required by the missing permission).

                ###Output Format
                The output must be in valid JSON format, as shown below:
                ```json
                {{
                  "has_equivalent_permission": "<yes or no>",
                  “reason_for_has_equivalent_permission”: "<reason for has_equivalent_permission>",
                }}
                ```

                **Permission Requirements in the Current Access Control Model**:
                {{
                    "Permission Requirements": \n {acm_permission_requirements}
                }}

                **Permission Requirements in the Missing Permission**：
                ```
                {pr_missing_permission_requirements}
                ```

                """

    def cls_vul_type_prompt(self,access_control_model):
        return f"""
        You are an expert in software security and access control vulnerability analysis, with deep knowledge of permission and authorization mechanisms in Java Web applications.
        
        ###Task Description

        You will be given a permission-related vulnerability from a Java Web system.
        Your task is to classify the vulnerability into exactly one category.
        
        We define **three and only three** types of permission vulnerabilities:
            1.	**Authentication**
        The system fails to properly verify the user’s identity, allowing unauthenticated access to protected functionality.
            2.	**Horizontal Privilege Escalation**
        An authenticated user is able to access or manipulate resources belonging to other users at the same privilege level (e.g., accessing another user’s order or data).
            3.	**Vertical Privilege Escalation**
        An authenticated user is able to perform operations beyond their assigned role or privilege level (e.g., a normal user performing administrator-only actions).
        
        ###Input Format (JSON)

        The input is a JSON object with the following fields:
        {{
          "location": "The vulnerability location, including file name and function name",
          "Operation Description": "A description of the operation performed by the vulnerable call chain",
          "Relevant Code Snippet": "The key code snippet implementing the operation",
          "Operation Location": "The function in which the operation occurs",
          "Parameters": "The parameters passed to the operation",
          "Object": "The core object being operated on",
          "Object Description": "A brief description of the object",
          "Permission Requirements": "The permission checks present in the call chain",
          "missing_permission": [
            {{
              "permission_description": "The security property that this permission check is intended to enforce",
              "missing_permission_requirements": "The permission check that is missing in the vulnerable call chain"
            }}
          ]
        }}
        
        ###Output Requirements (Critical)
        •	Output only the vulnerability category
        •	The output must be exactly one of the following (case-sensitive, no extra text):
        Authentication
        Horizontal Privilege Escalation
        Vertical Privilege Escalation
        
        Do not include explanations, reasoning steps, or any additional text
        
        ###Final Constraint

        Your response must contain only the final classification result, not the analysis process.
        
        Here are the vulnerabilities you need to classify:
        {access_control_model}
        """

    def has_equivalent_permission_and_operation_prompt(self, model, missing_permission_requirements):
        acm_operation_description = model["Operation Description"]
        acm_relevant_code_snippet = model["Relevant Code Snippet"]
        acm_permission_requirements = model["Permission Requirements"]

        for item in acm_permission_requirements:
            item.pop("Description", None)
            item.pop("Details", None)

                                             
        operation_missing_permission_requirements = copy.deepcopy(missing_permission_requirements)
        pr_missing_permission_requirements = copy.deepcopy(missing_permission_requirements)

        for item in operation_missing_permission_requirements:
            item.pop("Operation Description", None)
            item.pop("Permission Requirements", None)
                                            
            if "Relevant Code Snippet" in item:
                item["Operation Relevant Code Snippet"] = item.pop("Relevant Code Snippet")

        for item in pr_missing_permission_requirements:
            item.pop("Operation Description", None)
            item.pop("Relevant Code Snippet", None)
            permission = item.get("Permission Requirements")
            if permission:
                permission.pop("Description", None)                     
                permission.pop("Details", None)                 

        # print("8" * 100)
        # print(acm_permission_requirements)
        # print("8" * 100)
        # print("*" * 100)
        # print(missing_permission_requirements)
        # print("*" * 100)

        return f"""
        ###Input Description
         You will be provided with an access control model containing the following two fields:
            - "Operation Relevant Code Snippet"：The code snippet relevant to the operation.
            - "Permission Requirements"：The permissions currently defined in the model, containing the fields "Relevant Code Snippet" and "Detailed Code Snippet." These fields describe the code snippets relevant to the permissions and the detailed code snippets for the permission requirements, respectively.
        Additionally, a "missing permission" item will be provided, including:
            - "Operation Relevant Code Snippet"：The code snippet relevant to the operation corresponding to the missing permission.
            - "Permission Requirements"：The permissions defined in the missing permission item, containing the fields "Relevant Code Snippet" and "Detailed Code Snippet." These fields describe the code snippets relevant to the missing permission and the detailed code snippets for the permission requirements, respectively.

        ###Task Description
        Your task is to complete the following two judgments:
        1. Equivalent Permission Judgment
        Determine whether the permissions in the current access control model (considering both Relevant Code Snippet and Detailed Code Snippet) are functionally equivalent to any of the permissions in the "missing permission" item (also considering both Relevant Code Snippet and Detailed Code Snippet).
             - If there is a functionally equivalent permission, fill in "yes" in the "has_equivalent_permission" field.
             - If not, fill in "no."
             - Provide the rationale in the "reason_for_has_equivalent_permission" field.
        2. Operation Equivalence Judgment
        Determine whether the operation in the access control model (considering the Operation Relevant Code Snippet) is functionally equivalent to the operation corresponding to any item in the "missing permission" (also considering the Operation Relevant Code Snippet).
             - If the operations are functionally the same or very similar, fill in "yes" in the "is_operation_equivalent" field.
             - Otherwise, fill in "no."
             - Provide the rationale in the "reason_for_is_operation_equivalent" field.


        ### Judgment Criteria (Please base your reasoning on these criteria)
        #### For "Equivalent Permission Judgment":
        - Whether the permission names or semantics are highly similar or related;
        - Whether the functions described by the permissions can fulfill the operations required by the missing permission;
        - Whether there is an inclusion relationship (e.g., the current permission includes a subset or superset of the functions required by the missing permission).

        #### For "Operation Equivalence Judgment":
        - Whether the operation descriptions express the same or similar intentions (e.g., "read user data" vs. "access user information");
        - Whether the Operation Relevant Code Snippet in the current access control model has the same functional effect as any Operation Relevant Code Snippet in the missing permission. If it matches one of them, it is considered equivalent.

        ###Output Format
        The output must be in valid JSON format, as shown below:
        ```json
        {{
          "has_equivalent_permission": "<yes or no>",
          “reason_for_has_equivalent_permission”: "<reason for has_equivalent_permission>",
          "is_operation_equivalent": "<yes or no>"
          "reason_for_is_operation_equivalent": "<reason for is_operation_equivalent>"
        }}
        ```

        **Current Access Control Model Operation**:
        ```
        {{
        "Operation Relevant Code Snippet":\n {acm_relevant_code_snippet},
        "Permission Requirements": \n {acm_permission_requirements},
        }}
        ```
        **Operation in the Missing Permission**：
        {{
            {operation_missing_permission_requirements}
        }}

        **Permission Requirements in the Current Access Control Model**:
        {{
            "Permission Requirements": \n {acm_permission_requirements}
        }}

        **Permission Requirements in the Missing Permission**：
        ```
        {pr_missing_permission_requirements}
        ```

        """

    def detect_access_control_vulnerabilities_test(self, resource, code_snippet, call_chain_code, diff_model):
        return f"""


### Task Description
Analyze the provided code snippet and its context to determine whether the identified authentication-related vulnerability is a false positive in operation {diff_model["Relevant Code Snippet"]} involving the resource {resource}.

### Analysis Requirements
1. Carefully examine the code snippet and relevant context to:
   - Understand authentication mechanisms
   - Identify any permission checks related to the operation {diff_model["Relevant Code Snippet"]}
   - If the context reveals the presence of the permission check that the bug report claims is missing, classify the issue as a false positive.

2. Your analysis should:
   - Consider both explicit and implicit permission checks of the operation {diff_model["Relevant Code Snippet"]}
   - Evaluate whether existing permission checks are adequate
   - If you determine the issue is a false positive, output the source code of the missing permission check referenced in the bug report.

3. Conclude with a clear YES/NO determination:
   - YES: It is a false positive, there are adequate permission checks in the code
   - NO: It is a true positive, there are missing permission checks in the code
   - NOT SURE: If you are not sure whether there are exploitable vulnerabilities

### Output Format:
### Explanation:(A detailed analysis of the authentication mechanisms and permission checks found in the code snippet. Include reasoning on whether the checks are sufficient and align with the bug report's claim.)

### Relevant Permission Check Code: (Code snippet showing the relevant permission checks of the operation {diff_model["Relevant Code Snippet"]}, if present. If no permission check exists, state "None found.")

### Conclusion: (One of: YES / NO / NOT SURE, along with a brief justification.)




**Code Snippet**:  
'''
{code_snippet}
''' 

**Relevant Context**:
'''
{call_chain_code}
'''

**Bug Report**:
'''
{diff_model["Cause Analysis"]}
'''

"""

    def test_extract_permission_requirements_prompt(self, resource, func_name, code_snippet, call_chains,
                                                    call_chain_code, operation_list):
        return f"""
    ### Task Description: 
    Analyze the following code snippet and its contextual function calls to determine the required permissions for each operation listed in the provided operation list when accessing or modifying the resource `{resource}`.

    ### Instructions:

    1. **Understanding the Operation List:**  
       Each operation entry contains the following fields:  
       - **Operation Type**: One of the four categories — `read`, `create`, `remove`, or `edit`.  
       - **Operation Description**: A detailed explanation of the operation beyond its type.  
       - **Relevant Code Snippet**: The specific code segment within the function `{func_name}` where the operation is executed.  

    2. **Permission Requirement Analysis:**  
       - For each operation in the list, analyze the required permission conditions based on its **operation type, description, and relevant code snippet**.  
       - Consider the **context** of the code snippet to determine any implicit or explicit permission checks.  

    3. **Permission Extraction Criteria:**  
       The extracted permission requirements must be **clear, concise, and specific**. Each permission requirement must include:  
       - **Description**: A short, explicit statement describing the necessary access control conditions before performing the operation.  
       - **Relevant Code Snippet**: The specific lines of code that enforce the permission check.  

    4. **Note:**
       Note that here you need to focus on the permission checks that are done before the operation on the {resource}.
       Don't repeat the code snippet in the operation list, but extract the code related to permission checks.

    5. **Important:**
       All extracted relevant code snippets must be sourced from the provided code snippet. If there is no relevant code for the permission requirements, return {None} in the relevant code snippet field.

    6. **Output Format:**  
       The final output should **extend the original operation list** by appending the extracted permission requirements.  
       For the same operation, it is possible to check its permissions in multiple places in the code, so there can be multiple permission requirements for an operation list.
       The output format must be **valid JSON**, following this structure:  

       ```json
       [
           {{
        "Operation Type": "<operation type>",
               "Operation Description": "<detailed operation description>",
               "Relevant Code Snippet": "<code snippet>",
               "Permission Requirements": [{{
                    "Description": "<clear and specific access control requirement>",
                   "Relevant Code Snippet": "<code enforcing permission checks>"}}]
           }}
       ]```


    ### Example:

    ***Input (Operation list):***
    [
        {{
            "Operation Type": "create",
            "Operation Description": "Inserting a new user into the system after validation.",
            "Relevant Code Snippet": "userMapper.insertUser(user);"
        }}
    ]

    ***Expected Output:***

    [
        {{
            "Operation Type": "edit",
            "Operation Description": "Updating existing user information after validation.",
            "Relevant Code Snippet": "userMapper.updateUser(user);",
            "Permission Requirements": {{
                "Description": "Requires permission to update user accounts, validate department data, and check user permissions.",
                "Relevant Code Snippet": "checkUserAllowed(u); checkUserDataScope(u.getUserId()); deptService.checkDeptDataScope(user.getDeptId());"
            }}
        }}
    ]

    Here is the code snippet of function {func_name}:
         '''
         {code_snippet}
         '''

        Here are function call relationships:
         '''
         {call_chain_code}
         '''

         Here is the operation list:
         '''
        {operation_list}
         ''' """

    def extract_default_role(self, func_name, code_snippet, call_chains, call_chain_code):
        """
        分析创建用户时的默认角色和权限
        """
        call_chain_down = call_chains[0]
        call_chain_up = call_chains[1]
        call_chain_code_down = call_chain_code[0]
        call_chain_code_up = call_chain_code[1]

        return f"""
### Task Description:
分析以下创建用户的代码片段及其调用链，识别新创建用户被分配的默认角色，以及该默认角色所具有的权限。

### Analysis Requirements:
1. **识别默认角色**：
   - 在代码中查找新用户创建时被分配的默认角色（可能是角色ID、角色名称等）
   - 注意：默认角色可能在以下位置：
     a) 创建用户函数中直接硬编码
     b) 调用链中的其他函数中设置
     c) 通过配置或常量定义

2. **识别默认角色的权限**：
   - 如果代码中直接关联了权限信息，提取这些权限
   - 如果代码中只设置了角色，需要说明该角色对应的权限需要进一步查询角色-权限关联表

3. **代码位置**：
   - 明确指出设置默认角色的具体代码位置
   - 明确指出权限相关的代码位置（如果存在）
### Example:
String defaultRole = ParamResolver.getStr("USER_DEFAULT_ROLE");
这个代码片段可以推测出来，角色名称式USER_DEFAULT_ROLE或者DEFAULT_ROLE，所以这里的输出结果中role_name是USER_DEFAULT_ROLE，role_id需要进一步查询角色表获取。
### Output Format:
输出必须是有效的JSON格式：
```json
{{
    "default_role": {{
        "role_id": "<角色ID，如果代码中有, 如果没有填none>",
        "role_name": "<角色名称，如果代码中有, 如果没有填none>",
        "location": "<设置默认角色的代码位置，格式：文件名:函数名:行号>",
        "code_snippet": "<设置默认角色的具体代码片段>",
        "description": "<描述如何设置默认角色>"
    }},
    "analysis_note": "<如果无法从代码中直接获取权限信息，说明需要查询角色-权限关联表>",
    "success": "yes"
}}
```

如果无法识别默认角色，返回：
```json
{{
    "default_role": null,
    "default_permissions": [],
    "analysis_note": "<无法识别的原因>",
    "success": "no"
}}
```

### Code Context:

**创建用户的函数代码 ({func_name}):**
```
{code_snippet}
```

**被调用的函数列表:**
```
{call_chain_down if len(call_chain_down) > 0 else "该函数没有调用其他函数"}
```

**调用该函数的函数列表:**
```
{call_chain_up if len(call_chain_up) > 0 else "该函数没有被其他函数调用"}
```

**被调用函数的代码片段:**
```
{call_chain_code_down if len(call_chain_code_down) > 0 else "无"}
```

**调用者函数的代码片段:**
```
{call_chain_code_up if len(call_chain_code_up) > 0 else "无"}
```
"""

    def find_role(self, role, role_list):
        """
        # 输入：角色相关信息，角色权限相关信息
        # 输出：判断是否属于同一个角色
        """
        return f"""
### Task Description:
我将给出来你一个角色名称，以及一个角色名称列表。请你判断这个角色名称是否在这个角色名称列表中，
如果是的话，找出来在这个角色列表中最符合这个角色名称的列表序号，从0开始。
比如user和普通用户是等价的词汇，管理员和admin等是等价的词汇，USER_DEFAULT_ROLE和普通用户是等价词汇。你注意一定要从语义上理解
### Example:
input:
role: {{'role_id': '<角色ID需要进一步查询>', 'role_name': 'USER_DEFAULT_ROLE'}}
role_list: [{{'role_id': '2', 'role_name': "'普通用户'"}}, {{'role_id': '1', 'role_name': "'管理员'"}}]
output:
0
原因，因为USER_DEFAULT_ROLE和普通用户可以认为是同一类关系，都是默认角色。
### Input:
角色字段1：{role}
角色列表：{role_list}
### Output:
你只需要回答找到的最匹配的角色列表下标，编号从0开始，如果不存在返回-1，不需要任何其他输出
"""

    def extract_create_sql(self, sql_contents):
        """
        # 构建 数据库表视图
        # 输入：角色，角色权限，权限表等建表语句
        # 输出：建表语句中我需要的信息，包括表名，主键id字段名，名称字段名，角色id字段名，权限id字段名
        """
        return """
### Task Description:
    提取以下SQL语句中的创建角色和权限的SQL语句，
    请你从输入的信息（会包括角色相关信息、角色权限相关信息、权限表的建表语句）多条sql中，提取并确定三个数据库表的具体字段名。
### 具体要求如下：
    1. 在给出的sql中识别出角色相关信息、角色权限相关信息、权限表的建表语句
    2. 如果以上三张表有一张表的建表语句不存在，那么输出相关的表名，主键id字段名，名称字段名，角色id字段名，权限id字段名都为空。
    2. 对于识别出的建表语句，提取角色表的（表名，主键id字段名，名称字段名）,角色权限表的（表名，角色id字段名，权限id字段名）,权限表的（表名，主键id字段名，名称字段名）,
其中角色表的主键id字段名要能和角色权限表的角色id字段名匹配，权限表的主键id字段名要能和角色权限表的权限id字段名匹配。
例如：角色表的主键id字段名是id，角色权限表的角色id字段名是role_id，权限表的主键id字段名是id，角色权限表的权限id字段名是permission_id，
那么角色表的主键id字段名和角色权限表的角色id字段名匹配，权限表的主键id字段名和角色权限表的权限id字段名匹配。
    3. 输出格式必须为有效的json格式：
    ```json
    {{
        "role_table": {{
            "table_name": "<角色表名>",
            "id_field_name": "<角色表主键id字段名>",
            "name_field_name": "<角色表中用于显示的名称字段名>"
        }},
        "role_permission_table": {{
            "table_name": "<角色权限表名>",
            "role_id_field_name": "<角色权限表角色id字段名>",
            "permission_id_field_name": "<角色权限表权限id字段名>"
        }},
        "permission_table": {{
            "table_name": "<权限表名>",
            "id_field_name": "<权限表主键id字段名>",
            "name_field_name": "<权限表中用于显示的名称字段名>"
        }},
        "analysis_note": "<如果无法从输入的信息中提取出具体的字段名，说明需要进一步分析>",
        "success": <True or False>
    }}
    ```
    4. 请根据实际输入的信息，准确提取三个表的字段名并按上述格式返回结果。

    ### 输入信息：
    {}
""".format(sql_contents)

    def extract_create_permission_sql(self, sql_contents, permission_table_name):
        """
        # 获取数据库表权限表的资源字段
        # 输入：权限表等建表语句
        # 输出：建表语句中我需要的信息，包括资源表资源字段名称
        """
        return """
### Task Description:
    提取以下SQL语句中的权限的SQL语句，
    请你从输入的信息（主要包括权限表的建表语句）多条sql中，提取出其中创建权限的建表语句，并且从这个建表语句中找出一个字段能代表这一条权限的操作资源的字段名称
### 具体要求如下：
    1. 在给出的sql中识别出权限表的建表语句, 并且已知权限表名为 {}
    2. 如果无法找到权限表的建表语句，那么在返回的analysis_note中表明无法找到相关建表语句，并且resource_coloum字段设置为none
    3. 对于识别出的权限表建表语句，找出一个字段能代表这一条权限的操作资源的字段名称
    5. 例如：
    Example1: 我提供的建表语句是 "create table dayu_permission
    (
        permission_id  varchar(32)          not null
            primary key,
        action         varchar(255)         null,
        resource       varchar(255)         null,
        sub_service    varchar(255)         null,
        alias          varchar(255)         null,
        is_take_effect tinyint(1) default 1 null comment '权限是否生效',
        alias_en       varchar(255)         null comment '权限英文描述',
        resource_zh    varchar(255)         null comment '资源中文描述'
    )
        row_format = DYNAMIC;" 其中resource字段就可以代表这一条权限的操作资源的字段，你应该返回resource, 
    Example2:DROP TABLE IF EXISTS `sys_menu`;
    CREATE TABLE `sys_menu` (
        `menu_id` bigint NOT NULL COMMENT '菜单ID',
        `name` varchar(32)  DEFAULT NULL COMMENT '菜单名称',
        `en_name` varchar(128)  DEFAULT NULL COMMENT '英文名称',
        `permission` varchar(32)  DEFAULT NULL COMMENT '权限标识',
        `path` varchar(128)  DEFAULT NULL COMMENT '路由路径',
        `parent_id` bigint DEFAULT NULL COMMENT '父菜单ID',
        `icon` varchar(64)  DEFAULT NULL COMMENT '菜单图标',
        `visible` char(1)  DEFAULT '1' COMMENT '是否可见，0隐藏，1显示',
        `sort_order` int DEFAULT '1' COMMENT '排序值，越小越靠前',
        `keep_alive` char(1)  DEFAULT '0' COMMENT '是否缓存，0否，1是',
        `embedded` char(1)  DEFAULT NULL COMMENT '是否内嵌，0否，1是',
        `menu_type` char(1)  DEFAULT '0' COMMENT '菜单类型，0目录，1菜单，2按钮',
        `create_by` varchar(64)  NOT NULL DEFAULT ' ' COMMENT '创建人',
        `create_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
        `update_by` varchar(64)  NOT NULL DEFAULT ' ' COMMENT '修改人',
        `update_time` datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
        `del_flag` char(1)  DEFAULT '0' COMMENT '删除标志，0未删除，1已删除',
        PRIMARY KEY (`menu_id`) USING BTREE
        ) ENGINE=InnoDB  COMMENT='菜单权限表'; 其中path字段就可以代表这一条权限的操作资源的字段，你应该返回 path
    5. 输出格式必须为有效的json格式：
    ```json
    {{
            "resource_coloum": "<代表这一条权限的操作资源的字段名称， 如果无法找到返回none>",
            "analysis_note": "<如果无法从输入的信息中提取出具体的字段名，说明需要进一步分析>"
        
    }}
    ```
    4. 请根据实际输入的信息，准确提取字段名并按上述格式返回结果。

    ### 输入信息：
    {}
""".format(permission_table_name, sql_contents)

    def analyze_default_permission(self, role_id, role_name, default_permission):
        """
        # 分析默认角色的权限是否过大
        # 输入：默认角色的权限
        # 输出：是否过大的分析结果
        """
        return f"""
### Task Description:
    我将给你一个某个web系统中创建新用户时，该用户具有的初始角色和初始权限信息，你需要
    以一个优秀的产品经理的角度分析这个初始角色是否可能过大，初始权限是否可能过大，如果有一个过大就在is_too_large标记为true，并且在analysis_note分析原因, 否则标记为false，并且在analysis_note分析原因
### 具体要求如下：
    1. 分析默认角色的权限是否过大
    2. 如果默认角色的权限过大，那么在返回的analysis_note中表明默认角色的权限过大
    3. 如果默认角色的权限正常，那么在返回的analysis_note中表明默认角色的权限正常
    4. 输出格式必须为有效的json格式：
    ```json
    {{
            "is_too_large": "<是否过大，true or false>",
            "analysis_note": "<分析结果>"
        
    }}
    ```
    4. 请根据实际输入的信息，准确分析默认角色的权限是否过大并按上述格式返回结果。
    输入：
    角色信息：role_name={role_name}, role_id={role_id}
    默认权限：{default_permission}
    """

