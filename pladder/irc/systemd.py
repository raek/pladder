import logging

from systemd.journal import JournalHandler  # type: ignore
from systemd.daemon import notify  # type: ignore


def set_up_systemd(config, hooks_base_class):

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(JournalHandler(SYSLOG_IDENTIFIER="pladder-irc"))

    class SystemdHooks(hooks_base_class):
        def on_ready(self):
            super().on_ready()
            notify("READY=1")

        def on_message_received(self):
            super().on_message_received()
            notify("WATCHDOG=1")

        def on_privmsg(self, timestamp, channel, sender, text):
            super().on_privmsg(timestamp, channel, sender, text)
            notify("WATCHDOG=1")

        def on_status(self, status):
            super().on_status(status)
            notify("STATUS=" + status)

    return SystemdHooks
