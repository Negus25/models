# Copyright 2020-2021 Huawei Technologies Co., Ltd
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
"""hub config."""
from src.network import DenseNet121, DenseNet100
from src.model_utils.config import config

def create_network(name, *args, **kwargs):
    if name == 'densenet121':
        return DenseNet121(config.num_classes)
    if name == 'densenet100':
        return DenseNet100(*args, **kwargs)
    raise NotImplementedError(f"{name} is not implemented in the repo")
