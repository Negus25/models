# Copyright (c) 2022 Huawei Technologies Co., Ltd
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
"""Yolo eval."""
import os
import sys
import ast
import time
from collections import defaultdict
import argparse
import numpy as np
from pycocotools.coco import COCO
from pycocotools.cocoeval import COCOeval



def get_device_id():
    """Get device id"""
    device_id = os.getenv('DEVICE_ID', '0')
    return int(device_id)

def get_device_num():
    """Get device num"""
    device_num = os.getenv('RANK_SIZE', '1')
    return int(device_num)

class Redirct:
    """Redirct"""
    def __init__(self):
        self.content = ""

    def write(self, content):
        """write"""
        self.content += content

    def flush(self):
        """flush"""
        self.content = ""


class DetectionEngine:
    """Detection engine."""

    def __init__(self, config_detection):
        self.eval_ignore_threshold = config_detection.eval_ignore_threshold
        self.labels = ['person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 'boat',
                       'traffic light', 'fire hydrant', 'stop sign', 'parking meter', 'bench', 'bird', 'cat',
                       'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra', 'giraffe', 'backpack',
                       'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee', 'skis', 'snowboard', 'sports ball',
                       'kite', 'baseball bat', 'baseball glove', 'skateboard', 'surfboard', 'tennis racket',
                       'bottle', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple',
                       'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair',
                       'couch', 'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse', 'remote',
                       'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink', 'refrigerator', 'book',
                       'clock', 'vase', 'scissors', 'teddy bear', 'hair drier', 'toothbrush']
        self.num_classes = len(self.labels)
        self.results = {}
        self.file_path = ''
        self.save_prefix = config_detection.outputs_dir
        self.ann_file = config_detection.ann_file
        self._coco = COCO(self.ann_file)
        self._img_ids = list(sorted(self._coco.imgs.keys()))
        self.det_boxes = []
        self.nms_thresh = config_detection.nms_thresh
        self.multi_label = config_detection.multi_label
        self.multi_label_thresh = config_detection.multi_label_thresh
        self.coco_catIds = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27,
                            28, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 46, 47, 48, 49, 50, 51, 52, 53,
                            54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 67, 70, 72, 73, 74, 75, 76, 77, 78, 79, 80,
                            81, 82, 84, 85, 86, 87, 88, 89, 90]

    def do_nms_for_results(self):
        """Get result boxes."""
        for img_id in self.results:
            for clsi in self.results[img_id]:
                dets = self.results[img_id][clsi]
                dets = np.array(dets)
                keep_index = self._nms(dets, self.nms_thresh)

                keep_box = [{'image_id': int(img_id),
                             'category_id': int(clsi),
                             'bbox': list(dets[i][:4].astype(float)),
                             'score': dets[i][4].astype(float)}
                            for i in keep_index]
                self.det_boxes.extend(keep_box)

    def _nms(self, predicts, threshold):
        """Calculate NMS."""
        # convert xywh -> xmin ymin xmax ymax
        x1 = predicts[:, 0]
        y1 = predicts[:, 1]
        x2 = x1 + predicts[:, 2]
        y2 = y1 + predicts[:, 3]
        scores = predicts[:, 4]

        areas = (x2 - x1 + 1) * (y2 - y1 + 1)
        order = scores.argsort()[::-1]

        reserved_boxes = []
        while order.size > 0:
            i = order[0]
            reserved_boxes.append(i)
            max_x1 = np.maximum(x1[i], x1[order[1:]])
            max_y1 = np.maximum(y1[i], y1[order[1:]])
            min_x2 = np.minimum(x2[i], x2[order[1:]])
            min_y2 = np.minimum(y2[i], y2[order[1:]])

            intersect_w = np.maximum(0.0, min_x2 - max_x1 + 1)
            intersect_h = np.maximum(0.0, min_y2 - max_y1 + 1)
            intersect_area = intersect_w * intersect_h
            ovr = intersect_area / (areas[i] + areas[order[1:]] - intersect_area)

            indexes = np.where(ovr <= threshold)[0]
            order = order[indexes + 1]
        return reserved_boxes

    def _diou_nms(self, dets, thresh=0.5):
        """
        convert xywh -> xmin ymin xmax ymax
        """
        x1 = dets[:, 0]
        y1 = dets[:, 1]
        x2 = x1 + dets[:, 2]
        y2 = y1 + dets[:, 3]
        scores = dets[:, 4]
        areas = (x2 - x1 + 1) * (y2 - y1 + 1)
        order = scores.argsort()[::-1]
        keep = []
        while order.size > 0:
            i = order[0]
            keep.append(i)
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])

            w = np.maximum(0.0, xx2 - xx1 + 1)
            h = np.maximum(0.0, yy2 - yy1 + 1)
            inter = w * h
            ovr = inter / (areas[i] + areas[order[1:]] - inter)
            center_x1 = (x1[i] + x2[i]) / 2
            center_x2 = (x1[order[1:]] + x2[order[1:]]) / 2
            center_y1 = (y1[i] + y2[i]) / 2
            center_y2 = (y1[order[1:]] + y2[order[1:]]) / 2
            inter_diag = (center_x2 - center_x1) ** 2 + (center_y2 - center_y1) ** 2
            out_max_x = np.maximum(x2[i], x2[order[1:]])
            out_max_y = np.maximum(y2[i], y2[order[1:]])
            out_min_x = np.minimum(x1[i], x1[order[1:]])
            out_min_y = np.minimum(y1[i], y1[order[1:]])
            outer_diag = (out_max_x - out_min_x) ** 2 + (out_max_y - out_min_y) ** 2
            diou = ovr - inter_diag / outer_diag
            diou = np.clip(diou, -1, 1)
            inds = np.where(diou <= thresh)[0]
            order = order[inds + 1]
        return keep

    def write_result(self):
        """Save result to file."""
        import json
        t = "_1"
        try:
            self.file_path = self.save_prefix + '/predict' + t + '.json'
            f = open(self.file_path, 'w')
            json.dump(self.det_boxes, f)
        except IOError as e:
            raise RuntimeError("Unable to open json file to dump. What(): {}".format(str(e)))
        else:
            f.close()
            return self.file_path

    def get_eval_result(self):
        """Get eval result."""
        coco_gt = COCO(self.ann_file)
        coco_dt = coco_gt.loadRes(self.file_path)
        coco_eval = COCOeval(coco_gt, coco_dt, 'bbox')
        coco_eval.evaluate()
        coco_eval.accumulate()
        rdct = Redirct()
        stdout = sys.stdout
        sys.stdout = rdct
        coco_eval.summarize()
        sys.stdout = stdout
        return rdct.content

    def detect(self, outputs, batch, image_shape, image_id):
        """Detect boxes."""
        outputs_num = len(outputs)
        # output [|32, 52, 52, 3, 85| ]
        for batch_id in range(batch):
            for out_id in range(outputs_num):
                # 32, 52, 52, 3, 85
                out_item = outputs[out_id]
                # 52, 52, 3, 85
                out_item_single = out_item[batch_id, :]
                # get number of items in one head, [B, gx, gy, anchors, 5+80]
                dimensions = out_item_single.shape[:-1]
                out_num = 1
                for d in dimensions:
                    out_num *= d
                ori_w, ori_h = image_shape[batch_id]
                img_id = int(image_id[batch_id])
                x = out_item_single[..., 0] * ori_w
                y = out_item_single[..., 1] * ori_h
                w = out_item_single[..., 2] * ori_w
                h = out_item_single[..., 3] * ori_h

                conf = out_item_single[..., 4:5]
                cls_emb = out_item_single[..., 5:]
                cls_argmax = np.expand_dims(np.argmax(cls_emb, axis=-1), axis=-1)
                x = x.reshape(-1)
                y = y.reshape(-1)
                w = w.reshape(-1)
                h = h.reshape(-1)
                x_top_left = x - w / 2.
                y_top_left = y - h / 2.
                cls_emb = cls_emb.reshape(-1, self.num_classes)
                if self.multi_label:
                    conf = conf.reshape(-1, 1)
                    # create all False
                    confidence = cls_emb * conf
                    flag = cls_emb > self.multi_label_thresh
                    flag = flag.nonzero()
                    for index in range(len(flag[0])):
                        i = flag[0][index]
                        j = flag[1][index]
                        confi = confidence[i][j]
                        if confi < self.eval_ignore_threshold:
                            continue
                        if img_id not in self.results:
                            self.results[img_id] = defaultdict(list)
                        x_lefti = max(0, x_top_left[i])
                        y_lefti = max(0, y_top_left[i])
                        wi = min(w[i], ori_w)
                        hi = min(h[i], ori_h)
                        clsi = j
                        # transform catId to match coco
                        coco_clsi = self.coco_catIds[clsi]
                        self.results[img_id][coco_clsi].append([x_lefti, y_lefti, wi, hi, confi])
                else:
                    cls_argmax = np.expand_dims(np.argmax(cls_emb, axis=-1), axis=-1)
                    conf = conf.reshape(-1)
                    cls_argmax = cls_argmax.reshape(-1)

                    # create all False
                    flag = np.random.random(cls_emb.shape) > sys.maxsize
                    for i in range(flag.shape[0]):
                        c = cls_argmax[i]
                        flag[i, c] = True
                    confidence = cls_emb[flag] * conf

                    for x_lefti, y_lefti, wi, hi, confi, clsi in zip(x_top_left, y_top_left, w, h, confidence,
                                                                     cls_argmax):
                        if confi < self.eval_ignore_threshold:
                            continue
                        if img_id not in self.results:
                            self.results[img_id] = defaultdict(list)
                        x_lefti = max(0, x_lefti)
                        y_lefti = max(0, y_lefti)
                        wi = min(wi, ori_w)
                        hi = min(hi, ori_h)
                        # transform catId to match coco
                        coco_clsi = self.coco_catIds[clsi]
                        self.results[img_id][coco_clsi].append([x_lefti, y_lefti, wi, hi, confi])


