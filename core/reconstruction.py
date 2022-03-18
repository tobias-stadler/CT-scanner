from pathlib import Path

import numpy as np

from core import fsutil, scandata


class ReconstructionProvider:
    """
    Interface for implementing different reconstruction algorithms
    """
    def __init__(self, scan : scandata.CTScan):
        self.scan = scan

    def reconstruct(self):
        pass


class ReconAstra3DCone(ReconstructionProvider):

    """
    Implementation of 3D cone beam reconstruction using ASTRA toolbox
    """

    def __init__(self, scan : scandata.CTScan):
        super().__init__(scan)

    def reconstruct(self):
        #removed due to GPL
        pass