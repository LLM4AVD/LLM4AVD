import json
import requests
import time
import os
import re
import sys
import argparse
import requests
from tqdm import tqdm
from urllib.parse import urlparse

nvd_api_key = ""                         
github_api_token = ""                              

session = requests.Session()
session.headers.update({'Accept': 'application/vnd.github.v3+json'})
if github_api_token:
    session.headers.update({'Authorization': f'token {github_api_token}'})

def fetch_all_cve_for_cwe(cwe_id, api_key):
    """
    分页调用 NVD JSON API，获取指定 CWE 下的所有 CVE ID 列表。
    """
    base_url = "https://services.nvd.nist.gov/rest/json/cves/2.0/"
    # print(f"api_key: {api_key}")
    headers = {}
    if api_key:
        headers["apiKey"] = api_key

    results_per_page = 2000                   
    start_index = 0
    total_results = None
    all_cve = []
    meta_data = {}

    while True:
        params = {
            "cweId": f"CWE-{cwe_id}",
            "resultsPerPage": results_per_page,
            "startIndex": start_index,
        }
        resp = requests.get(base_url, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()

                                     
        if not meta_data:
            meta_data = {k: v for k, v in data.items() if k != "vulnerabilities"}
                                       


        # with open("nvd_response.json", "w", encoding="utf-8") as f:
        #     json.dump(data, f, indent=2, ensure_ascii=False)
                                           
        #
        # break

                    
        if total_results is None:
            total_results = int(data["totalResults"])
            print(f"总共 {total_results} 条，分批拉取中…")


                    
        items = data.get("vulnerabilities", {})
        # print(items)
        all_cve.extend(items)
        print(f"已获取 {len(all_cve)} / {total_results}")

                
        if len(all_cve) >= total_results:
            break

                         
        # time.sleep(6)
        start_index += results_per_page


                                                     
    data = {
        **meta_data,
        "vulnerabilities": all_cve
    }

    return data


def parse_commit_url(url):
    # Expecting https://github.com/{owner}/{repo}/commit/{sha}
    parsed = urlparse(url)
    parts = parsed.path.strip('/').split('/')
    if len(parts) >= 4 and parts[-2] == 'commit':
        owner = parts[-4]
        repo = parts[-3]
        sha = parts[-1]
        return owner, repo, sha
    else:
        raise ValueError(f"Invalid commit URL: {url}")

def fetch_commit_data(owner, repo, sha, token=None):
    api_url = f"https://api.github.com/repos/{owner}/{repo}/commits/{sha}"
    headers = {'Accept': 'application/vnd.github.v3+json'}
    if token:
        headers['Authorization'] = f'token {token}'
    try:
        resp = session.get(api_url)
        # resp = requests.get(api_url, headers=headers)
        resp.raise_for_status()
        return resp.json()
    except requests.HTTPError as e:
        print(f"Error fetching commit data for {owner}/{repo}@{sha}: {e}")
    return {}

def fetch_raw_file(owner, repo, ref, path, token=None):
    raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{path}"
    headers = {}
    if token:
        headers['Authorization'] = f'token {token}'
    resp = session.get(raw_url)
    # resp = requests.get(raw_url, headers=headers)
    if resp.status_code == 404:
        return {}
    resp.raise_for_status()
    return resp.text

def save_to_file(outdir, relpath, content):
    dest = os.path.join(outdir, relpath)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, 'w', encoding='utf-8') as f:
        f.write(content)

def parse_patch(patch_text):
    # returns list of hunks with line numbers and content
    patches = []
    lines = patch_text.splitlines()
    patch = None
    old_line = new_line = None
    for line in lines:
        header = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @", line)
        if header:
            if patch:
                patches.append(patch)
            old_start = int(header.group(1))
            old_len = int(header.group(2) or '1')
            new_start = int(header.group(3))
            new_len = int(header.group(4) or '1')
            patch = {
                'old_start': old_start,
                'old_end': old_start + old_len - 1,
                'new_start': new_start,
                'new_end': new_start + new_len - 1,
                'old_lines': [],
                'new_lines': []
            }
            old_line = old_start
            new_line = new_start
        elif patch is not None:
            if line.startswith('-'):
                patch['old_lines'].append(line[1:])
                old_line += 1
            elif line.startswith('+'):
                patch['new_lines'].append(line[1:])
                new_line += 1
            else:
                # context
                old_line += 1
                new_line += 1
    if patch:
                                                     
        patch['old_lines'] = '\n'.join(patch['old_lines'])
        patch['new_lines'] = '\n'.join(patch['new_lines'])
        patches.append(patch)
    return patches

def extract_CVEfix_info_from_gitcommit(commit_url, github_api_token=None):
    commit_info = []
    owner, repo, sha = parse_commit_url(commit_url)
    data = fetch_commit_data(owner, repo, sha, token=github_api_token)
    # print(f"data: {data}")
    parent_shas = [p['sha'] for p in data.get('parents', [])]
    if not parent_shas:
        print("No parent commit found. Cannot extract before state.")
        parent_sha = None
    else:
        parent_sha = parent_shas[0]

    for f in data.get('files', []):
        commit_info_item = {}
        path = f['filename']
        patch = f.get('patch', '')
        if patch == '':
            print(f"No patch found for {path}. Skipping.")
            print(f"error data: {f}")
            continue
        patches = parse_patch(patch)

        # print(f"Handling file: {path}")

        code_before_change = None
        if parent_sha:
            code_before_change = fetch_raw_file(owner, repo, parent_sha, path, token=github_api_token)
            # if code_before_change is not None:
                # print(f"code_before_change: {code_before_change}")
        code_after_change = fetch_raw_file(owner, repo, sha, path, token=github_api_token)
        # if code_after_change is not None:
            # print(f"code_after_change: {code_after_change}")

        commit_info_item = {
            'file': path,
            'code_before_change': code_before_change,
            'code_after_change': code_after_change,
            'patches': patches,
        }
        commit_info.append(commit_info_item)

    return commit_info

def main():
    cwe_number = 841

    data = fetch_all_cve_for_cwe(cwe_number, nvd_api_key)

    # with open(f"CWE_{cwe_number}.json", "w", encoding="utf-8") as f:
    #     json.dump(data, f, indent=2, ensure_ascii=False)
    #
                                                              

                
    for cve in tqdm(data["vulnerabilities"], desc="Processing CVEs",total=len(data["vulnerabilities"])):
    # for cve in data["vulnerabilities"]:
        references = cve["cve"]["references"]
        for url_item in references:
            url = url_item.get("url", "")
                                               
            if url.startswith("https://github.com/") and "/commit/" in url:
                print(url)
                commit_info = extract_CVEfix_info_from_gitcommit(url, github_api_token=github_api_token)
                                         
                url_item["commit_info"] = commit_info

    with open(f"CWE_{cwe_number}_with_commit_info.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()