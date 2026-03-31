## Directory Structure

```
/
├── README.md
├── requirements.txt
├── data/
│   ├── train/                  # training set for knowledge extraction
│   └── test/                   # test set for detection & evaluation
├── output/
│   ├── detect/                 # detection runs (each run -> one JSON)
│   │   └── metrics/            # evaluation reports
│   └── knowledge/              # extracted knowledge JSONs
├── src/
│   ├── data_collection/  
│   │   ├── collect.py
│   │   ├── filter.py
│   ├── extract_knowledge.py
│   ├── vulnerability_detect.py
│   └── evaluate_result.py
└── utils/
    ├── bm25_retriever.py
    └── llm_client.py
```

## Environment

- Python **3.12**

- Install deps:

  ```
  pip install -r requirements.txt
  ```

- Install spaCy model:

  ```
  python -m spacy download en_core_web_sm
  ```

- Put your LLM credentials in `utils/llm_client.py` (`api_key`, `base_url`).

## Dataset Construction

We build the dataset in **two steps**:

1. **Collect** CVEs for a target CWE from **NVD**, crawl **GitHub commit** links in CVE references, and fetch each commit’s **before/after** code and **patch hunks**.
2. **Filter & normalize** each changed file into a single **case** (the format used by both training and testing).

### 1）Data Collection (NVD + GitHub commits)

#### Command

```
python src/dataset/collect.py 
```

This step automatically downloads CVE data for a given **CWE** category from the NVD API and extracts linked **GitHub commits** that contain vulnerability fixes.
For each commit, the script fetches:

- The **before/after** source files (`code_before_change`, `code_after_change`)
- The **diff patch** (`patches`)
- Metadata including CVE ID, CWE type, and reference URL

### 2) Data Filtering

- **File-level**: keep only source files (`.c`, `.cpp`, `.java`, `.py`, …)
- **Test files**: exclude `/test/`, `*.spec.*`, `unittest/`, etc.
- **Line-level**: drop comments, blanks, `import/include/using` only diffs
- **Single-file commit**: split a multi-file commit so **each file diff is one case**

#### Command

```
python src/dataset/filter.py <input.json> <output.json>
```

#### **Output file format** (data/<your_file>.json)

> **dataset form(used by both train/test):**

```
{
  "cve_id": "CVE-XXXX-YYYY",
  "cwe": ["CWE-285"],
  "cve_description": "Human-readable CVE summary...",
  "file": "path/inside/repo/Foo.java",
  "code_before_change": "…original snippet…",
  "code_after_change": "…patched snippet…",
  "function_modified_lines": { "added": ["…"], "deleted": ["…"] },
  "id": "CWE_285_PROJECT_filter_00001"
}
```

- Put **training** cases in `data/train/` (used to build the knowledge base)
- Put **test** cases in `data/test/` (used to evaluate detection)

## Method Overview

```
train/*.json --(LLM)--> knowledge/*.json
                 │
test/*.json  --(BM25 + LLM re-rank over knowledge)--> detect/*.json --(evaluation)--> detect/metrics/*
```

- **Knowledge Extraction**: normalize prior patches into structured vulnerability knowledge
- **Retrieval**: BM25 over `purpose/function/code` → LLM re-rank → top-K knowledge
- **Detection**: LLM judges (a) similar vulnerability behavior? (b) similar fix already present?
- **Evaluation**: Aggregate all detection results and compute classification and pairwise metrics, including
  **Precision, Recall, F1-score, Accuracy, False-Positive/False-Negative Rates**, and detailed pairwise match statistics.

### 1) Knowledge Extraction

#### Command

```
python src/extract_knowledge.py \
  --input_file_name linux_kernel_CWE-401_data.json \
  --output_file_name linux_kernel_CWE-401_knowledge.json \
  --model_name gpt-4o-mini \
  --thread_pool_size 10 \
  --resume \
  --model_settings temperature=0.01
```

#### Parameters

- `--input_file_name` (from `data/train/`): training set file
- `--output_file_name` (to `output/knowledge/`): extracted knowledge
- `--model_name`: LLM for extraction
- `--thread_pool_size`: parallel workers
- `--resume`: resume if output already exists
- `--model_settings`: pass model kwargs (e.g., `temperature=0.01`)

#### **Output file format** (`output/knowledge/<your_file>.json`)

An array where **each training case** yields **one knowledge item**:

```
{
  "id": "CWE_285_VULRAG_filter_00270",
  "CVE_id": "CVE-2024-9095",

  "GPT_purpose": "Function purpose: one sentence summary…",
  "GPT_function": "The functions of the code snippet are: 1) … 2) …",
  "GPT_analysis": "Why the patch is necessary; reason rooted in added/deleted lines…",

  "vulnerability_behavior": {
    "preconditions_for_vulnerability": "What must be true in the system before the bug can bite…",
    "trigger_condition": "How the vulnerable behavior is triggered…",
    "specific_code_behavior_causing_vulnerability":
      "The concrete code pattern that creates the risk…"
  },

  "solution": "Remediation pattern (e.g., RBAC check on role/permission before action)…",

  "code_before_change": "…(optional for later inspection)…",
  "code_after_change":  "…",
  "modified_lines": { "added": ["…"], "deleted": ["…"] }
}
```

