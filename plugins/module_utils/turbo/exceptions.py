class EmbeddedModuleBaseException(Exception):
    def __init__(self, msg):
        self._message = msg

    def get_message(self):
        return str(self._message)


class EmbeddedModuleFailure(EmbeddedModuleBaseException):
    def __init__(self, msg):
        super(EmbeddedModuleFailure, self).__init__(msg=msg)


class EmbeddedModuleUnexpectedFailure(EmbeddedModuleBaseException):
    def __init__(self, msg):
        super(EmbeddedModuleUnexpectedFailure, self).__init__(msg=msg)


class EmbeddedModuleSuccess(Exception):
    def __init__(self, **kwargs):
        self.kwargs = kwargs
