from contextlib import ExitStack

class Plugin(ExitStack):
    def register(self, bot):
        raise NotImplementedError()
