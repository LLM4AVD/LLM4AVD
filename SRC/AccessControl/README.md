## Method Overview

- **Access Control Model Extraction**: Based on the operations on project resources in the code, attempt to extract the permission checks related to these operations in order to build the corresponding access control model.
- **Vulnerability Detection**: Based on the idea of consistency checking, compare the permission checks in each access control model with the permission checks in all access control models for performing the same operations on the same resources within the project, identify the currently missing permission checks, and further verify in the original code whether functionally equivalent checks are missing.

### 1) Access Control Model Extraction

#### Command

```
python extract_access_control_model.py \
  --model_name Qwen3-32B \
  --resources_path project_resources.json \
  --call_chains_path project_call_chains.json \
  --output_path project_acm.json \
  --resource_list resource1 resource2 resource3

```

#### Parameters

- `--resources_path` (from `data/resource/`): File for storing all resources within the scanned project
- `--call_chains_path` (from `data/call_chain/`): File for storing the context call chain of each dangerous function
- `--model_name`: LLM for extraction
- `--output_path` (to `output/`): File for storing the extracted access control models
- `--resource_list`: Name of the scanned resource

#### **Output file format** (`output/<your_file>.json`)

Each operation on a resource corresponds to an access control model:

```
{
     "Operation Type": "<operation type>",
     "Operation Description": "<detailed operation description>",
     "Relevant Code Snippet": "<code snippet>",
     "Object": "<object of the operation>",
     "Object Description": "<detailed description of the object>",
     "Permission Requirements": [
          {
          "Description": "<clear and specific access control requirement>",
          "Details": "<detailed description of the specific code behavior of the permission check>",
          "Relevant Code Snippet": "<code enforcing permission checks>",
          "Detailed Code Snippet": "<expanded code showing the implementation of the permission check function or API>"
         }
      ]
}
```

### 2) Vulnerability Detection

#### Command

```
python vul_detection.py \
  --model_name Qwen3-32B \
  --access_model_path project_acm.json \
  --processed_access_control_model_path project_processed_models.json \
  --complete_access_model_path project_complete_models.json \
  --output_access_control_model_path project_diff_models.json \
  --call_chains_path project_call_chains.json \
  --after_reducing_false_positives_path project_final_result.json \
  --false_positives_path project_false_positives.json \
  --resource_list resource1 resource2 resource3

```

#### Parameters

- `--call_chains_path` (from `data/call_chain/`): File for storing the context call chain of each dangerous function
- `--model_name`: LLM for extraction
- `--access_model_path` (from `output/`): The file storing the access control model output during the extraction phase of the access control model
- `--processed_access_control_model_path` (to `output/`): Classify access control models based on performing the same operation on the same resource.
- `--complete_access_model_path` (to `output/`): Extract all permission checks from the same type of access control model and remove duplicates
- `--output_access_control_model_path` (to `output/`): Check which permission checks are missing in each access control model compared to all permission checks of the same type and output preliminary results.
- `--after_reducing_false_positives_path` (to `output/`): Final detection output after false positive elimination of preliminary results
- `--false_positives_path` (to `output/`): False positives eliminated in the preliminary results
- `--resource_list`: Name of the scanned resource

#### **Output file format** (`output/<your_file>.json`)

Each access control model that is missing a permission check will be listed, and it will be assessed from multiple dimensions whether the original code truly lacks the check:

```
{
     "Operation Type": "<operation type>",
     "Operation Description": "<detailed operation description>",
     "Relevant Code Snippet": "<code snippet>",
     "Object": "<object of the operation>",
     "Object Description": "<detailed description of the object>",
     "Permission Requirements": [
          {
          "Description": "<clear and specific access control requirement>",
          "Details": "<detailed description of the specific code behavior of the permission check>",
          "Relevant Code Snippet": "<code enforcing permission checks>",
          "Detailed Code Snippet": "<expanded code showing the implementation of the permission check function or API>"
         }
      ],
     "missing_permission":[
         {
          "permission_description":<Accurately describe the purpose and logic of this type of permission check in one sentence.>
          "missing_permission_requirements":[<Access control models with the required missing permissions>]
          "result":
              {
                "has_equivalent_permission": "<yes or no>",
                "reason_for_has_equivalent_permission”: "<reason for has_equivalent_permission>",
                "is_operation_equivalent": "<yes or no>",
                "reason_for_is_operation_equivalent": "<reason for is_operation_equivalent>",
                "permission_in_call_code":
                      [
                          {
                            "has_equivalent_permission_in_call_chain": "<yes or no>",
                            "is_irrelevant_permission":"<yes or no>",
                            "reason": "<reason for has_equivalent_permission_in_call_chain_or_irrelevant_permission>"
                          }
                      ]
              }
         }

     ]
}
```
