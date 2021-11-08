import logging
from time import sleep

from pladder.threading import background_thread


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
    <method name="GetConfig">
      <arg direction="out" name="return" type="a{ss}" />
    </method>
    <method name="SendMessage">
      <arg direction="in" name="channel" type="s" />
      <arg direction="in" name="text" type="s" />
      <arg direction="out" name="return" type="s" />
    </method>
    <method name="GetChannels">
      <arg direction="out" name="channels" type="as" />
    </method>
    <method name="GetChannelUsers">
      <arg direction="in" name="channel" type="s" />
      <arg direction="out" name="channels" type="as" />
    </method>
    <method name="TriggerReload">
      <arg direction="out" name="triggered" type="b" />
    </method>
    <signal name="ReloadComplete">
    </signal>
  </interface>
</node>
"""


PLADDER_WEB_API_XML = """
<node>
  <interface name="se.raek.PladderWebApi">
    <method name="CreateToken">
      <arg direction="in" name="token_name" type="s" />
      <arg direction="in" name="creator_network" type="s" />
      <arg direction="in" name="creator_user" type="s" />
      <arg direction="out" name="ok" type="b" />
      <arg direction="out" name="secret" type="s" />
    </method>
    <method name="GetToken">
      <arg direction="in" name="token_name" type="s" />
      <arg direction="out" name="ok" type="b" />
      <arg direction="out" name="used" type="i" />
      <arg direction="out" name="use_count" type="i" />
      <arg direction="out" name="created" type="i" />
      <arg direction="out" name="creator_network" type="s" />
      <arg direction="out" name="creator_user" type="s" />
    </method>
    <method name="ListTokens">
      <arg direction="out" name="token_names" type="as" />
    </method>
    <method name="DeleteToken">w
      <arg direction="in" name="token_name" type="s" />
      <arg direction="out" name="ok" type="b" />
    </method>
  </interface>
</node>
"""


logger = logging.getLogger("pladder.dbus")


class RetryProxy:
    def __init__(self, bus, object_name):
        self.bus = bus
        self.object_name = object_name
        self.obj = None

    def __getattr__(self, name):
        def wrapper(*args, on_error=None, **kwargs):
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


def dbus_loop():
    from gi.repository import GLib  # type: ignore

    loop = GLib.MainLoop()
    sync_timeout = 10

    def await_loop_running():
        for _ in range(sync_timeout ** 10):
            if loop.is_running():
                return True
            else:
                sleep(0.1)
        return False

    return background_thread("DBus main loop",
                             work_fn=loop.run,
                             sync_fn=await_loop_running,
                             stop_fn=loop.quit)
