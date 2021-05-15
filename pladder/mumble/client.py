from contextlib import AbstractContextManager, ExitStack
from collections import namedtuple
from datetime import datetime, timezone
import logging
from threading import Lock

import pymumble_py3 as pymumble  # type: ignore


PLADDER_CLBK_PING_RECEIVED = "ping_received"


logger = logging.getLogger("pladder.mumble")


Config = namedtuple("Config", [
    "network",
    "host",
    "port",
    "password",
    "user",
    "certfile",
    "application",
    "trigger_prefix",
    "reply_prefix",
])


class Hook(AbstractContextManager):
    def on_ready(self):
        pass

    def on_ping_received(self):
        pass

    def on_status(self, s):
        pass

    def on_trigger(self, timestamp, channel, sender, text):
        pass


class Mumble(pymumble.Mumble):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.callbacks[PLADDER_CLBK_PING_RECEIVED] = None

    def ping_response(self, mess):
        super().ping_response(mess)
        self.callbacks(PLADDER_CLBK_PING_RECEIVED)


class Client(ExitStack):
    def __init__(self, config):
        super().__init__()
        self._config = config
        self._hooks = []
        self._pymumble = None
        self._send_lock = Lock()

    # Public API

    def install_hook(self, hook_ctor):
        hook = self.enter_context(hook_ctor(self._config, self))
        self._hooks.append(hook)

    def run(self):
        assert self._pymumble is None
        self._update_status(f"Connecting to {self._config.host}:{self._config.port}")
        self._pymumble = Mumble(host=self._config.host,
                                port=self._config.port,
                                user=self._config.user,
                                password=self._config.password,
                                certfile=self._config.certfile,
                                reconnect=False)
        self._pymumble.set_application_string(self._config.application)
        self._set_callback(pymumble.constants.PYMUMBLE_CLBK_CONNECTED, self._on_connected)
        self._set_callback(pymumble.constants.PYMUMBLE_CLBK_TEXTMESSAGERECEIVED, self._on_message_received)
        self._set_callback(PLADDER_CLBK_PING_RECEIVED, self._on_ping_received)
        self._pymumble.run()

    def _on_connected(self):
        for hook in self._hooks:
            hook.on_ready()
        self._update_status(f"Connected to {self._config.network}")

    def _on_message_received(self, mess):
        for channel_id in mess.channel_id:
            channel = self._pymumble.channels[channel_id]["name"]
            sender = self._pymumble.users[mess.actor]["name"]
            text = mess.message
            if not text.startswith(self._config.trigger_prefix):
                continue
            logger.info(f"{sender} -> {channel}: {text}")
            timestamp = datetime.now(timezone.utc).timestamp()
            text_without_prefix = text[len(self._config.trigger_prefix):]
            reply = None
            for hook in self._hooks:
                reply = hook.on_trigger(timestamp, channel, sender, text_without_prefix) or reply
            if not reply or not reply["text"]:
                continue
            reply_text = self._config.reply_prefix + reply["text"]
            logger.info(f"{self._config.user} -> {channel}: {reply_text}")
            self.send_message(channel, reply_text)

    def _on_ping_received(self):
        for hook in self._hooks:
            hook.on_ping_received()

    def send_message(self, channel_name, text):
        try:
            channel = self._pymumble.channels.find_by_name(channel_name)
            with self._send_lock:
                channel.send_text_message(text)
        except Exception as e:
            logger.error(e)

    def get_channels(self):
        try:
            root = self._pymumble.channels[0]
            return self._channel_names(root)
        except Exception as e:
            logger.error(e)
            return []

    def _channel_names(self, channel, output=None):
        if output is None:
            output = []
        output.append(channel["name"])
        for child in self._pymumble.channels.get_childs(channel):
            self._channel_names(child, output)
        return output

    def get_channel_users(self, channel):
        try:
            root = self._pymumble.channels.find_by_name(channel)
            return sorted(self._channel_users(root))
        except Exception as e:
            logger.error(e)
            return []

    def _channel_users(self, channel, output=None):
        if output is None:
            output = []
        self_id = channel["channel_id"]
        for user in self._pymumble.users.values():
            if user["channel_id"] == self_id:
                output.append(user["name"])
        for child in self._pymumble.channels.get_childs(channel):
            self._channel_users(child, output)
        return output

    # Internal helper methods

    def _update_status(self, s):
        logger.info(s)
        for hook in self._hooks:
            hook.on_status(s)

    def _set_callback(self, name, fn):
        self._pymumble.callbacks.set_callback(name, fn)
