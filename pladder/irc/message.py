import codecs
from contextlib import suppress
from collections import namedtuple
import logging
import socket
from threading import Lock
from time import sleep


logger = logging.getLogger("pladder.irc")


Message = namedtuple("Message", "sender, command, params")
Sender = namedtuple("Sender", "nick, user, host")
NO_SENDER = Sender(None, None, None)
MAX_LINE_BYTES = 512
OUTGOING_RATE_LIMIT = 2  # seconds between each outgoing message


def make_message(command, *params):
    return Message(NO_SENDER, command, params)


def parse_message(line):
    p = _Parser(line)
    return p.parse()


class _Parser:
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
        length = self._rest.find(" ")
        if length == -1:
            word = self._rest
            self._rest = ""
        else:
            word = self._rest[:length]
            self._rest = self._rest[length+1:]
        return word

    def _split_off_optional_suffix(self, s, delimiter):
        length = s.find(delimiter)
        if length == -1:
            return s, None
        else:
            return s[:length], s[length+1:]


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
        last_param = msg.params[-1]
        if last_param.startswith(":") or " " in last_param:
            separator = " :"
        else:
            separator = " "
        result += separator + last_param
    return result


# Takes message and returns generator to split long lines into separate messages
def message_generator(msgtype, target, reply_prefix, text, conn_overhead):
    header = f"{msgtype} {target} :{reply_prefix}"
    # -2 because CR LF will be added
    max_msglength = MAX_LINE_BYTES - 2 - len(header.encode("utf-8")) - conn_overhead
    while len(text) > 0:
        if len(text.encode("utf-8")) > max_msglength:
            more = ' <more>'
            max_partlength = max_msglength - len(more.encode("utf-8"))
            # Take the longest utf-8 encodable part of the text that will fit
            msgpart = text[:max_partlength]
            while len(msgpart.encode('utf-8')) > max_partlength:
                msgpart = msgpart[:-1]
            # Avoid cutting a word in part, by finding the previous space,
            # within reason
            endpos = msgpart.rfind(" ")
            if endpos < 350:
                endpos = len(msgpart)
            text = text[endpos:].lstrip()
            msgpart = msgpart[:endpos]
            msgpart = f"{header}{msgpart}{more}"
        else:
            msgpart = f"{header}{text}"
            text = ""
        yield msgpart


class ConnectionError(Exception):
    pass


class MessageConnection:
    RECV_SIZE = 4096

    def __init__(self, host, port):
        self._recv_buffer = b""
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect((host, port))
        self._send_lock = Lock()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def close(self):
        self._socket.close()

    def recv_messages(self):
        with suppress(ConnectionError):
            while True:
                yield self.recv_message()

    def recv_message(self):
        line_bytes = self._recv_line()
        line = decode_utf8_with_fallback(line_bytes)
        logger.debug("--> %s", line)
        message = parse_message(line)
        return message

    def _recv_line(self):
        while True:
            length = self._recv_buffer.find(b"\r\n")
            if length != -1:
                line_bytes = self._recv_buffer[:length]
                self._recv_buffer = self._recv_buffer[length+2:]
                if line_bytes:
                    return line_bytes
            new_bytes = self._socket.recv(self.RECV_SIZE)
            if not new_bytes:
                raise ConnectionError("Server closed connection")
            self._recv_buffer += new_bytes

    def send_message(self, message):
        line = format_message(message)
        logger.debug("<-- %s", line)
        line = line.replace("\n", "").replace("\r", "")
        line_bytes = line.encode("utf-8")
        line_bytes = line_bytes[:MAX_LINE_BYTES - 2]
        line_bytes += b"\r\n"
        with self._send_lock:
            self._socket.sendall(line_bytes)
            sleep(OUTGOING_RATE_LIMIT)

    def send(self, *args):
        self.send_message(make_message(*args))


def decode_utf8_with_fallback(bytestring):
    return bytestring.decode("utf8", errors="fallback_to_cp1252")


def _fallback_to(encoding_name):
    def error_handler(err):
        replacement = err.object[err.start:err.end].decode(encoding_name)
        return replacement, err.end
    return error_handler


codecs.register_error("fallback_to_cp1252", _fallback_to("cp1252"))
