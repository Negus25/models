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
""" Model Config """
MODEL_WIDTH = 128
MODEL_HEIGHT = 128
STREAM_NAME = "detection"

INFER_TIMEOUT = 100000
SELECTED_ATTRS = ["Bald", "Bangs", "Black_Hair", "Blond_Hair", "Brown_Hair", "Bushy_Eyebrows", "Eyeglasses", "Male",
                  "Mouth_Slightly_Open", "Mustache", "No_Beard", "Pale_Skin", "Young"]
TENSOR_DTYPE_FLOAT32 = 0
TENSOR_DTYPE_FLOAT16 = 1
TENSOR_DTYPE_INT8 = 2