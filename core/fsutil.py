from pathlib import Path

import PIL
import cv2
import numpy as np


def construct_path_numbered(path_str, num):
    """
    Create path containing a base string and a 4 digit number
    :param path_str: base path name
    :param num: number to be concatenated
    :return: constructed file path
    """
    path = Path(path_str)

    if num is not None and type(num) is int and 0 <= num < 10000:
        file_path = path.parent / ('%s%04d%s' % (path.stem, num, path.suffix))
    else:
        file_path = path

    return file_path

def load_image_downsample(fp, downsample=None):
    print(fp)
    im = cv2.imread(str(fp), cv2.IMREAD_ANYDEPTH)

    if downsample:
        w = round(im.shape[1] / downsample)
        h = round(im.shape[0] / downsample)
        sz = (w, h)
        im = cv2.resize(im, sz, interpolation=cv2.INTER_LANCZOS4)
        #im = PIL.Image.open(fp)
        #w, h = im.size
        #im = im.resize((round(w / downsample), round(h / downsample)), PIL.Image.ANTIALIAS)
    return im


def save_np_as_img(np_arr, path_str, cutaxis=0, num=None):
    """
    Convert numpy array (2D or 3D )to one/multiple PIL image(s) and save to disk
    :param np_arr: input numpy array
    :param path_str: output path
    :param cutaxis: direction of axis that is used to slice 3D data into 2D images
    :param num: number added to export name if only one image should be exported
    """
    arrshape = np_arr.shape

    path = Path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)

    if cutaxis not in range(0, 3):
        raise Exception("cutaxis out of bounds")

    #convert to 16bit uint
    np_arr *= np.iinfo("uint16").max
    np_arr = np_arr.astype("uint16")

    if len(arrshape) == 2:
        im = PIL.Image.fromarray(np_arr)
        file_path = construct_path_numbered(path_str, num)
        #im.save(file_path)
        cv2.imwrite(str(file_path), np_arr)
    elif len(arrshape) == 3:
        for i in range(arrshape[cutaxis]):
            slc = [slice(None)] * np_arr.ndim
            slc[cutaxis] = i
            im_arr = np_arr[tuple(slc)]
            im = PIL.Image.fromarray(im_arr)
            file_path = construct_path_numbered(path_str, num=i)
            cv2.imwrite(str(file_path), im_arr)

            #im.save(file_path)

    else:
        raise Exception("Numpy Array doesn't have the right shape to be saved as an image")

def load_img_as_np(path_str, stackaxis=0, num=None, downsample=None):
    """
    Load  PIL images from disk interpret them as 2D/3D data and convert to a numpy array
    :param path_str: path string of input files
    :param stackaxis: direction of axis that is used to stack 2D images to convert to a 3D array
    :param num: optional number of file to be loaded if only one should be imported instead of an array of images
    :return: numpy array of loaded data
    """
    path = construct_path_numbered(path_str, num)

    if stackaxis not in range(0, 3):
        raise Exception("stackaxis out of bounds")

    if path.is_file():
        im = load_image_downsample(path, downsample)
        return np.array(im)

    elif path.parent.is_dir() and (num is None):
        c = 0
        while True:
            test_path = construct_path_numbered(path, num=c)
            if not test_path.is_file():
                break
            c += 1

        hero_path = construct_path_numbered(path, num=0)
        if not hero_path.is_file() or c <= 0:
            raise Exception("No 3D image array found with path %s", path)

        hero_im = load_image_downsample(hero_path, downsample)
        hero_arr = np.array(hero_im)

        sz = [hero_arr.shape[0], hero_arr.shape[1]]
        sz.insert(stackaxis, c)

        raw_arr = np.zeros(tuple(sz), dtype="float32")
        for i in range(c):
            slc = [slice(None)] * raw_arr.ndim
            slc[stackaxis] = i
            #construct_path_numbered(path, num=i)
            im = load_image_downsample(construct_path_numbered(path, num=i), downsample)

            raw_arr[tuple(slc)] = im

        return raw_arr

    else:
        raise Exception("Failed loading image array: No such filearray exists")



def obj_to_dict(obj, name, dic=None):
    """
    Convert python object to dict and insert into python dict
    :param obj: source object
    :param name: dictionary key
    :param dic: destination dict. If None a new dict will be allocated
    :return: dict filled with data
    """
    if dic is None:
        dic = {}

    dic[name] = obj.__dict__
    return dic


def dict_to_obj(obj, name, dic):
    """
    Insert data contained in a dict as attributes into python object
    :param obj: destination object
    :param name: dict key to be used
    :param dic: source dictionary
    :return: destination object filled with data
    """
    try:
        for key in dic[name]:
            try:
                setattr(obj, key, dic[name][key])
                #print(name, key)
            except Exception as e:
                print("dict_to_obj warning: " + str(e))
    except Exception as e:
        print("dict_to_obj warning: " + str(e))

    return obj