def convert_testing_shape(config_testing_shape):
    """Convert testing shape to list."""
    testing_shape = [int(config_testing_shape), int(config_testing_shape)]
    return testing_shape


def modelarts_pre_process():
    '''modelarts pre process function.'''
    def unzip(zip_file, save_dir):
        import zipfile
        s_time = time.time()
        if not os.path.exists(os.path.join(save_dir, config.modelarts_dataset_unzip_name)):
            zip_isexist = zipfile.is_zipfile(zip_file)
            if zip_isexist:
                fz = zipfile.ZipFile(zip_file, 'r')
                data_num = len(fz.namelist())
                print("Extract Start...")
                print("unzip file num: {}".format(data_num))
                data_print = int(data_num / 100) if data_num > 100 else 1
                i = 0
                for file in fz.namelist():
                    if i % data_print == 0:
                        print("unzip percent: {}%".format(int(i * 100 / data_num)), flush=True)
                    i += 1
                    fz.extract(file, save_dir)
                print("cost time: {}min:{}s.".format(int((time.time() - s_time) / 60),
                                                     int(int(time.time() - s_time) % 60)))
                print("Extract Done.")
            else:
                print("This is not zip.")
        else:
            print("Zip has been extracted.")

    if config.need_modelarts_dataset_unzip:
        zip_file_1 = os.path.join(config.data_path, config.modelarts_dataset_unzip_name + ".zip")
        save_dir_1 = os.path.join(config.data_path)

        sync_lock = "/tmp/unzip_sync.lock"

        # Each server contains 8 devices as most.
        if get_device_id() % min(get_device_num(), 8) == 0 and not os.path.exists(sync_lock):
            print("Zip file path: ", zip_file_1)
            print("Unzip file save dir: ", save_dir_1)
            unzip(zip_file_1, save_dir_1)
            print("===Finish extract data synchronization===")
            try:
                os.mknod(sync_lock)
            except IOError:
                pass

        while True:
            if os.path.exists(sync_lock):
                break
            time.sleep(1)

        print("Device: {}, Finish sync unzip data from {} to {}.".format(get_device_id(), zip_file_1, save_dir_1))

    config.log_path = os.path.join(config.output_path, config.log_path)