### 2) Retrieval-Augmented Detection

#### Command

```
python src/vulnerability_detect.py \
  --input_file_name linux_kernel_CWE-401_testset.json \
  --output_file_name linux_kernel_CWE-401_result_gpt-4o-mini.json \
  --knowledge_file_name linux_kernel_CWE-401_knowledge.json \
  --model_name gpt-4o-mini \
  --summary_model_name gpt-4o-mini \
  --retrieval_top_k 20 \
  --thread_pool_size 10 \
  --resume \
  --model_settings temperature=0.01 \
  --early_return \
  --max_knowledge 3
```

#### Parameters

- `--input_file_name` (from `data/test/`): test cases to detect
- `--output_file_name` (to `output/detect/`): detection results
- `--knowledge_file_name` (from `output/knowledge/`): knowledge base json
- `--model_name`: LLM for detection
- `--summary_model_name`: LLM to summarize **purpose/function** used in retrieval
- `--retrieval_top_k`: BM25 recall pool size before re-ranking
- `--max_knowledge`: knowledge items finally concatenated into the prompt (e.g., 3–5)
- `--retrieve_by_code` (optional): only use raw code for retrieval (ablation)
- `--early_return`: Return early if a clear solution behavior is found.

#### **Output file format** (`output/detect/<your_file>.json`)

At the **run level**:

```
{

  "id": "CWE_285_VULRAG_filter_00156",
  "detect_result_before": { /* analysis on code_before_change */ },
  "detect_result_after":  { /* analysis on code_after_change  */ },
  
}
```

Where `final_result` is the consolidated verdict:

- `1` = vulnerable,
- `0` = not vulnerable / fixed,
- `-1` = uncertain 

Each of `detect_result_before` / `detect_result_after` has:

```
{
  "code_snippet": "…the exact snippet analyzed…",
  "purpose": "\"One-sentence internal summary used for retrieval\"",
  "function": "1. …  2. …",

  "detect_result": [
    {
      "vul_knowledge": {
        "cve_id": "CVE-2024-9095",
        "id": "CWE_285_VULRAG_filter_00270",
        "vulnerability_behavior": {
          "preconditions_for_vulnerability": "…",
          "trigger_condition": "…",
          "specific_code_behavior_causing_vulnerability": "…"
        },
        "solution_behavior": "Canonical fix pattern (if your extractor includes it)…"
      },

      "vul_detect_prompt":  "…full prompt sent to LLM…",
      "vul_output":         "…LLM reasoning…\n<result> YES </result>",

      "sol_detect_prompt":  "…prompt to check if fix behavior exists…",
      "sol_output":         "…LLM reasoning…\n<result> NO </result>"
    }，
  "final_result": 1
  "detection_model": "gpt-4o-mini",
  "summary_model": "gpt-4o-mini",
  "model_settings": {},
  "id": "CWE_285_VULRAG_filter_00156",
  "cve_id": "CVE-2025-29926"
  ]
}
```

### 3) Evaluation

#### Command

```
python src/evaluate_result.py --input_files $(ls -F output/detect | grep -v '/$')
```

#### Parameters

- `--input_files`: space-separated list of detection JSONs (filenames only)
- `--baseline` (optional): also compute a baseline (e.g., “LLM-only no retrieval”) for comparison

#### **Output files** (`output/detect/metrics/`)

- `linux_kernel_CWE-401_result_gpt-4o-mini_basic_metrics.json`

**Typical JSON fields**:

```
{
    "true_positive": xx,
    "false_positive": xx,
    "false_negative": xx,
    "true_negative": xx,
    "precision": xx,
    "recall": xx,
    "f1": xx,
    "accuracy": xx,
    "FN_rate": xx,
    "FP_rate": xx,
    "TN_rate": xx,
    "TP_rate": xx,
    "pair_total": xx,
    "pair_right": xx,
    "pair_1": xx,
    "pair_0": xx,
    "pair_wrong": xx,
    "pair_accuracy": xx,
    "pair_1_rate": xx,
    "pair_0_rate": xx,
    "false_pair_rate": xx
}
```

## Usage Steps

1. **Prepare Dataset**: Create the data directory and output directory with subdirectories according to the directory structure specified in this README, and place the training dataset and test dataset (in the `/benchmark` folder of project [KnowledgeRAG4LLMVulD](https://github.com/KnowledgeRAG4LLMVulD/KnowledgeRAG4LLMVulD)) in the `data/train/` and `data/test/` directories respectively.
2. **Configure API**: Replace the model's `api_key` and `base_url` in `utils/llm_client.py` with your own API key and base URL.
3. **Extract Knowledge**: Run the `extract_knowledge.py` script to extract knowledge from the training dataset.
4. **Perform Detection**: Run the `vulnerability_detect.py` script to detect vulnerabilities in the test dataset.
5. **Evaluate Results**: Run the `evaluate_result.py` script to calculate evaluation metrics for the detection results.

## Notes

- Ensure that the required spaCy model `en_core_web_sm` for tokenization has been downloaded on your system.
- If you need to interrupt processing and resume later, you can use the `--resume` parameter.