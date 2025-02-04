#!/bin/bash

# 定义 inference.py 需要的参数
#MODEL_TYPE="mistralai/Mistral-7B-Instruct-v0.2"
MODEL_TYPE="Qwen/Qwen2-72B-Instruct"
# MODEL_TYPE="meta-llama/Meta-Llama-3.1-8B-Instruct"
# MODEL_TYPE="google/gemma-2-9b"
# MODEL_TYPE="In2Training/FILM-7B"
# export VLLM_ATTENTION_BACKEND=FLASHINFER


MODEL_TYPE="Qwen/Qwen2-72B-Instruct"
MODEL_NAME=$(basename $MODEL_TYPE)
MAX_LENGTH=16000
NUM_GPUS=8
INPUT_DIR="/home/yuhao/THREADING-THE-NEEDLE/Dataset/Dataset_short.json"
OUTPUT_DIR="./results"
OUTPUT_FILE="${OUTPUT_DIR}/${MODEL_NAME}_maxlen${MAX_LENGTH}.json"
export CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7
# 确保输出目录存在
# 运行 inference.py
python inference.py --model $MODEL_TYPE --max_length $MAX_LENGTH --gpu $NUM_GPUS  --input_file $INPUT_DIR  --output_file $OUTPUT_FILE 
CSV_PATH="/home/yuhao/THREADING-THE-NEEDLE/Evalution/results/accuracy_results.csv"
# 运行 eval.py
python eval.py --data $OUTPUT_FILE --csv $CSV_PATH --gpu $NUM_GPUS



MODEL_TYPE="meta-llama/Meta-Llama-3.1-70B-Instruct"
MODEL_NAME=$(basename $MODEL_TYPE)
OUTPUT_FILE="${OUTPUT_DIR}/${MODEL_NAME}_maxlen${MAX_LENGTH}.json"

python inference.py --model $MODEL_TYPE --max_length $MAX_LENGTH --gpu $NUM_GPUS  --input_file $INPUT_DIR  --output_file $OUTPUT_FILE 
# 运行 eval.py
python eval.py --data $OUTPUT_FILE --csv $CSV_PATH --gpu $NUM_GPUS


MODEL_TYPE="google/gemma-2-27b"
MODEL_NAME=$(basename $MODEL_TYPE)
OUTPUT_FILE="${OUTPUT_DIR}/${MODEL_NAME}_maxlen${MAX_LENGTH}.json"

python inference.py --model $MODEL_TYPE --max_length $MAX_LENGTH --gpu $NUM_GPUS  --input_file $INPUT_DIR  --output_file $OUTPUT_FILE 
# 运行 eval.py
python eval.py --data $OUTPUT_FILE --csv $CSV_PATH --gpu $NUM_GPUS


MODEL_TYPE="mistralai/Mixtral-8x7B-Instruct-v0.1"
MODEL_NAME=$(basename $MODEL_TYPE)
OUTPUT_FILE="${OUTPUT_DIR}/${MODEL_NAME}_maxlen${MAX_LENGTH}.json"

python inference.py --model $MODEL_TYPE --max_length $MAX_LENGTH --gpu $NUM_GPUS  --input_file $INPUT_DIR  --output_file $OUTPUT_FILE 
# 运行 eval.py
python eval.py --data $OUTPUT_FILE --csv $CSV_PATH --gpu $NUM_GPUS

