from dasbus.loop import EventLoop
from dasbus.connection import SessionMessageBus


def main():
    loop = EventLoop()
    bus = SessionMessageBus()
    bus.publish_object("/se/raek/PladderBot", PladderBot())
    bus.register_service("se.raek.PladderBot")
    loop.run()


class PladderBot:
    __dbus_xml__ = """
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
