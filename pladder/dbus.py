PLADDER_BOT_XML = """
<node>
  <interface name="se.raek.PladderBot">
    <method name="RunCommand">
      <arg direction="in" name="timestamp" type="u" />
      <arg direction="in" name="network" type="s" />
      <arg direction="in" name="channel" type="s" />
      <arg direction="in" name="nick" type="s" />
      <arg direction="in" name="text" type="s" />
      <arg direction="out" name="return" type="a{ss}" />
    </method>
  </interface>
</node>
"""


PLADDER_CONNECTOR_XML = """
<node>
  <interface name="se.raek.PladderConnector">
    <method name="SendMessage">
      <arg direction="in" name="channel" type="s" />
      <arg direction="in" name="text" type="s" />
    </method>
    <method name="GetChannels">
      <arg direction="out" name="channels" type="as" />
    </method>
  </interface>
</node>
"""


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
