import rawpy
from pathlib import Path
import re
import shutil
from matplotlib import pyplot

# Default image folder names
path_raw = Path('raw')
path_projections = Path('projections')

"""
Functions for abstracting import and conversion of images files.
If a non-panasonic camera (RW2 format) is used, the file format must be changed here.
Internally libraw/rawpy is used to process the image files, so a list of supported cameras can be found here: 
https://www.libraw.org/supported-cameras (accessed 22.08.2020)
"""
file_format_extension = ".rw2" # CHANGE FILE FORMAT HERE


def load_projection_raw_pana(path_str, i):
    """
    Convert RW2 file (panasonic raw image format) to RGB color space with as little processing as possible and extract green color channel
    :param path_str: loaded scan folder path
    :param i: index of image to be loaded
    :return: numpy array of green color channel data
    """
    # List of supported cameras can be found here: https://www.libraw.org/supported-cameras (accessed 22.08.2020)
    with rawpy.imread(str(Path(path_str) / path_raw / Path(str(i) + file_format_extension))) as raw:
        # Disable all parameters that look like they might do things on their own: See https://letmaik.github.io/rawpy/api/rawpy.Params.html (accessed 03.06.2020)
        rgb = raw.postprocess(use_camera_wb=False, use_auto_wb=False, no_auto_scale=True, no_auto_bright=True, half_size=True,
                              gamma=(1,1), user_wb=[1.0, 1.0, 1.0, 1.0], bright=1.0, fbdd_noise_reduction=rawpy.FBDDNoiseReductionMode.Full,
                              output_color=rawpy.ColorSpace.raw, output_bps=16, demosaic_algorithm=rawpy.DemosaicAlgorithm.LINEAR)
        green = rgb[:, :, 1]
        return green

def import_images(path_str, img_path, img_count):
    """
    Import consecutive RW2 files (panasonic raw image format) or jpg files into scan folder
    :param path_str: loaded scan folder path
    :param img_path: path to first image of the sequence
    :param img_count: number of images to be imported
    """

    path = Path(img_path)
    m = re.search(r'\d+', path.name) # extract number from file name

    (Path(path_str) / path_raw).mkdir(parents=True, exist_ok=True)

    # Check if file extension is jpg or rw2. CHANGE IF OTHER FILE FORMATS ARE REQUIRED
    if m is None or (path.suffix.lower() != ".jpg" and path.suffix.lower() != file_format_extension):
        raise Exception("Invalid file format")

    cnt_begin = m.group()

    additional = 0
    skipped = False

    i = 0
    while i < img_count:
        src = path.parent / (path.stem.replace(cnt_begin, str(int(cnt_begin)+i+additional)) + str(path.suffix))
        dest = Path(path_str) / path_raw / (str(i) + str(path.suffix))

        print('----- %d/%d -----' % (i+1, img_count))
        print(src)
        print(dest)
        try:
            shutil.copy(src, dest)
            skipped = False
            i+=1
        except Exception as e:
            if skipped is True:
                print("DIDN'T EXIST: FAILED")
                print(e)
                raise FileNotFoundError()
            print("DIDN'T EXIST: SKIPPED")
            skipped = True
            additional += 9001
