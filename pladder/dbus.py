class RetryProxy:
    def __init__(self, bus, object_name):
        self.bus = bus
        self.object_name = object_name
        self.obj = None

    def __getattr__(self, name):
        def wrapper(*args, on_error, **kwargs):
            try:
                if not self.obj:
                    self.obj = self.bus.get(self.object_name)
                return getattr(self.obj, name)(*args, **kwargs)
            except Exception as e:
                if on_error is None:
                    raise
                else:
                    return on_error(e)
        return wrapper
