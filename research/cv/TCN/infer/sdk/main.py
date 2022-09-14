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
""" main.py """
import argparse
import os
import json
from StreamManagerApi import StreamManagerApi
from StreamManagerApi import MxDataInput, InProtobufVector, MxProtobufIn
import MxpiDataType_pb2 as MxpiDataType
import numpy as np


shape = [1, 1, 784]

def parse_args(parsers):
    """
    Parse commandline arguments.
    """
    parsers.add_argument('--images_txt_path', type=str,
                         default="../data/mnist_infer_data/mnist_bs_1_label.txt",
                         help='image text')
    return parsers


def read_file_list(input_file):
    """
    :param infer file content:
        1.bin 0
        2.bin 2
        ...
    :return image path list, label list
    """
    image_file = []
    labels_l = []
    if not os.path.exists(input_file):
        print('input file does not exists.')
    with open(input_file, "r") as fs:
        for line in fs.readlines():
            line = line.strip('\n').split(',')
            file_name = line[0]
            label = line[1]
            image_file.append(file_name)
            labels_l.append(label)
    return image_file, labels_l


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Om TCN Inference')
    parser = parse_args(parser)
    args, _ = parser.parse_known_args()
    # init stream manager
    stream_manager = StreamManagerApi()
    ret = stream_manager.InitManager()
    if ret != 0:
        print("Failed to init Stream manager, ret=%s" % str(ret))
        exit()

    # create streams by pipeline config file
    with open("../data/config/TCN.pipeline", 'rb') as f:
        pipeline = f.read()
    ret = stream_manager.CreateMultipleStreams(pipeline)
    if ret != 0:
        print("Failed to create Stream, ret=%s" % str(ret))
        exit()

    # Construct the input of the stream

    res_dir_name = 'result'
    if not os.path.exists(res_dir_name):
        os.makedirs(res_dir_name)

    if not os.path.exists("../results"):
        os.makedirs("../results")

    file_list, label_list = read_file_list(args.images_txt_path)

    img_size = len(file_list)
    results = []

    for idx, file in enumerate(file_list):
        image_path = os.path.join(args.images_txt_path.replace('label.txt', 'bin'), file)

        # Construct the input of the stream
        data_input = MxDataInput()
        with open(image_path, 'rb') as f:
            data = f.read()
        data_input.data = data
        tensorPackageList1 = MxpiDataType.MxpiTensorPackageList()
        tensorPackage1 = tensorPackageList1.tensorPackageVec.add()
        tensorVec1 = tensorPackage1.tensorVec.add()
        tensorVec1.deviceId = 0
        tensorVec1.memType = 0
        for t in shape:
            tensorVec1.tensorShape.append(t)
        tensorVec1.dataStr = data_input.data
        tensorVec1.tensorDataSize = len(data)
        protobufVec1 = InProtobufVector()
        protobuf1 = MxProtobufIn()
        protobuf1.key = b'appsrc0'
        protobuf1.type = b'MxTools.MxpiTensorPackageList'
        protobuf1.protobuf = tensorPackageList1.SerializeToString()
        protobufVec1.push_back(protobuf1)

        unique_id = stream_manager.SendProtobuf(b'TCN', b'appsrc0', protobufVec1)

        # Obtain the inference result by specifying streamName and uniqueId.
        infer_result = stream_manager.GetResult(b'TCN', 0)
        if infer_result.errorCode != 0:
            print("GetResultWithUniqueId error. errorCode=%d, errorMsg=%s" % (
                infer_result.errorCode, infer_result.data.decode()))
            exit()

        res = json.loads(infer_result.data.decode())['MxpiClass'][0]['className']

        results.append(res)

    results = np.array(results)
    labels = np.array(label_list)
    np.savetxt("./result/infer_results.txt", results, fmt='%s')

    # destroy streams
    stream_manager.DestroyAllStreams()
    acc = (results == labels).sum() / img_size
    print('total acc:', acc)

    with open("../results/eval_sdk.log", 'w') as f:
        f.write('Eval size: {} \n'.format(img_size))
        f.write('total acc: {} \n'.format(acc))