import json
import random
import re
import time
import numpy as np
import pandas as pd
# from vllm import LLM, SamplingParams
import argparse
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
from datasets import load_dataset
# 读取JSON文件
def read_json(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

# 写入JSON文件
def write_json(file_path, data):
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)


def parse_args():
    parser = argparse.ArgumentParser(description='Run LLM with command line arguments.')
    parser.add_argument('--data', type=str, required=True, help='data_path')
    parser.add_argument('--csv', type=str, required=True, help='csv_path')
    parser.add_argument('--gpu', type=int, default=1, help='Number of GPUs to use.')
    parser.add_argument('--model', type=str, default=None, choices=["phi4-unsloth","phi4","mistral","qwen2.5","llama3.1-8b-instruct","llama2-7b-chat-4k", "llama-2-7B-32k-instruct", "longchat-v1.5-7b-32k", "xgen-7b-8k", "internlm-7b-8k", "chatglm2-6b", "chatglm2-6b-32k", "chatglm3-6b-32k", "vicuna-v1.5-7b-16k"])
    parser.add_argument('--hopf_type', type=str, default="max_fused")
    parser.add_argument('--len', "-l", type=int, default=None)
    parser.add_argument('--e', action='store_true', help="Evaluate on LongBench-E")
    parser.add_argument("--window_size", "-ws", type=int, default=3, help="Window size for HopFormer")
    parser.add_argument("--sim_threshold", "-st", type=float, default=20.0, help="Similarity threshold for HopFormer")
    parser.add_argument("--exhale_after", "-ea", type=float, default=1.0, help="Exhale after exceeding this times the KV limit")
    parser.add_argument("--num_attn_sinks", "-snks", type=float, default=0, help="Attention sinks (streaming LLM)")
    parser.add_argument("--gumbel", "-gbl", action='store_true', help="use gumbel softmax")
    parser.add_argument("--no_hopf", action='store_true', help="Disable HopFormer")  # Updated line
    parser.add_argument("--save_wts", action='store_true', help="Save attn wts")  # Updated line
    return parser.parse_args()


# 解析output_blocks中特定类型的条目
def parse_blocks(output_blocks, type):
    type_to_block = {}
    pattern = rf"{type} (\d+)"  # 假设类型后的数字仍有用，例如标识ID或序号
    for block in output_blocks:
        match = re.search(pattern, block)
        if match:
            identifier = int(match.group(1))  # 获取类型后的数字
            if identifier not in type_to_block or type_to_block[identifier] is None:
                type_to_block[identifier] = block

    return type_to_block

# 生成检查内容的prompt
def create_prompts(checks, type_to_block):
    prompts = []
    identifiers = []
    for identifier, event_desc in checks.items():
        identifier = int(identifier)  # 确保转换为整数
        if identifier in type_to_block:
            prompt = f"Context: " + type_to_block[identifier] + f"### Instruction: Does this context include the {event_desc}? Please answer with 'yes' or 'no' only."
            prompts.append(prompt)
            identifiers.append(identifier)
    return prompts, identifiers

# 定义评估准确性的函数
def evaluate_accuracy(prompts, llm, sampling_params):
    outputs = llm.generate(prompts, sampling_params)
    results = []
    for output in outputs:
        response = output.outputs[0].text.strip().lower()
        result = 'yes' if 'yes' in response else 'no'
        results.append(result)
    return results

# 保存准确率到CSV文件
def save_accuracy_to_csv(file_path, model_name, completion_rate, acc_once, acc_range, acc_periodic):
    df = pd.DataFrame({
        'Model': [model_name],
        'Completion Rate': [completion_rate],
        'Accuracy Once': [acc_once],
        'Accuracy Range': [acc_range],
        'Accuracy Periodic': [acc_periodic],
        'Average Accuracy': [(acc_once + acc_range + acc_periodic) / 3]
    })
    
    try:
        existing_df = pd.read_csv(file_path)
        existing_df = existing_df[existing_df['Model'] != model_name]  # 删除相同模型名称的行
        df = pd.concat([existing_df, df], ignore_index=True)
    except FileNotFoundError:
        pass
    
    df.to_csv(file_path, index=False)

