from collections import namedtuple
from datetime import datetime, timezone
import logging
import socket

from pladder.irc.message import MessageConnection, Sender, message_generator


logger = logging.getLogger("pladder.irc")


Config = namedtuple("Config", "network, host, port, nick, realname, auth, user_mode, channels, trigger_prefix, reply_prefix")
AuthConfig = namedtuple("AuthConfig", "system, username, password")

msgsplitter = {}
commands = {}

class Hooks:
    def on_ready(self):
        pass

    def on_ping(self):
        pass

    def on_status(self, s):
        pass

    def on_trigger(self, timestamp, network, channel, sender, text):
        pass

    def on_privmsg(self, timestamp, network, channel, sender, text):
        pass

    def on_send_privmsg(self, timestamp, network, channel, sender, text):
        pass


def run_client(config, hooks):
    def update_status(s):
        logger.info(s)
        hooks.on_status(s)
    update_status(f"Connecting to {config.host}:{config.port}")
    with MessageConnection(config.host, config.port) as conn:

        def handle_ping(message):
            conn.send("PONG", *message.params)
            hooks.on_ping()

        def handle_privmsg(message):
            target, text = message.params
            if target[0] in "&#+!":
                reply_to = target
            else:
                reply_to = message.sender.nick
            timestamp = datetime.now(timezone.utc).timestamp()
            reply = None
            command = None
            msgpart = None
            if text.startswith(config.trigger_prefix):
                logger.info("{} -> {} : {}".format(message.sender.nick, target, text))
                timestamp = datetime.now(timezone.utc).timestamp()
                text_without_prefix = text[len(config.trigger_prefix):]
                reply = hooks.on_trigger(timestamp, config.network, reply_to, message.sender, text_without_prefix)
            if reply:
                commands[reply_to] = reply['command']
                msgsplitter[reply_to] = message_generator("PRIVMSG", reply_to, config.reply_prefix, reply['text'], conn.headerlen)
                command = reply['command']
                msgpart = next(msgsplitter[reply_to])
            if text == "more":
                try:
                    command = commands[reply_to]
                    msgpart = next(msgsplitter[reply_to])
                except:
                    pass
                else:
                    logger.info("{} -> {} : {}".format(message.sender.nick, target, text))
            if msgpart:
                logger.info("-> {} : {}".format(reply_to, msgpart[msgpart.find(":")+1:]))
                if command != 'searchlog':
                    hooks.on_privmsg(timestamp, config.network, reply_to, message.sender, text)
                    hooks.on_send_privmsg(timestamp, config.network, reply_to, config.nick, msgpart[msgpart.find(":")+1:])
                conn.send(msgpart)
            else:
                hooks.on_privmsg(timestamp, config.network, reply_to, message.sender, text)

        def messages_with_default_handling():
            for message in conn.recv_messages():
                if message.command == "PING":
                    handle_ping(message)
                elif message.command == "PRIVMSG":
                    handle_privmsg(message)
                else:
                    yield message

        messages = messages_with_default_handling()

        def choose_nick():
            update_status(f'Using nick "{config.nick}" and realname "{config.realname}"')
            conn.send("NICK", config.nick)
            conn.send("USER", config.nick, "0", "*", config.realname)
            for message in messages:
                if message.command == "001":
                    break

        def authenticate():
            if config.auth.system == "Q":
                update_status(f"Authenticating with Q as {config.auth.username}")
                conn.send("PRIVMSG", "Q@CServe.quakenet.org", f"AUTH {config.auth.username} {config.auth.password}")
                q_bot = Sender("Q", "TheQBot", "CServe.quakenet.org")
                for message in messages:
                    if message.command == "NOTICE" and message.sender == q_bot:
                        if message.params == [config.nick, f"You are now logged in as {config.auth.username}."]:
                            break
                        else:
                            raise Exception("Authentication failed: " + message.params[1])
            else:
                Exception("Unknown authentication system: " + config.auth.system)

        def set_user_mode():
            update_status(f"Setting user mode to {config.user_mode}")
            conn.send("MODE", config.nick, config.user_mode)
            for message in messages:
                if message.command == "MODE" and message.params == [config.nick, config.user_mode]:
                    break

        def join_channels():
            update_status("Joining channels: {}".format(", ".join(config.channels)))
            channels_to_join = set(config.channels)
            joined_channels = set()
            for channel in config.channels:
                conn.send("JOIN", channel)
            for message in messages:
                if message.command == "JOIN":
                    if message.sender.nick == config.nick:
                        channel = message.params[0]
                        logger.info(f"Joined channel: {channel}")
                        if channel in channels_to_join:
                            joined_channels.add(channel)
                            update_status("Joined {} of {} channels: {}".format(len(joined_channels),
                                                                                len(channels_to_join),
                                                                                ", ".join(sorted(joined_channels))))
                            if joined_channels == channels_to_join:
                                break
        
        def whois_self():
            conn.send("WHOIS", config.nick)
            for message in messages:
                if message.command == "311":
                    conn.username = message.params[2]
                    conn.hostname = message.params[3]
                    conn.header = f":{config.nick}!{conn.username}@{conn.hostname} "
                    conn.headerlen = len(conn.header.encode("utf-8"))
                    logger.info(f"Whois {config.nick}: {conn.username}@{conn.hostname} - length {conn.headerlen}")
                    break


        def run():
            update_status("Joined all channels: {}".format(", ".join(config.channels)))
            hooks.on_ready()
            for message in messages:
                pass

        choose_nick()
        if config.auth:
            authenticate()
        if config.user_mode:
            set_user_mode()
        if config.channels:
            join_channels()
        whois_self()
        run()
