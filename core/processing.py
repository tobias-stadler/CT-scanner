import numpy as np
from core import fsimage, scandata, fsutil
import PIL
from pathlib import Path

class Processor:
    """
    Interface for implementing a step in the processing stack
    """

    def process_static(self, arr: np.ndarray):
         """
         Process data with supplied settings
         :param arr: input numpy array
         :return: output numpy array
         """
         return arr

    def process_auto(self, arr: np.ndarray):
        """
        Process data and automatically calculate settings
        :param arr: input numpy array
        :return: output numpy array
        """
        return self.process_static(arr)

class ProcessingStack:

    """
    Utility to combine multiple data processors into a consecutive processing stack
    """

    def __init__(self):
        self.processors = []
        self.processors_enable = []
        self.processors_name = []

    def push(self, proc: Processor, name, enable=True):
        """
        Add new processor to the end of processing stack
        :param proc: Processor to be added
        :param name: descriptive name for later access
        :param enable: bool if processor is enabled by default
        :return: reference to self for chaining multiple calls together
        """
        self.processors.append(proc)
        self.processors_enable.append(enable)
        self.processors_name.append(name)
        return self

    def execute(self, arr: np.ndarray, auto=True):
        """
        Run numpy array through processing stack
        :param arr: input numpy array
        :param auto: bool if processors should automatically calculate their settings
        :return: processed numpy array
        """
        intermediate_arr = arr.astype(np.float32)

        for i in range(len(self.processors)):
            if self.processors_enable[i]:
                if auto:
                    intermediate_arr = self.processors[i].process_auto(intermediate_arr)
                else:
                    intermediate_arr = self.processors[i].process_static(intermediate_arr)

        return intermediate_arr

    def enable_all(self):
        """
        Enable all processors
        """
        for i in range(len(self.processors_enable)):
            self.processors_enable[i] = True

    def disable_all(self):
        """
        Disable all processors
        """
        for i in range(len(self.processors_enable)):
            self.processors_enable[i] = False

    def enable_list(self, ran):
        """
        Enable multiple processors
        :param ran: list of processor ids or names (can be mixed)
        """
        for i in range(len(self.processors)):
            if i in ran or self.processors[i] in ran or self.processors_name[i] in ran:
                self.processors_enable[i] = True

    def get_processor(self, name):
        """
        Get reference to processor in processing stack
        :param name: processor name or id
        :return:
        """
        for i in range(len(self.processors)):
            if self.processors_name[i] == name or i == name:
                return self.processors[i]

    def to_dict(self, name, dic=None):
        """
        Export the settings of all processors into python dict
        :param name: dictionary key
        :param dic: dict for data to be stored in
        :return: data filled dict
        """
        proc_params = []
        for proc in self.processors:
            proc_params.append(proc.__dict__)

        if dic is None:
            dic = {}

        dic[name] = proc_params

        return dic

    def from_dict(self, name, dic):
        """
        Import processor settings from dict
        :param name: dictionary key
        :param dic: dict containing processor settings
        """
        for i in range(len(self.processors)):
            try:
                for key, val in dic[name][i].items():
                    setattr(self.processors[i], key, val)
            except Exception as e:
                print("ProcessingStack from_dict warning: " + str(e))
                #traceback.print_exc()

class XRayProcessingStack(ProcessingStack):
    """
    Default processing stack for converting X-ray images to attenuation values
    """
    def __init__(self):
        super().__init__()
        self.push(NormalizeProc(min=None, max=1),"normalize_raw").push(LimitProcAlt(), "limit_pre").push(NormalizeProc(min=None, max=1), "normalize_pre").push(LogProc(), "log").push(LimitProcAlt(), "limit_post").push(NormalizeProc(min=None, max=1), "normalize_final")#push(CropProc(0, 0, 256, 256), "crop")

class LimitProc(Processor):
    def __init__(self, low=None, high=None):
        """
        Cut off values outside the range between low and high
        :param low: minimum value
        :param high: maximum value
        """
        self.low_limit = low
        self.high_limit = high

    def process_static(self, arr):
        if self.low_limit is not None:
            arr[arr < self.low_limit] = self.low_limit

        if self.high_limit is not None:
            arr[arr > self.high_limit] = self.high_limit

        print("Limited from %f to %f" % (self.low_limit, self.high_limit))
        return arr

class LimitProcAlt(Processor):
    def __init__(self, low=None, high=None):
        """
        Like LimitProc, but all values below low will be 0 instead of low
        :param low: minimum value
        :param high: maximum value
        """
        self.low_limit = low
        self.high_limit = high

    def process_static(self, arr):
        if self.low_limit is not None:
            arr[arr < self.low_limit] = 0

        if self.high_limit is not None:
            arr[arr > self.high_limit] = self.high_limit

        print("Limited from %f to %f" % (self.low_limit, self.high_limit))
        return arr

class CropProc(Processor):
    def __init__(self, x, y, w, h):
        """
        Crop image to specified size
        :param x: x position
        :param y: y position
        :param w: width
        :param h: height
        """
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    def process_static(self, arr: np.ndarray):
        return arr[round(self.x):round(self.x+self.w), round(self.y):round(self.y+self.h)]

class NormalizeProc(Processor):
    def __init__(self, min=None, max=None):
        """
        Normalize/Scale data to a range between 0 and 1
        :param min: minimum value that should correspond to 0. if auto min will be assigned to the minimum value in the array
        :param max: maximum value that should correspond to 1. if auto max will be assigned to the maximum value in the array
        """
        self.min = min
        self.max = max

    def process_static(self, arr):
        if self.min is not None:
            arr -= self.min

        if self.max is not None:
            arr /= self.max

        print("Normalized (min: %f, max: %f)" % (self.min if self.min else -1, self.max if self.max else -1))
        return arr

    def process_auto(self, arr: np.ndarray):
        if self.min is not None:
            self.min = float(np.min(arr))
        if self.max is not None:
            self.max = float(np.max(arr)) - (self.min if self.min is not None else 0)

        return self.process_static(arr)

class LogProc(Processor):
   """
   Apply the negative natural logarithm
   """

   def process_static(self, arr):
        arr = -np.log(arr)
        #arr = np.nan_to_num(arr)
        print("Calculated minus log")
        return arr


