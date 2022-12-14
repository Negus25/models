#!/bin/bash
# Copyright 2022 Huawei Technologies Co., Ltd
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
    echo "Usage: sh run_eval_for_ascend.sh [DEVICE_ID] [DATASET_PATH] [CHECKPOINT]"
exit 1
fi

# check device id
if [ "$1" -eq "$1" ] 2>/dev/null
then
    if [ $1 -lt 0 ] || [ $1 -gt 7 ]
    then
        echo "error: DEVICE_ID=$1 is not in (0-7)"
    exit 1
    fi
else
    echo "error: DEVICE_ID=$1 is not a number"
exit 1
fi

# check dataset path
if [ ! -d $2 ]
then
    echo "error: DATASET_PATH=$2 is not a directory"    
exit 1
fi

# check checkpoint file
if [ ! -f $3 ]
then
    echo "error: CHECKPOINT=$3 is not a file"    
exit 1
fi

export DEVICE_ID=$1

python ../eval.py --device_target='Ascend' --device_id=$DEVICE_ID --dataset_path=$2 --checkpoint=$3 --enable_checkpoint_dir=False > ./eval.log 2>&1 &