def parser_args():
    """
    configuration parameter, input from outside
    """
    parser = argparse.ArgumentParser(description="yolov3_tiny inference")
    parser.add_argument("--pipeline_path", type=str, required=False, default="./config/yv3.pipeline",
                        help="pipeline file path. The default is './config/yv3.pipeline'. ")
    parser.add_argument('--log_path', type=str, default='../data/eval_log', help='inference result save location')
    parser.add_argument('--nms_thresh', type=float, default=0.5, help='threshold for NMS')
    parser.add_argument('--ann_file', type=str, default='../../data/annotations/instances_val2017.json',
                        help='path to annotation')
    parser.add_argument('--eval_ignore_threshold', type=float, default=0.001,
                        help='threshold to throw low quality boxes')
    parser.add_argument('--dataset_path', type=str, default='../../data/val2017', help='path of image dataset')
    parser.add_argument('--result_files', type=str, default='../data/preds/sdk/val2017',
                        help='path to 310 infer result path')
    parser.add_argument('--multi_label', type=ast.literal_eval, default=True, help='whether to use multi label')
    parser.add_argument('--multi_label_thresh', type=float, default=0.1, help='threshold to throw low quality boxes')
    parser.add_argument('--toalignfile', type=str, default='../data/preds/sdk/test.txt',
                        help='to align file save location')
    arg = parser.parse_args()
    return arg

