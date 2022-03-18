import logging
from gui import main

import numpy as np
from core import fs

mpl_logger = logging.getLogger("matplotlib")

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logging.info("Starting GUI")
    mpl_logger.setLevel(logging.WARNING)

    np.set_printoptions(threshold=np.inf)

    frame = main.MainFrame()
    frame.start()

