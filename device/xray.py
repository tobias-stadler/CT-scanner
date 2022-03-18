import logging


class CTXRay:
    """
    Abstraction of underlying network layer to interface with the X-ray/positioning device
    """
    def __init__(self):
        self.dlogger = logging.getLogger("CTXrayDevice")
        self.dlogger.info("created")
        self.listeners = [CTXRayListenerDefault()]

    def add_listener(self, newlistener):
        self.listeners.append(newlistener)

    def remove_listener(self, remlistener):
        if remlistener in self.listeners:
            self.listeners.remove(remlistener)
        else:
            pass
            #self.dlogger.warning("Tried to remove a listener that didn't exist!")

    def set_position(self, angle, token):
        """
        Request move
        :param angle: requested angle in degrees
        :param token: sequencing number to match requests and answers
        :return:
        """
        pass

    # Currently unimplemented
    def request_position(self):
        """
        Request status message that contains the current position
        """
        pass

    def is_ready(self):
        """
        :return: X-ray status
        """
        return False

class CTXRayListener:

    """
    Interface to receive status information from X-ray device
    """
    def on_xray_position_done(self, angle, token):
        pass

    def on_xray_status(self, angle):
        pass

class CTXRayListenerDefault(CTXRayListener):

    """
    Default implementation of CTXrayListener that prints debug information to the console
    """

    def on_xray_position_done(self, angle, token):
        print("XRay, Done: ", angle)

    def on_xray_status(self, angle):
        #print("XRay, Status: ", angle)
        pass
