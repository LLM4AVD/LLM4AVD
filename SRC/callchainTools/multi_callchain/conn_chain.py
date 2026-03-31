import json,jsonlines

input_layer_file='/home/fdse/hzc/LLM4VUL/scripts/callchains/RuoYi/multi_up_res_callchains_625.json'
output_multi_callchain_file='/home/fdse/hzc/LLM4VUL/scripts/callchains/RuoYi/multi_up_res_callchains_71.json'

with open(input_layer_file,'r',encoding='utf-8') as f:
    multi_layers=json.load(f)


all_chains=[]

for multi_layer in multi_layers:
    resource=multi_layer['layer0']['resource']
    sink_func_name=multi_layer['layer0']['func_name']
    sink_func_path=multi_layer['layer0']['file_path']
    sink_func_code=multi_layer['layer0']['code']
    sink_func_annotation=multi_layer['layer0']['annotation']
    sink_location=sink_func_path.split('/')[-1]+':'+sink_func_name
    down_chains=[]
    up_chains=[]
    # func_name_chain=[sink_func_name]
    # func_path_chain=[sink_func_path]
    # func_code_chain=[sink_func_code]
    # func_annotation_chain=[sink_func_annotation]


    layer1_down=multi_layer['layer1_down'][sink_func_name] if len(multi_layer['layer1_down'].keys())>0 else None
    if layer1_down is not None:
        for i,layer1_down_callchain in enumerate(layer1_down['call_chain_down'][0]):
            layer1_down_func_path=layer1_down_callchain.split(':')[0]
            layer1_down_func_name=layer1_down_callchain.split(':')[1]
            layer1_down_func_code=layer1_down['call_chain_down'][1][i]
            layer1_down_func_annotation=layer1_down['annotation'][i]
            
            layer2_down=multi_layer['layer2_down'][layer1_down_callchain] if layer1_down_callchain in multi_layer['layer2_down'].keys() else None
            if layer2_down is None:
                down_chains.append([[[[layer1_down_func_path+':'+layer1_down_func_name],[layer1_down_func_code]],[layer1_down_func_annotation]]])
                continue
            else:
                for j,layer2_down_callchain in enumerate(layer2_down['call_chain_down'][0]):
                    layer2_down_func_path=layer2_down_callchain.split(':')[0]
                    layer2_down_func_name=layer2_down_callchain.split(':')[1]
                    layer2_down_func_code=layer2_down['call_chain_down'][1][j]
                    layer2_down_func_annotation=layer2_down['annotation'][j]

                    layer3_down=multi_layer['layer3_down'][layer2_down_callchain] if layer2_down_callchain in multi_layer['layer3_down'].keys() else None
                    if layer3_down is None:
                        down_chains.append([[[layer1_down_func_path+':'+layer1_down_func_name,layer1_down_func_code],[layer1_down_func_annotation]],[[[layer2_down_func_path+':'+layer2_down_func_name],[layer2_down_func_code]],[layer2_down_func_annotation]]])
                        continue
                    else:
                        down_chains.append([[[layer1_down_func_path+':'+layer1_down_func_name,layer1_down_func_code],[layer1_down_func_annotation]],[[layer2_down_func_path+':'+layer2_down_func_name,layer2_down_func_code],[layer2_down_func_annotation]],[layer3_down['call_chain_down'],layer3_down['annotation']]])
                        continue


    layer1_up=multi_layer['layer1_up'][sink_func_name] if len(multi_layer['layer1_up'].keys())>0 else None
    if layer1_up is not None:
        for i,layer1_up_callchain in enumerate(layer1_up['call_chain_up'][0]):
            layer1_up_func_path=layer1_up_callchain.split(':')[0]
            layer1_up_func_name=layer1_up_callchain.split(':')[1]
            layer1_up_func_code=layer1_up['call_chain_up'][1][i]
            layer1_up_func_annotation=layer1_up['annotation'][i]
            
            layer2_up=multi_layer['layer2_up'][layer1_up_callchain] if layer1_up_callchain in multi_layer['layer2_up'].keys() else None
            if layer2_up is None:
                up_chains.append([[[[layer1_up_func_path+':'+layer1_up_func_name],[layer1_up_func_code]],[layer1_up_func_annotation]]])
                continue
            else:
                for j,layer2_up_callchain in enumerate(layer2_up['call_chain_up'][0]):
                    layer2_up_func_path=layer2_up_callchain.split(':')[0]
                    layer2_up_func_name=layer2_up_callchain.split(':')[1]
                    layer2_up_func_code=layer2_up['call_chain_up'][1][j]
                    layer2_up_func_annotation=layer2_up['annotation'][j]

                    layer3_up=multi_layer['layer3_up'][layer2_up_callchain] if layer2_up_callchain in multi_layer['layer3_up'].keys() else None
                    if layer3_up is None:
                        up_chains.append([[[layer1_up_func_path+':'+layer1_up_func_name,layer1_up_func_code],[layer1_up_func_annotation]],[[[layer2_up_func_path+':'+layer2_up_func_name],[layer2_up_func_code]],[layer2_up_func_annotation]]])
                        continue
                    else:
                        up_chains.append([[[layer1_up_func_path+':'+layer1_up_func_name,layer1_up_func_code],[layer1_up_func_annotation]],[[layer2_up_func_path+':'+layer2_up_func_name,layer2_up_func_code],[layer2_up_func_annotation]],[layer3_up['call_chain_up'],layer3_up['annotation']]])
                        continue


    chain={'resource':resource,'location':sink_location,'func_name':sink_func_name,'file_path':sink_func_path,'code':sink_func_code,'annotation':sink_func_annotation,'call_chain_down':down_chains,'call_chain_up':up_chains}
    all_chains.append(chain)
    with open(output_multi_callchain_file,'w',encoding='utf-8') as f:
        json.dump(all_chains, f, indent=4, ensure_ascii=False)


# with open(output_multi_callchain_file,'r',encoding='utf-8') as f:
#         layers=json.load(f)[0]
#         chains=layers['call_chain_down']
#         for chain in chains:
#             print(chain)
                




    # for i in range(3):
    #     if not continue_down and not continue_up:
    #         break
    #     if continue_down:
    #         one_down_layer=multi_layers[f'layer{i+1}_down']
    #         if len(one_down_layer.keys())==0:
    #             continue_down=False
    #         else:

    #     if continue_up:
    #         one_up_layer=multi_layers[f'layer{i+1}_up']
    #         if len(one_up_layer.keys())==0:
    #             continue_up=False
        