def seed_everything(seed):
    torch.manual_seed(seed)
    nprch.cuda.manual_seed(seed)
    np.random.seed(seed)
    random.seed(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.cuda.manual_seed_all(seed)

# 计算完成度
def calculate_completion_rate(type_to_block, total_number):
    identifiers = set(type_to_block.keys())
    expected_identifiers = set(range(1, total_number + 1))
    missing_identifiers = expected_identifiers - identifiers
    completion_rate = (len(expected_identifiers) - len(missing_identifiers)) / len(expected_identifiers)
    return completion_rate * 100

# 主函数
seed_everything(42)

args = parse_args()

#csv_file_path = "/home/yuhao/THREADING-THE-NEEDLE/Evalution/results/accuracy_results.csv"
model_name = args.model
dataset = load_dataset("mozhu/LongGenBench")
datas = dataset['train']

prompts_once = []
prompts_range = []
prompts_periodic = []
identifiers_once = []
identifiers_range = []
identifiers_periodic = []

completion_rate = 0
for data in datas:
    checks_block = parse_blocks(data['output_blocks'], data['type'])
    # 生成once, range, periodic的prompts
    p_once, ids_once = create_prompts(data['checks_once'], checks_block)
    p_range, ids_range = create_prompts(data['checks_range'], checks_block)
    p_periodic, ids_periodic = create_prompts(data['checks_periodic'], checks_block)
    
    prompts_once.extend(p_once)
    identifiers_once.extend(ids_once)
    
    prompts_range.extend(p_range)
    identifiers_range.extend(ids_range)
    
    prompts_periodic.extend(p_periodic)
    identifiers_periodic.extend(ids_periodic)

    data['count_once'] = len(ids_once)
    data['count_range'] = len(ids_range)
    data['count_periodic'] = len(ids_periodic)

    completion_rate += calculate_completion_rate(checks_block, data['number'])

completion_rate /= len(datas)  # 平均完成度

# Define the sampling parameters
sampling_params = SamplingParams(temperature=0.95, top_p=0.95, max_tokens=50, seed=42)

# Record the start time
start_time = time.time()

# Initialize the model and tokenizer from Hugging Face
model_name = "meta-llama/Meta-Llama-3.1-8B-Instruct"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)
model.to('cuda' if torch.cuda.is_available() else 'cpu')

# Define a function to generate responses using Hugging Face Transformers
def generate_responses(prompts, model, tokenizer, sampling_params):
    results = []
    for prompt in prompts:
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        outputs = model.generate(
            **inputs,
            max_length=sampling_params.max_tokens,
            temperature=sampling_params.temperature,
            top_p=sampling_params.top_p,
            do_sample=True
        )
        response = tokenizer.decode(outputs[0], skip_special_tokens=True).strip().lower()
        result = 'yes' if 'yes' in response else 'no'
        results.append(result)
    return results

# Evaluate the accuracy for each set of prompts using the new function
results_once = generate_responses(prompts_once, model, tokenizer, sampling_params)
results_range = generate_responses(prompts_range, model, tokenizer, sampling_params)
results_periodic = generate_responses(prompts_periodic, model, tokenizer, sampling_params)


# 计算准确率
acc_once = sum(1 for result in results_once if result == 'yes') / len(results_once) if results_once else 0
acc_range = sum(1 for result in results_range if result == 'yes') / len(results_range) if results_range else 0
acc_periodic = sum(1 for result in results_periodic if result == 'yes') / len(results_periodic) if results_periodic else 0

# 将结果添加到JSON文件中
start_index_once = 0
start_index_range = 0
start_index_periodic = 0
for data in datas:
    data['results_once'] = {str(identifiers_once[i]): results_once[i] for i in range(start_index_once, start_index_once + data['count_once'])}
    start_index_once += data['count_once']
    
    data['results_range'] = {str(identifiers_range[i]): results_range[i] for i in range(start_index_range, start_index_range + data['count_range'])}
    start_index_range += data['count_range']
    
    data['results_periodic'] = {str(identifiers_periodic[i]): results_periodic[i] for i in range(start_index_periodic, start_index_periodic + data['count_periodic'])}
    start_index_periodic += data['count_periodic']

# 写回JSON文件
write_json(args.data, datas)
# 保存准确率到CSV文件
save_accuracy_to_csv(args.csv, model_name, completion_rate, acc_once, acc_range, acc_periodic)

# Print the elapsed time
elapsed_time = time.time() - start_time
print(f"Elapsed time: {elapsed_time:.2f} seconds")
