#!/bin/bash
# Copyright 2020 Huawei Technologies Co., Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ============================================================================

if [ $# != 6 ]
then
    echo "Usage: sh run_distribute_train.sh [DATASET_PATH] [TRAIN_IMG_DIR] [TRAIN_JSON_FILE] [VAL_IMG_DIR] [VAL_JSON_FILE] [RANK_TABLE_FILE]"
exit 1
fi

get_real_path(){
  if [ "${1:0:1}" == "/" ]; then
    echo "$1"
  else
    echo "$(realpath -m $PWD/$1)"
  fi
}

DATASET_PATH=$(get_real_path $1)
TRAIN_IMG_DIR=$2
TRAIN_JSON_FILE=$3
VAL_IMG_DIR=$4
VAL_JSON_FILE=$5
RANK_TABLE_FILE=$(get_real_path $6)
echo $DATASET_PATH
echo $RANK_TABLE_FILE

if [ ! -d $DATASET_PATH ]
then
    echo "error: DATASET_PATH=$DATASET_PATH is not a directory"
exit 1
fi

if [ ! -f $RANK_TABLE_FILE ]
then
    echo "error: RANK_TABLE_FILE=$RANK_TABLE_FILE is not a file"
exit 1
fi

export DEVICE_NUM=8
export RANK_SIZE=8
export RANK_TABLE_FILE=$RANK_TABLE_FILE
export MINDSPORE_HCCL_CONFIG_PATH=$RANK_TABLE_FILE

for((i=0; i<${DEVICE_NUM}; i++))
do
    export DEVICE_ID=$i
    export RANK_ID=$i
    rm -rf ./train_parallel$i
    mkdir ./train_parallel$i
    cp ../*.py ./train_parallel$i
    cp ../*.yaml ./train_parallel$i
    cp -r ../src ./train_parallel$i
    cp -r ../model_utils ./train_parallel$i
    cd ./train_parallel$i || exit
    echo "start training for rank $RANK_ID, device $DEVICE_ID"
    env > env.log
    nohup python train.py \
        --data_dir=$DATASET_PATH \
        --train_img_dir=$TRAIN_IMG_DIR \
        --train_json_file=$TRAIN_JSON_FILE \
        --val_img_dir=$VAL_IMG_DIR \
        --val_json_file=$VAL_JSON_FILE \
        --is_distributed=1 \
        --lr=0.01 \
        --t_max=500 \
        --max_epoch=500 \
        --warmup_epochs=20 \
        --per_batch_size=16 \
        --training_shape=416 \
        --lr_scheduler=cosine_annealing  > log.txt 2>&1 &
    cd ..
done