if __name__ == "__main__":

    lib_path = os.path.abspath(os.path.join('../..'))
    sys.path.append(lib_path)
    from model_utils.config import config

    print("Begin mxbase prediction result eval....")
    start_time = time.time()

    args = parser_args()
    args.outputs_dir = os.path.join(args.log_path,
                                    "06-27-1")
    if not os.path.exists(args.outputs_dir):
        os.makedirs(args.outputs_dir)
    detection = DetectionEngine(args)

    file_list = os.listdir(args.dataset_path)

    coco = COCO(args.ann_file)

    for _, file_name in enumerate(file_list):

        img_ids_name = file_name.split('.')[0]
        img_id_ = int(np.squeeze(img_ids_name))
        imgIds = coco.getImgIds(imgIds=[img_id_])
        img = coco.loadImgs(imgIds[np.random.randint(0, len(imgIds))])[0]
        image_shapes = ((img['width'], img['height']),)
        img_id_ = (np.squeeze(img_ids_name),)

        img_ids = file_name.split(".")[0]

        np_path_0 = os.path.join(args.result_files, img_ids) + "_0.bin"
        np_path_1 = os.path.join(args.result_files, img_ids) + "_1.bin"
        f_0 = open(np_path_0, 'rb')
        output_small = np.fromfile(f_0, dtype=np.float32).reshape((1, 20, 20, 3, 85))
        f_1 = open(np_path_1, 'rb')
        output_big = np.fromfile(f_1, dtype=np.float32).reshape((1, 40, 40, 3, 85))

        if img_ids == "000000000139":
            print('txt has been produced')
            with open(args.toalignfile, 'w') as fp:
                for ii in range(len(output_small)):
                    fp.write(str(output_big[ii]) + '\n')

        detection.detect([output_small, output_big], 1, image_shapes, img_id_)


    print('do_nms_for_results...')
    detection.do_nms_for_results()
    detection.write_result()
    eval_result = detection.get_eval_result()
    print('\n=============coco eval result=========\n' + eval_result)

    cost_time = time.time() - start_time
    print('testing cost time {:.2f}s'.format(cost_time))