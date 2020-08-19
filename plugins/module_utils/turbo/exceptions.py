class EmbeddedModuleFailure(Exception):
    def __init__(self, message):
        self._message = message

    def get_message(self):
        return repr(self._message)


class EmbeddedModuleSuccess(Exception):
    def __init__(self, **kwargs):
        self.kwargs = kwargs
