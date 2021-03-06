from collections import namedtuple
from datetime import datetime, timezone
import logging

from pladder.irc.message import MessageConnection, Sender, message_generator


logger = logging.getLogger("pladder.irc")


Config = namedtuple("Config", [
    "network",
    "host",
    "port",
    "nick",
    "realname",
    "auth",
    "user_mode",
    "channels",
    "trigger_prefix",
    "reply_prefix"
])
AuthConfig = namedtuple("AuthConfig", "system, username, password")


class Hook:
    def on_ready(self):
        pass

    def on_message_received(self):
        pass

    def on_status(self, s):
        pass

    def on_trigger(self, timestamp, channel, sender, text):
        pass

    def on_privmsg(self, timestamp, channel, sender, text):
        pass

    def on_send_privmsg(self, timestamp, channel, sender, text):
        pass


def run_client(config, hooks):
    def update_status(s):
        logger.info(s)
        for hook in hooks:
            hook.on_status(s)
    update_status(f"Connecting to {config.host}:{config.port}")
    with MessageConnection(config.host, config.port) as conn:
        client = Client(config, hooks, conn, update_status)
        client.run_all()


class Client:
    def __init__(self, config, hooks, conn, update_status):
        self.config = config
        self.hooks = hooks
        self.conn = conn
        self.update_status = update_status
        self.messages = self._messages_with_default_handling()
        self.commands = {}
        self.msgsplitter = {}
        self.headerlen = 0

    def _messages_with_default_handling(self):
        for message in self.conn.recv_messages():
            for hook in self.hooks:
                hook.on_message_received()
            if message.command == "PING":
                self.handle_ping(message)
            elif message.command == "PRIVMSG":
                self.handle_privmsg(message)
            else:
                yield message

    def await_message(self, command=None, *, sender=None, sender_nick=None, params=None):
        for message in self.messages:
            if command is not None and message.command != command:
                continue
            if sender is not None and message.sender != sender:
                continue
            if sender_nick is not None and message.sender.nick != sender_nick:
                continue
            if params is not None and message.params != params:
                continue
            return message

    # Messages that should always be handled: the reactive part of client

    def handle_ping(self, message):
        self.conn.send("PONG", *message.params)

    def handle_privmsg(self, message):
        target, text = message.params
        if target[0] in "&#+!":
            reply_to = target
        else:
            reply_to = message.sender.nick
        timestamp = datetime.now(timezone.utc).timestamp()
        reply = None
        command = None
        msgpart = None
        if text.startswith(self.config.trigger_prefix):
            logger.info("{} -> {} : {}".format(message.sender.nick, target, text))
            timestamp = datetime.now(timezone.utc).timestamp()
            text_without_prefix = text[len(self.config.trigger_prefix):]
            for hook in self.hooks:
                reply = hook.on_trigger(timestamp, reply_to, message.sender, text_without_prefix) or reply
        if reply and reply['text']:
            self.commands[reply_to] = reply['command']
            self.msgsplitter[reply_to] = message_generator("PRIVMSG",
                                                           reply_to,
                                                           self.config.reply_prefix,
                                                           reply['text'],
                                                           self.headerlen)
            command = reply['command']
            msgpart = next(self.msgsplitter[reply_to])
        if text == "more":
            try:
                command = self.commands[reply_to]
                msgpart = next(self.msgsplitter[reply_to])
            except KeyError:
                pass
            except StopIteration:
                del self.commands[reply_to]
                del self.msgsplitter[reply_to]
            else:
                logger.info("{} -> {} : {}".format(message.sender.nick, target, text))
        if msgpart:
            logger.info("-> {} : {}".format(reply_to, msgpart[msgpart.find(":")+1:]))
            if command != 'searchlog':
                for hook in self.hooks:
                    hook.on_privmsg(timestamp, reply_to, message.sender, text)
                    hook.on_send_privmsg(timestamp, reply_to,
                                         self.config.nick, msgpart[msgpart.find(":")+1:])
            self.conn.send(msgpart)
        else:
            for hook in self.hooks:
                hook.on_privmsg(timestamp, reply_to, message.sender, text)

    # The "phases" of connecting: the active part of the client

    def run_all(self):
        self.choose_nick()
        if self.config.auth:
            self.authenticate()
        if self.config.user_mode:
            self.set_user_mode()
        if self.config.channels:
            self.join_channels()
        self.whois_self()
        self.run()

    def choose_nick(self):
        self.update_status(f'Using nick "{self.config.nick}" and realname "{self.config.realname}"')
        self.conn.send("NICK", self.config.nick)
        self.conn.send("USER", self.config.nick, "0", "*", self.config.realname)
        self.await_message("001")

    def authenticate(self):
        if self.config.auth.system == "Q":
            self.update_status(f"Authenticating with Q as {self.config.auth.username}")
            self.conn.send("PRIVMSG", "Q@CServe.quakenet.org",
                           f"AUTH {self.config.auth.username} {self.config.auth.password}")
            q_bot = Sender("Q", "TheQBot", "CServe.quakenet.org")
            message = self.await_message("NOTICE", sender=q_bot)
            if message.params != [self.config.nick, f"You are now logged in as {self.config.auth.username}."]:
                raise Exception("Authentication failed: " + message.params[1])
        else:
            Exception("Unknown authentication system: " + self.config.auth.system)

    def set_user_mode(self):
        self.update_status(f"Setting user mode to {self.config.user_mode}")
        self.conn.send("MODE", self.config.nick, self.config.user_mode)
        self.await_message("MODE", params=[self.config.nick, self.config.user_mode])

    def join_channels(self):
        self.update_status("Joining channels: {}".format(", ".join(self.config.channels)))
        channels_to_join = set(self.config.channels)
        joined_channels = set()
        for channel in self.config.channels:
            self.conn.send("JOIN", channel)
        while joined_channels != channels_to_join:
            message = self.await_message("JOIN", sender_nick=self.config.nick)
            channel = message.params[0]
            logger.info(f"Joined channel: {channel}")
            if channel in channels_to_join:
                joined_channels.add(channel)
                self.update_status("Joined {} of {} channels: {}".format(len(joined_channels),
                                                                         len(channels_to_join),
                                                                         ", ".join(sorted(joined_channels))))

    def whois_self(self):
        self.conn.send("WHOIS", self.config.nick)
        message = self.await_message("311")
        username = message.params[2]
        hostname = message.params[3]
        header = f":{self.config.nick}!{username}@{hostname} "
        headerlen = len(header.encode("utf-8"))
        self.headerlen = headerlen
        logger.info(f"Whois {self.config.nick}: {username}@{hostname} - length {headerlen}")

    def run(self):
        self.update_status("Joined all channels: {}".format(", ".join(self.config.channels)))
        for hook in self.hooks:
            hook.on_ready()
        while True:
            self.await_message()
