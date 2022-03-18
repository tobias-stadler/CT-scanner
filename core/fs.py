import json
from pathlib import Path

from core.scandata import CTScan

"""
Functions to load/save scan data
"""

# Default filesystem paths
path_main = Path('TEST')
path_ext = 'gct'


def load_ctscan(path_name):
    """
    Lodd ctscan from disk
    :param path_name: path of scan folder to be loaded
    :return: imported scan
    """
    dirpath = Path(path_name)
    if not dirpath.is_dir():
        raise FileNotFoundError()

    fpath = dirpath / Path('%s.%s' % (dirpath.name, path_ext))

    with open(fpath, 'r') as f:
        dic = json.load(f)
        nscan = CTScan(fpath.stem)
        nscan.from_dict(dic)
        nscan.path = fpath
        print("Scan Loaded")
        return nscan


def save_ctscan(scan: CTScan, dir_name):
    """
    Save ctscan to disk
    :param scan: ctscan to be saved
    :param dir_name: output directory path as string
    """
    if scan.name is None:
        return

    fpath = Path(dir_name) / Path(scan.name) / Path('%s.%s' % (scan.name, path_ext))
    fpath.parent.mkdir(parents=True, exist_ok=True)

    with open(fpath, 'w') as f:
        json.dump(scan.to_dict(), f, indent=4)
        scan.path = fpath


