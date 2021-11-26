#!/bin/bash
# Copyright 2021 Huawei Technologies Co., Ltd
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
# Simple log helper functions
info() { echo -e "\033[1;34m[INFO ][MxStream] $1\033[1;37m" ; }
warn() { echo >&2 -e "\033[1;31m[WARN ][MxStream] $1\033[1;37m" ; }

PY_PATH=/usr/bin/python3.7

export LD_LIBRARY_PATH=${MX_SDK_HOME}/lib:${MX_SDK_HOME}/opensource/lib:${LD_LIBRARY_PATH}
export PYTHONPATH=${MX_SDK_HOME}/python:${PYTHONPATH}
export GST_PLUGIN_PATH=${MX_SDK_HOME}/opensource/lib/gstreamer-1.0:${MX_SDK_HOME}/lib/plugins
export GST_PLUGIN_SCANNER=${MX_SDK_HOME}/opensource/libexec/gstreamer-1.0/gst-plugin-scanner

# to set PYTHONPATH, import the StreamManagerApi.py
export PYTHONPATH=${PYTHONPATH}:${MX_SDK_HOME}/python

${PY_PATH} om_infer_perf_test.py \
--img_dir=/data/coco2017/val2017 \
--how_many_images_to_infer=-1 \
--pipeline_config=../conf/ssd_resnet50_fpn_ms_coco_opencv.pipeline \
--infer_stream_name=detection \
--output_dir=./om_infer_output_on_coco_val2017_OPENCV \
--infer_timeout_secs=5 \
--display_step=100 \
--draw_box=true \
--preprocess=OPENCV \
--score_thresh_for_draw=0.5


