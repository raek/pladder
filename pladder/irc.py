import argparse
import collections
import io
import logging
import re
import socket

import ftfy


logger = logging.getLogger("pladder.irc")


Message = collections.namedtuple("Message", "sender, command, params")
Sender = collections.namedtuple("Sender", "nick, user, host")
NO_SENDER = Sender(None, None, None)


def make_message(command, *params):
    return Message(NO_SENDER, command, params)


def parse_message(line):
    p = Parser(line)
    return p.parse()


class Parser:
    def __init__(self, line):
        self._rest = line

    def parse(self):
        sender = self._parse_sender()
        command = self._parse_word()
        params = self._parse_params()
        return Message(sender, command, params)

    def _parse_sender(self):
        if self._try_parse_colon():
            sender = self._parse_word()
            nick_and_user, host = self._split_off_optional_suffix(sender, "@")
            nick, user = self._split_off_optional_suffix(nick_and_user, "!")
            return Sender(nick, user, host)
        else:
            return NO_SENDER

    def _parse_params(self):
        params = []
        while self._rest:
            if self._rest.startswith(":"):
                param = self._rest[1:]
                self._rest = ""
            else:
                param = self._parse_word()
            params.append(param)
        return params

    def _try_parse_colon(self):
        if self._rest.startswith(":"):
            self._rest = self._rest[1:]
            return True
        else:
            return False

    def _parse_word(self):
        l = self._rest.find(" ")
        if l == -1:
            word = self._rest
            self._rest = ""
        else:
            word = self._rest[:l]
            self._rest = self._rest[l+1:]
        return word

    def _split_off_optional_suffix(self, s, delimiter):
        l = s.find(delimiter)
        if l == -1:
            return s, None
        else:
            return s[:l], s[l+1:]


def format_message(msg):
    result = ""
    if msg.sender.nick:
        result += ":" + msg.sender.nick
        if msg.sender.user:
            result += "!" + msg.sender.user
        if msg.sender.host:
            result += "@" + msg.sender.host
        result += " "
    result += msg.command
    if msg.params:
        for param in msg.params[:-1]:
            result += " " + param
        result += " :" + msg.params[-1]
    return result


class MessageConnection:
    RECV_SIZE = 4096

    def __init__(self, host, port):
        self._recv_buffer = b""
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect((host, port))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def close(self):
        self._socket.close()

    def recv_message(self):
        line_bytes = self._recv_line()
        line = self._magically_decode_utf8(line_bytes)
        logger.debug("--> %s", line)
        message = parse_message(line)
        return message

    def _recv_line(self):
        while True:
            l = self._recv_buffer.find(b"\r\n")
            if l != -1:
                line_bytes = self._recv_buffer[:l]
                self._recv_buffer = self._recv_buffer[l+2:]
                if line_bytes:
                    return line_bytes
            new_bytes = self._socket.recv(self.RECV_SIZE)
            if not new_bytes:
                raise Exception("Server closed connection")
            self._recv_buffer += new_bytes

    def _magically_decode_utf8(self, bytestring):
        return ftfy.fix_text(bytestring.decode("cp1252"))

    def send_message(self, message):
        line = format_message(message)
        logger.debug("<-- %s", line)
        line += "\r\n"
        line_bytes = line.encode("utf-8")
        self._socket.sendall(line_bytes)

    def send(self, *args):
        self.send_message(make_message(*args))


Config = collections.namedtuple("Config", "host, port, nick, realname, channels")
class Hooks:
    def on_ready(self):
        pass

    def on_ping(self):
        pass


def run_client(config, hooks):
    logger.info("Connecting to {host}:{port}".format(**config._asdict()))
    with MessageConnection(config.host, config.port) as conn:
        logger.info("Using nick \"{nick}\" and realname \"{realname}\"".format(**config._asdict()))
        conn.send("NICK", config.nick)
        conn.send("USER", config.nick, "0", "*", config.realname)
        channels_to_join = set(config.channels)
        joined_channels = set()
        while True:
            message = conn.recv_message()
            if message.command == "001":
                logger.info("Joining channels: {}".format(", ".join(config.channels)))
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
                        logger.info("Joined {} of {} channels".format(len(joined_channels), len(channels_to_join)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--systemd", action="store_true")
    parser.add_argument("host")
    parser.add_argument("port", type=int)
    parser.add_argument("nick")
    parser.add_argument("realname")
    parser.add_argument("channels", nargs="*")
    args = parser.parse_args()
    if args.systemd:
        from systemd.journal import JournalHandler
        from systemd.daemon import notify

        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        root_logger.addHandler(JournalHandler(SYSLOG_IDENTIFIER="pladder-irc"))

        class SystemdHooks(Hooks):
            def on_ready(self):
                notify("READY=1")

            def on_ping(self):
                notify("WATCHDOG=1")

        hooks = SystemdHooks()
    else:
        logging.basicConfig(level=logging.DEBUG)
        hooks = Hooks()
    config = Config(args.host, args.port, args.nick, args.realname, args.channels)
    run_client(config, hooks)


if __name__ == "__main__":
    main()
