class EmbeddedModuleFailure(Exception):
    def __init__(self, msg):
        self._message = msg

    def get_message(self):
        return repr(self._message)

    def __repr__(self):
        return self.get_message()

    def __str__(self):
        return self.get_message()


class EmbeddedModuleUnexpectedFailure(Exception):
    def __init__(self, msg):
        self._message = msg

    def get_message(self):
        return repr(self._message)

    def __repr__(self):
        return self.get_message()

    def __str__(self):
        return self.get_message()


class EmbeddedModuleSuccess(Exception):
    def __init__(self, **kwargs):
        self.kwargs = kwargs
