class PluginError(Exception):
    pass


class PluginLoadError(PluginError):
    """The plugin could not load due to error in environment (missing dependencies, config files, etc)"""
    pass
