import json,jsonlines

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


down_path = "./RuoYi_down_callchains_414.json"
up_path='./RuoYi_up_callchains_414.json'
new_path = "./RuoYi_call_chains_up_down_414.json"

def process_data(down_path,up_path,new_path,sink_locations):
    # data_down = load_json(down_path)
    new_data = {}
    i=0
          
    for item in jsonlines.Reader(open(down_path,'r')):
        if item["resource"] not in new_data:
            new_data[item["resource"]] = {}
        new_data[item["resource"]][item["location"]] = {}
        new_data[item["resource"]][item["location"]]['full_path'] = sink_locations[i]
        new_data[item["resource"]][item["location"]]["function_name"] = item["call_chain_down"][0][0]
        new_data[item["resource"]][item["location"]]["code_snippet"] = item["call_chain_down"][1][0]
        new_data[item["resource"]][item["location"]]["call_chain_down"] = item["call_chain_down"][0][1:]
        new_data[item["resource"]][item["location"]]["call_chain_code_down"] = item["call_chain_down"][1][1:]
        new_data[item["resource"]][item["location"]]["annotation_down"] = item["annotation"]
        i+=1
          
    # data_up=load_json(up_path)
    for item in jsonlines.Reader(open(up_path,'r')):
        new_data[item["resource"]][item["location"]]["call_chain_up"] = item["call_chain_up"][0]
        new_data[item["resource"]][item["location"]]["call_chain_code_up"] = item["call_chain_up"][1]
        new_data[item["resource"]][item["location"]]["annotation_up"] = item["annotation"]


    save_json(new_path, new_data)

