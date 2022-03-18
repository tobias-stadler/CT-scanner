from pathlib import Path

import PIL
import numpy as np

from core import processing, fsimage, fsutil
import cv2
import matplotlib.pyplot as plt

# All measurements in mm or px

class ReconstructionParameters:
    def __init__(self):
        self.dist_source_origin = 10000
        self.dist_origin_detector = 0
        self.axis_adj = 0
        self.in_name = "full"
        self.out_name = "recon"
        self.algorithm = "SIRT3D_CUDA"
        self.alg_iterations = 100
        self.high_output = 1

class ProcessingParameters:
    def __init__(self):
        self.coords_align = [0, 0, 500] # top left corner of rectangle (x,y,width/height)
        self.coords_axis = [260, 300, 50, 50] # top left corner of rectangle (x,y,width,height)
        self.coords_crop = [256, 128] # (width, height)
        self.dist_reference = 150
        self.downsample = 4
        self.out_name = "full"

    def get_center(self):
        half = self.coords_align[2]/2
        return (self.coords_align[0] + half, self.coords_align[1] + half)

    def get_rotaxis_x(self):
        return self.coords_axis[0] + self.coords_axis[2]/2

    def get_detector_spacing(self):
        return (self.dist_reference/(self.coords_align[2]))*self.downsample

    def get_shift_x(self):
        return (self.get_rotaxis_x()-self.get_center()[0])/self.downsample

class ScanParameters:
    def __init__(self):
        self.shutterlen = 500
        self.exposure = 500
        self.focuslen = 500

class CTScan:
    """
    Object for storing all scan related data
    """
    def __init__(self, name):
        self.path = None
        self.name = name
        self.num_projections = 180
        self.scan_max_angle = 360

        self.scan_parameters = ScanParameters()
        self.processing_parameters = ProcessingParameters()
        self.reconstruction_parameters = ReconstructionParameters()

        self.target_angles = []
        self.reached_angles = []

        self.processing_stack = processing.XRayProcessingStack()


    def scan_prepare(self):
        """
        Prepare internal data structures for running a scan
        """
        self.target_angles = [(self.scan_max_angle / self.num_projections) * i for i in range(self.num_projections)]
        self.reached_angles = []

    def process_all(self):
        center_x = self.processing_parameters.get_center()[0]
        center_y = self.processing_parameters.get_center()[1]
        # Calculate image region
        x = center_x - self.processing_parameters.coords_crop[0]/2
        y = center_y - self.processing_parameters.coords_crop[1]/2
        x2 = center_x + self.processing_parameters.coords_crop[0]/2
        y2 = center_y + self.processing_parameters.coords_crop[1]/2

        for i in range(self.num_projections): #self.num_projections
            raw = fsimage.load_projection_raw_pana(self.path.parent, i)

            #TODO alle dateien sauber packagen + RAW bilder dazu packen
            print(raw.dtype)
            arr = raw[round(y):round(y2),round(x):round(x2)]

            self.processing_stack.enable_all()
            #self.processing_stack.disable_all()
            #self.processing_stack.enable_list(['normalize_raw'])
            arr = self.processing_stack.execute(arr, auto=False)
            print(np.max(arr), np.min(arr))

            print(np.max(arr))
            print(arr.dtype)
            #imgplt = plt.imshow(arr,cmap="gray")
            #plt.show()
            #cv2.imwrite("1", arr)
            #arr *= 255
            #arr = np.uint8(arr)
           # cv2.imshow("2", arr)

            fsutil.save_np_as_img(arr, str(self.path.parent / Path("proj/" + str(self.processing_parameters.out_name) + ".tiff")), num=i)

    def get_resolution(self):
        """
        Calculate spatial resolution
        :return: resolution in degrees
        """
        return self.scan_max_angle / self.num_projections

    def get_reached_angles_rad(self):
        """
        Convert all reached projection angles to radians
        :return: list of angles in radians
        """
        return [(val/180.0)*np.pi for val in self.reached_angles]


    def to_dict(self, dic=None):
        """
        Convert all scan data to a python dict
        :param dic: destination dict
        :return: dict filled with all scan data
        """
        if dic is None:
            dic = {}

        dic['num_projections'] = self.num_projections
        dic['max_angle'] = self.scan_max_angle
        dic['reached_angles'] = self.reached_angles

        fsutil.obj_to_dict(self.scan_parameters, "scan_parameters", dic)
        fsutil.obj_to_dict(self.reconstruction_parameters, "reconstruction_parameters", dic)
        fsutil.obj_to_dict(self.processing_parameters, "processing_parameters", dic)
        self.processing_stack.to_dict("processing_stack", dic)
        return dic

    def from_dict(self, dic):
        """
        Load scan data from dict
        :param dic: source dict
        """
        self.num_projections = dic.get('num_projections', 0)
        self.scan_max_angle = dic.get('max_angle', 180)
        self.reached_angles = dic.get('reached_angles', [])

        fsutil.dict_to_obj(self.scan_parameters, "scan_parameters", dic)
        fsutil.dict_to_obj(self.reconstruction_parameters, "reconstruction_parameters", dic)
        fsutil.dict_to_obj(self.processing_parameters, "processing_parameters", dic)
        self.processing_stack.from_dict("processing_stack", dic)

class CTScanContext:
    curr_scan: CTScan
    """
    Handle to reference all the objects needed to run a scan. Stores all the state information and gives access to the hardware devices
    """

    def __init__(self):
        self.dev_detector = None
        self.dev_xray = None
        self.curr_scan = None

        self.locked = False

