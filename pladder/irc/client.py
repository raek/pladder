from contextlib import AbstractContextManager, ExitStack
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


class Hook(AbstractContextManager):
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


class Client(ExitStack):
    def __init__(self, config):
        super().__init__()
        self._config = config
        self._hooks = []
        self._conn = None
        self._messages = self._messages_with_default_handling()
        self._commands = {}
        self._msgsplitter = {}
        self._headerlen = 0

    # Public API

    def install_hook(self, hook_ctor):
        hook = self.enter_context(hook_ctor(self._config, self))
        self._hooks.append(hook)

    def run(self):
        assert self._conn is None
        self._update_status(f"Connecting to {self._config.host}:{self._config.port}")
        self._conn = self.enter_context(MessageConnection(self._config.host, self._config.port))
        self._settle_in()

    # Internal helper methods

    def _messages_with_default_handling(self):
        for message in self._conn.recv_messages():
            for hook in self._hooks:
                hook.on_message_received()
            if message.command == "PING":
                self._handle_ping(message)
            elif message.command == "PRIVMSG":
                self._handle_privmsg(message)
            else:
                yield message

    def _await_message(self, command=None, *, sender=None, sender_nick=None, params=None):
        for message in self._messages:
            if command is not None and message.command != command:
                continue
            if sender is not None and message.sender != sender:
                continue
            if sender_nick is not None and message.sender.nick != sender_nick:
                continue
            if params is not None and message.params != params:
                continue
            return message

    def _update_status(self, s):
        logger.info(s)
        for hook in self._hooks:
            hook.on_status(s)

    # Messages that should always be handled: the reactive part of client

    def _handle_ping(self, message):
        self._conn.send("PONG", *message.params)

    def _handle_privmsg(self, message):
        target, text = message.params
        if target[0] in "&#+!":
            reply_to = target
        else:
            reply_to = message.sender.nick
        timestamp = datetime.now(timezone.utc).timestamp()
        reply = None
        command = None
        msgpart = None
        if text.startswith(self._config.trigger_prefix):
            logger.info("{} -> {} : {}".format(message.sender.nick, target, text))
            timestamp = datetime.now(timezone.utc).timestamp()
            text_without_prefix = text[len(self._config.trigger_prefix):]
            for hook in self._hooks:
                reply = hook.on_trigger(timestamp, reply_to, message.sender, text_without_prefix) or reply
        if reply and reply['text']:
            self._commands[reply_to] = reply['command']
            self._msgsplitter[reply_to] = message_generator("PRIVMSG",
                                                            reply_to,
                                                            self._config.reply_prefix,
                                                            reply['text'],
                                                            self._headerlen)
            command = reply['command']
            msgpart = next(self._msgsplitter[reply_to])
        if text == "more":
            try:
                command = self._commands[reply_to]
                msgpart = next(self._msgsplitter[reply_to])
            except KeyError:
                pass
            except StopIteration:
                del self._commands[reply_to]
                del self._msgsplitter[reply_to]
            else:
                logger.info("{} -> {} : {}".format(message.sender.nick, target, text))
        if msgpart:
            logger.info("-> {} : {}".format(reply_to, msgpart[msgpart.find(":")+1:]))
            if command != 'searchlog':
                for hook in self._hooks:
                    hook.on_privmsg(timestamp, reply_to, message.sender, text)
                    hook.on_send_privmsg(timestamp, reply_to,
                                         self._config.nick, msgpart[msgpart.find(":")+1:])
            self._conn.send(msgpart)
        else:
            for hook in self._hooks:
                hook.on_privmsg(timestamp, reply_to, message.sender, text)

    # The "phases" of connecting: the active part of the client

    def _settle_in(self):
        self._choose_nick()
        if self._config.auth:
            self._authenticate()
        if self._config.user_mode:
            self._set_user_mode()
        if self._config.channels:
            self._join_channels()
        self._whois_self()
        self._ready()

    def _choose_nick(self):
        self._update_status(f'Using nick "{self._config.nick}" and realname "{self._config.realname}"')
        self._conn.send("NICK", self._config.nick)
        self._conn.send("USER", self._config.nick, "0", "*", self._config.realname)
        self._await_message("001")

    def _authenticate(self):
        if self._config.auth.system == "Q":
            self._update_status(f"Authenticating with Q as {self._config.auth.username}")
            self._conn.send("PRIVMSG", "Q@CServe.quakenet.org",
                            f"AUTH {self._config.auth.username} {self._config.auth.password}")
            q_bot = Sender("Q", "TheQBot", "CServe.quakenet.org")
            message = self._await_message("NOTICE", sender=q_bot)
            if message.params != [self._config.nick, f"You are now logged in as {self._config.auth.username}."]:
                raise Exception("Authentication failed: " + message.params[1])
        else:
            Exception("Unknown authentication system: " + self._config.auth.system)

    def _set_user_mode(self):
        self._update_status(f"Setting user mode to {self._config.user_mode}")
        self._conn.send("MODE", self._config.nick, self._config.user_mode)
        self._await_message("MODE", params=[self._config.nick, self._config.user_mode])

    def _join_channels(self):
        self._update_status("Joining channels: {}".format(", ".join(self._config.channels)))
        channels_to_join = set(self._config.channels)
        joined_channels = set()
        for channel in self._config.channels:
            self._conn.send("JOIN", channel)
        while joined_channels != channels_to_join:
            message = self._await_message("JOIN", sender_nick=self._config.nick)
            channel = message.params[0]
            logger.info(f"Joined channel: {channel}")
            if channel in channels_to_join:
                joined_channels.add(channel)
                self._update_status("Joined {} of {} channels: {}".format(len(joined_channels),
                                                                          len(channels_to_join),
                                                                          ", ".join(sorted(joined_channels))))

    def _whois_self(self):
        self._conn.send("WHOIS", self._config.nick)
        message = self._await_message("311")
        username = message.params[2]
        hostname = message.params[3]
        header = f":{self._config.nick}!{username}@{hostname} "
        headerlen = len(header.encode("utf-8"))
        self._headerlen = headerlen
        logger.info(f"Whois {self._config.nick}: {username}@{hostname} - length {headerlen}")

    def _ready(self):
        self._update_status("Joined all channels: {}".format(", ".join(self._config.channels)))
        for hook in self._hooks:
            hook.on_ready()
        while True:
            self._await_message()
