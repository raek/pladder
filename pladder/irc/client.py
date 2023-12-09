from contextlib import AbstractContextManager, ExitStack
from collections import namedtuple
from datetime import datetime, timezone
import logging
import re

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
Channel = namedtuple("Channel", "users")


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
    def __init__(self, config, inherited_fd=None):
        super().__init__()
        self._config = config
        self._inherited_fd = inherited_fd
        self._hooks = []
        self._conn = None
        self._messages = self._messages_with_default_handling()
        self._msgsplitter = {}
        self._headerlen = 0
        self._channels = {}
        self._partial_users = {}

    # Public API

    def install_hook(self, hook_ctor):
        hook = self.enter_context(hook_ctor(self._config, self))
        self._hooks.append(hook)

    def run(self):
        assert self._conn is None
        if self._inherited_fd:
            self._update_status(f"Inherited socket connected to {self._config.host}:{self._config.port}")
            self._conn = self.enter_context(MessageConnection(self._config.host, self._config.port, self._inherited_fd))
            self._resettle_in()
        else:
            self._update_status(f"Connecting to {self._config.host}:{self._config.port}")
            self._conn = self.enter_context(MessageConnection(self._config.host, self._config.port))
            self._settle_in()

    def send_message(self, target, text):
        timestamp = datetime.now(timezone.utc).timestamp()
        text = self._config.reply_prefix + text
        logger.info(f"-> {target} : {text}")
        for hook in self._hooks:
            hook.on_send_privmsg(timestamp, target, self._config.nick, text)
        try:
            self._conn.send("PRIVMSG", target, text)
        except Exception as e:
            logger.error(e)

    def get_channels(self):
        return sorted(self._channels.keys())

    def get_channel_users(self, channel):
        if channel in self._channels:
            return sorted(self._channels[channel].users)
        else:
            return []

    def trigger_detach(self):
        self._conn.trigger_detach()

    # Internal helper methods

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
        else:
            raise Exception("Connection closed")

    def _update_status(self, s):
        logger.info(s)
        for hook in self._hooks:
            hook.on_status(s)

    # Messages that should always be handled: the reactive part of client

    def _messages_with_default_handling(self):
        for message in self._conn.recv_messages():
            for hook in self._hooks:
                hook.on_message_received()
            if message.command == "PING":
                self._handle_ping(message)
            elif message.command == "PRIVMSG":
                self._handle_privmsg(message)
            elif message.command == "NICK":
                self._handle_nick(message)
            elif message.command == "JOIN":
                self._handle_join(message)
            elif message.command == "PART":
                self._handle_leave(message)
            elif message.command == "INVITE":
                self._handle_invite(message)
            elif message.command == "KICK":
                self._handle_kick(message)
            elif message.command == "QUIT":
                self._handle_quit(message)
            elif message.command == "353":
                self._handle_names_reply(message)
            elif message.command == "366":
                self._handle_end_of_names_reply(message)
            yield message

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
        msgpart = None
        if text.startswith(self._config.trigger_prefix):
            logger.info("{} -> {} : {}".format(message.sender.nick, target, text))
            timestamp = datetime.now(timezone.utc).timestamp()
            text_without_prefix = text[len(self._config.trigger_prefix):]
            for hook in self._hooks:
                reply = hook.on_trigger(timestamp, reply_to, message.sender, text_without_prefix) or reply
        if reply and reply['text']:
            self._msgsplitter[reply_to] = message_generator("PRIVMSG",
                                                            reply_to,
                                                            self._config.reply_prefix,
                                                            reply['text'],
                                                            self._headerlen)
            msgpart = next(self._msgsplitter[reply_to])
        if text.strip().lower() == "more":
            try:
                msgpart = next(self._msgsplitter[reply_to])
            except KeyError:
                pass
            except StopIteration:
                del self._msgsplitter[reply_to]
            else:
                logger.info("{} -> {} : {}".format(message.sender.nick, target, text))
        if msgpart:
            logger.info("-> {} : {}".format(reply_to, msgpart[msgpart.find(":")+1:]))
            for hook in self._hooks:
                hook.on_privmsg(timestamp, reply_to, message.sender, text)
                hook.on_send_privmsg(timestamp, reply_to,
                                     self._config.nick, msgpart[msgpart.find(":")+1:])
            self._conn.send(msgpart)
        else:
            for hook in self._hooks:
                hook.on_privmsg(timestamp, reply_to, message.sender, text)

    def _handle_nick(self, message):
        old_nick = message.sender.nick
        new_nick, = message.params
        for channel in self._channels.values():
            if old_nick in channel.users:
                channel.users.remove(old_nick)
                channel.users.add(new_nick)
        if old_nick == self._config.nick:
            logger.info(f"Changed nick from {old_nick} to {new_nick}")
            raise Exception("TODO: Implement support for changing own nick")
        else:
            logger.info(f"User changed nick from {old_nick} to {new_nick}")

    def _handle_join(self, message):
        nick = message.sender.nick
        channel, = message.params
        if nick == self._config.nick:
            self._channels[channel] = Channel(set())
            logger.info(f"Joined channel {channel}")
        else:
            if channel in self._channels:
                self._channels[channel].users.add(nick)
            logger.info(f"User {nick} joined channel {channel}")

    def _handle_leave(self, message):
        nick = message.sender.nick
        if len(message.params) == 1:
            channel, reason = message.params + [""]
        elif len(message.params) == 2:
            channel, reason = message.params
        else:
            raise ValueError(message)
        if nick == self._config.nick:
            if channel in self._channels:
                del self._channels[channel]
            logger.info(f"Left channel {channel}: {reason}")
        else:
            if channel in self._channels:
                users = self._channels[channel].users
                if nick in users:
                    users.remove(nick)
            logger.info(f"User {nick} left channel {channel}: {reason}")

    def _handle_invite(self, message):
        inviter = message.sender.nick
        invited, channel = message.params
        if invited == self._config.nick:
            self._clear_partial_users(channel)
            self._conn.send("JOIN", channel)
            logger.info(f"Was invited to channel {channel} by {inviter}, joining")
        else:
            logger.info(f"User {inviter} invited user {invited} to channel {channel}")

    def _handle_quit(self, message):
        nick = message.sender.nick
        if len(message.params) == 0:
            reason = ""
        elif len(message.params) == 1:
            reason = message.params[0]
        else:
            raise ValueError(message)
        if nick == self._config.nick:
            logger.info(f"Quit from server: {reason}")
            raise Exception("Got my own QUIT message from server")
        else:
            for channel in self._channels.values():
                if nick in channel.users:
                    channel.users.remove(nick)
            logger.info(f"User {nick} quit from server: {reason}")

    def _handle_kick(self, message):
        kicker = message.sender.nick
        if len(message.params) == 2:
            channel, kicked, reason = message.params + [""]
        elif len(message.params) == 3:
            channel, kicked, reason = message.params
        else:
            raise ValueError(message)
        if kicked == self._config.nick:
            if channel in self._channels:
                del self._channels[channel]
            logger.warning(f"Kicked from channel {channel} by {kicker}: {reason}")
        else:
            if channel in self._channels:
                users = self._channels[channel].users
                if kicked in users:
                    users.remove(kicked)
            logger.info(f"User {kicker} kicked user {kicked} from channel {channel}: {reason}")

    def _handle_names_reply(self, message):
        _, _, channel, nicks_string = message.params
        if channel not in self._channels:
            return
        users = [self._strip_nick_prefix(nick) for nick in nicks_string.split()]
        self._add_partial_users(channel, users)

    def _strip_nick_prefix(self, nick):
        """Remove non-alphanumeric character before nick (such as @)"""
        return re.sub(r"^\W", "", nick)

    def _handle_end_of_names_reply(self, message):
        channel = message.params[1]
        users = self._get_partial_users(channel)
        if channel in self._channels:
            self._channels[channel] = self._channels[channel]._replace(users=users)
        self._clear_partial_users(channel)
        logger.info(f"Channel {channel} users: " + ', '.join(sorted(users)))

    # The "phases" of connecting: the active part of the client

    def _settle_in(self):
        self._choose_nick()
        if self._config.auth:
            self._authenticate()
        if self._config.user_mode:
            self._set_user_mode()
        self._whois_self()
        if self._config.channels:
            self._join_channels()
        self._ready()

    def _resettle_in(self):
        self._whois_self()
        if self._config.channels:
            self._list_channel_nicks()
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
        for channel in self._config.channels:
            self._clear_partial_users(channel)
            self._conn.send("JOIN", channel)
        while channels_to_join - set(self._channels.keys()):
            message = self._await_message("JOIN", sender_nick=self._config.nick)
            channel = message.params[0]
            if channel in channels_to_join:
                n_joined = len(set(self._channels.keys()) & channels_to_join)
                n_total = len(channels_to_join)
                channel_list = ", ".join(sorted(set(self._channels.keys()) & channels_to_join))
                self._update_status(f"Joined {n_joined} of {n_total} channels: {channel_list}")

    def _list_channel_nicks(self):
        for channel in self._config.channels:
            self._clear_partial_users(channel)
            self._conn.send("NAMES", channel)

    def _clear_partial_users(self, channel):
        if channel in self._partial_users:
            del self._partial_users[channel]

    def _add_partial_users(self, channel, new_users):
        partial_users = self._partial_users.setdefault(channel, set())
        for new_user in new_users:
            partial_users.add(new_user)

    def _get_partial_users(self, channel):
        return self._partial_users.get(channel, set())

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
