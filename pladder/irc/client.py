from collections import namedtuple
from datetime import datetime, timezone
import logging
import socket

from pladder.irc.message import MessageConnection


logger = logging.getLogger("pladder.irc")


Config = namedtuple("Config", "network, host, port, nick, realname, auth, user_mode, channels, trigger_prefix, reply_prefix")


class Hooks:
    def on_ready(self):
        pass

    def on_ping(self):
        pass

    def on_status(self, s):
        pass

    def on_trigger(self, timestamp, network, channel, sender, text):
        pass


def run_client(config, hooks):
    def update_status(s):
        logger.info(s)
        hooks.on_status(s)
    update_status("Connecting to {host}:{port}".format(**config._asdict()))
    with MessageConnection(config.host, config.port) as conn:
        update_status("Using nick \"{nick}\" and realname \"{realname}\"".format(**config._asdict()))
        conn.send("NICK", config.nick)
        conn.send("USER", config.nick, "0", "*", config.realname)
        channels_to_join = set(config.channels)
        joined_channels = set()
        while True:
            message = conn.recv_message()
            if message.command == "001":
                if config.auth:
                    conn.send("AUTH", config.nick, config.auth)
                if config.user_mode:
                    conn.send("MODE", config.nick, config.user_mode)
                update_status("Joining channels: {}".format(", ".join(config.channels)))
                for channel in config.channels:
                    conn.send("JOIN", channel)
                hooks.on_ready()
            elif message.command == "PING":
                conn.send("PONG", *message.params)
                hooks.on_ping()
            elif message.command == "JOIN":
                if message.sender.nick == config.nick:
                    channel = message.params[0]
                    logger.info("Joined channel: {}".format(channel))
                    if channel in channels_to_join:
                        joined_channels.add(channel)
                        update_status("Joined {} of {} channels: {}".format(len(joined_channels), len(channels_to_join), ", ".join(sorted(joined_channels))))
            elif message.command == "PRIVMSG":
                target, text = message.params
                if text.startswith(config.trigger_prefix):
                    if target[0] in "&#+!":
                        reply_to = target
                    else:
                        reply_to = message.sender.nick
                    logger.info("{} -> {} : {}".format(message.sender.nick, target, text))
                    timestamp = datetime.now(timezone.utc).timestamp()
                    text_without_prefix = text[len(config.trigger_prefix):]
                    reply = hooks.on_trigger(timestamp, config.network, reply_to, message.sender, text_without_prefix)
                    if reply:
                        full_reply = config.reply_prefix + reply
                        logger.info("-> {} : {}".format(reply_to, full_reply))
                        conn.send("PRIVMSG", reply_to, full_reply)
