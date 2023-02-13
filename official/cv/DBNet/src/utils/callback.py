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
"""Monitor the result of DBNet."""
import os
import time
import numpy as np

import mindspore as ms
from mindspore.train.callback import Callback

from src.datasets.load import create_dataset
from src.modules.model import get_dbnet
from .metric import AverageMeter
from .eval_utils import WithEval


class ResumeCallback(Callback):
    def __init__(self, start_epoch_num=0):
        super(ResumeCallback, self).__init__()
        self.start_epoch_num = start_epoch_num

    def on_train_epoch_begin(self, run_context):
        run_context.original_args().cur_epoch_num += self.start_epoch_num


class DBNetMonitor(Callback):
    """
    Monitor the result of DBNet.
    If the loss is NAN or INF, it will terminate training.
    Note:
        If per_print_times is 0, do not print loss.
    Args:
        config(class): configuration class.
        train_net(nn.Cell): Train network.
        per_print_times (int): How many steps to print once loss. During sink mode, it will print loss in the
                               nearest step. Default: 1.
    Raises:
        ValueError: If per_print_times is not an integer or less than zero.
    """

    def __init__(self, config, train_net, lr, per_print_times=1):
        super(DBNetMonitor, self).__init__()
        if not isinstance(per_print_times, int) or per_print_times < 0:
            raise ValueError("The argument 'per_print_times' must be int and >= 0, "
                             "but got {}".format(per_print_times))
        self._per_print_times = per_print_times
        self._last_print_time = 0
        self.config = config
        self.lr = lr
        self.loss_avg = AverageMeter()
        self.rank_id = config.rank_id
        self.run_eval = config.run_eval
        self.eval_interval = config.eval_interval
        self.save_ckpt_dir = config.save_ckpt_dir
        if self.run_eval:
            config.backbone.pretrained = False
            eval_net = get_dbnet(config.net, config, isTrain=False)
            self.eval_net = WithEval(eval_net, config)
            val_dataset, _ = create_dataset(config, False)
            self.val_dataset = val_dataset.create_dict_iterator(output_numpy=True)
            self.max_f = 0.0
        self.train_net = train_net
        self.epoch_start_time = time.time()
        self.step_start_time = time.time()
        self.cur_steps = 0

    def load_parameter(self):
        param_dict = dict()
        for name, param in self.train_net.parameters_and_names():
            param_dict[name] = param
        ms.load_param_into_net(self.eval_net.model, param_dict)

    def on_train_step_begin(self, run_context):
        self.step_start_time = time.time()

    def on_train_step_end(self, run_context):
        """
        Print training loss at the end of step.

        Args:
            run_context (RunContext): Context of the train running.
        """
        cb_params = run_context.original_args()
        loss = cb_params.net_outputs
        cur_epoch = cb_params.cur_epoch_num
        if cb_params.net_outputs is not None:
            if isinstance(loss, tuple):
                if loss[1]:
                    self.config.logger.info("==========overflow!==========")
                loss = loss[0]
            loss = loss.asnumpy()
        else:
            self.config.logger.info("custom loss callback class loss is None.")
            return

        cur_step_in_epoch = (cb_params.cur_step_num - 1) % cb_params.batch_num + 1

        if cur_step_in_epoch == 1:
            self.loss_avg = AverageMeter()
        self.loss_avg.update(loss)

        if isinstance(loss, float) and (np.isnan(loss) or np.isinf(loss)):
            raise ValueError(
                "epoch: {} step: {}. Invalid loss, terminating training.".format(cur_epoch, cur_step_in_epoch))
        if self._per_print_times != 0 and (cb_params.cur_step_num - self._last_print_time) >= self._per_print_times:
            self._last_print_time = cb_params.cur_step_num
            loss_log = "epoch: [%s/%s] step: [%s/%s], loss: %.6f, lr: %.6f, per step time: %.3f ms" % (
                cur_epoch, self.config.train.total_epochs, cur_step_in_epoch, self.config.steps_per_epoch,
                np.mean(self.loss_avg.avg), self.lr[self.cur_steps], (time.time() - self.step_start_time) * 1000)
            self.config.logger.info(loss_log)
        self.cur_steps += 1

    def on_train_epoch_begin(self, run_context):
        """
        Called before each epoch beginning.
        Args:
            run_context (RunContext): Include some information of the model.
        """
        self.epoch_start_time = time.time()

    def on_train_epoch_end(self, run_context):
        """
        Called after each training epoch end.

        Args:
            run_context (RunContext): Include some information of the model.
        """
        cb_params = run_context.original_args()
        loss = cb_params.net_outputs
        cur_epoch = cb_params.cur_epoch_num
        epoch_time = (time.time() - self.epoch_start_time)
        loss_log = "epoch: [%s/%s], loss: %.6f, epoch time: %.3f s, per step time: %.3f ms" % (
            cur_epoch, self.config.train.total_epochs, loss[0].asnumpy(), epoch_time,
            epoch_time * 1000 / self.config.steps_per_epoch)
        self.config.logger.info(loss_log)
        if self.run_eval and cur_epoch % self.eval_interval == 0:
            self.load_parameter()
            self.eval_net.model.set_train(False)
            metrics, fps = self.eval_net.eval(self.val_dataset, show_imgs=self.config.eval.show_images)

            cur_f = metrics['fmeasure'].avg
            self.config.logger.info('current epoch is: %s \n FPS: %s \n Recall: %s \n Precision: %s \n Fmeasure: %s' % (
                cur_epoch, fps, metrics['recall'].avg, metrics['precision'].avg, metrics['fmeasure'].avg))
            if cur_f >= self.max_f and self.rank_id == 0:
                self.config.logger.info('update best ckpt at epoch: %s, best fmeasure is: %s' % (cur_epoch, cur_f))
                ms.save_checkpoint(self.eval_net.model,
                                   os.path.join(self.save_ckpt_dir, f"best_rank{self.config.rank_id}.ckpt"))
                self.max_f = cur_f

    def on_train_end(self, run_context):
        if self.rank_id == 0:
            self.config.logger.info('best fmeasure is: %s' % self.max_f)
