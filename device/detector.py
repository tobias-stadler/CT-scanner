import logging

class CTDetector:
    """
    Abstraction of underlying network layer to interface with the detector
    """
    def __init__(self):
        self.dlogger = logging.getLogger("CTDetectorDevice")
        self.dlogger.info("created")
        self.listeners = [CTDetectorListenerDefault()]

    def add_listener(self, newlistener):
        self.listeners.append(newlistener)

    def remove_listener(self, remlistener):
        if remlistener in self.listeners:
            self.listeners.remove(remlistener)
        else:
            self.dlogger.warning("Tried to remove a listener that didn't exist!")

    def capture_raw(self, shutterlen, exposure, focuslen, token):
        """
        Send request to capture RAW image. All values in milliseconds!
        :param shutterlen: Android: camera ISO; DSLM: duration that shutter is held down
        :param exposure: Exposure time
        :param focuslen: Android: focus distance; DSLM: duration that auto focus is active
        :param token: sequencing number to match requests and answers
        """
        pass

    # Would have only been used with Android
    # def capture_test(self, shutterlen, exposure, focuslen, token):
    #     pass

    def is_ready(self):
        """
        :return: Detector status
        """
        return False

class CTDetectorListener:
   """
   Interface to receive status information from the detector
   """
   def on_detector_raw(self, data, stride_pixel, stride_row, sensor, token):
       pass

   # Would have only been used with Android
   def on_detector_test(self, data, token):
       pass


class CTDetectorListenerDefault(CTDetectorListener):
    """
    Default implementation of CTDetectorListener that prints debug information to the console
    """

    # Would have only been used with Android
    # def on_detector_test(self, data, token):
    #     print("Photo, jpeg")

    def on_detector_raw(self, data, stride_pixel, stride_row, sensor, token):
        print("Photo, raw")