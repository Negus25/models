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

if [ $# != 3 ]
then
    echo "Usage: bash run_standalone_train.sh [DATASET_PATH] [PRETRAINED_BACKBONE] [DEVICE_ID]"
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
echo $DATASET_PATH
PRETRAINED_BACKBONE=$(get_real_path $2)
echo $PRETRAINED_BACKBONE

if [ ! -d $DATASET_PATH ]
then
    echo "error: DATASET_PATH=$DATASET_PATH is not a directory"
exit 1
fi

if [ ! -f $PRETRAINED_BACKBONE ]
then
    echo "error: PRETRAINED_PATH=$PRETRAINED_BACKBONE is not a file"
exit 1
fi

export DEVICE_NUM=1
export DEVICE_ID=$3
export RANK_ID=0
export RANK_SIZE=1
export CPU_BIND_NUM=24

if [ -d "train" ];
then
    rm -rf ./train
fi
mkdir ./train
cp ../*.py ./train
cp ../*.yaml ./train
cp -r ../src ./train
cp -r ../model_utils ./train
cd ./train || exit
echo "start training for device $DEVICE_ID"
env > env.log

cmdopt=`lscpu | grep NUMA | tail -1 | awk '{print $4}'`
if test -z $cmdopt
then
  cpus=`cat /proc/cpuinfo| grep "processor"| wc -l`
  if [ $cpus -ge $CPU_BIND_NUM ]
  then
    start=`expr $cpus - $CPU_BIND_NUM`
    end=`expr $cpus - 1`
  else
    start=0
    end=`expr $cpus - 1`
  fi
  cmdopt=$start"-"$end
fi

taskset -c $cmdopt python train.py \
    --data_dir=$DATASET_PATH \
    --pretrained_backbone=$PRETRAINED_BACKBONE \
    --is_distributed=0 \
    --lr=0.001 \
    --loss_scale=1024 \
    --weight_decay=0.016 \
    --T_max=320 \
    --max_epoch=320 \
    --warmup_epochs=4 \
    --lr_scheduler=cosine_annealing > log.txt 2>&1 &
cd ..
