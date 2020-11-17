class EmbeddedModuleFailure(Exception):
    def __init__(self, msg, **kwargs):
        self._message = msg
        if kwargs:
            self._message += str(kwargs)

    def get_message(self):
        return repr(self._message)


class EmbeddedModuleUnexpectedFailure(Exception):
    def __init__(self, msg):
        self._message = msg

    def get_message(self):
        return repr(self._message)


class EmbeddedModuleSuccess(Exception):
    def __init__(self, **kwargs):
        self.kwargs = kwargs
