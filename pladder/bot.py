from gi.repository import GLib
from pydbus import SessionBus


def main():
    pladder_bot = PladderBot()
    bus = SessionBus()
    bus.publish("se.raek.PladderBot", pladder_bot)
    loop = GLib.MainLoop()
    loop.run()


class PladderBot:
    """
    <node>
      <interface name="se.raek.PladderBot">
        <method name="RunCommand">
          <arg direction="in" name="text" type="s" />
          <arg direction="out" name="return" type="s" />
        </method>
      </interface>
    </node>
    """

    def RunCommand(self, text):
        print(text)
        return text


if __name__ == "__main__":
    main()
