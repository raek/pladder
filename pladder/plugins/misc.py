from contextlib import contextmanager
from datetime import datetime
import random
import re
import unicodedata

from pladder.script.types import ScriptError


@contextmanager
def pladder_plugin(bot):
    cmds = bot.new_command_group("misc")
    cmds.register_command("give", give, varargs=True)
    cmds.register_command(re.compile("^kloo+fify$"), kloooofify, varargs=True, contextual=True)
    cmds.register_command(re.compile("^vrå*lify$"), vraaaal, varargs=True, contextual=True)
    cmds.register_command("time", time)
    cmds.register_command("capify", capify, varargs=True)
    cmds.register_command("suspektify", suspektify, varargs=True)
    cmds.register_command("tutify", tutify, varargs=True)
    cmds.register_command("unicode", unicode, varargs=True)
    cmds.register_command("unicode-name", unicode_name, varargs=True)
    cmds.register_command("tijd", tijd)
    cmds.register_command("vecka", vecka)
    cmds.register_command("morse", morse, varargs=True)
    cmds.register_command("unmorse", unmorse)
    yield


def give(target, text):
    return f"{target}: {text}"


def kloooofify(context, text):
    command = context.command_name
    for _ in range(command.count("o")-1):
        text = kloofify(text)
    return text


def vraaaal(context, text):
    count = context.command_name.lower().count("å")
    text = vral(count, text)
    return text


def time():
    now = datetime.now()
    t = now.strftime("%H:%M:%S.%f")
    return t


def capify(text):
    return text.title()


def suspektify(text):
    import random
    words = text.split(" ")
    # suspektify between 1 word and 1/8 of all words, +-1
    max_word_count = len(words)//8 + 1
    suspekt_word_count = random.randint(1, max_word_count)
    # pick out indices for the words to suspektify
    suspekt_word_indices = random.sample(range(len(words)), suspekt_word_count)
    # perform suspektification
    for i in suspekt_word_indices:
        words[i] = '"%s"' % words[i]
    return " ".join(words)


def tutify(text):
    return re.sub(r"([aeiouyåäö]+)", "\U0001f4e2", text)


def check_spoofy(target):
    r_spoof = re.compile('[aeiouyåäö]+[^aeiouyåäö]+i(?=[^aeiouyåäö]+y$)')
    m_spoof = r_spoof.search(target)

    if (m_spoof):
        return target[0:m_spoof.start()] + 'oo' + target[m_spoof.end():len(target)]

    return target


def strip_double_consonants(target):
    r = re.compile('oo(bb|cc|ck|dd|ff|gg|hh|jj|kk|ll|mm|nn|pp|qq|rr|ss|tt|vv|ww|xx|zz)y$', re.IGNORECASE)
    m = r.search(target)
    if m:
        return target[0:m.start()+2:] + target[m.end()-2:len(target):]
    else:
        return target


def strip_vowels_from_end(target):
    r = re.compile('[^aeiouyåäö][aeiouyåäö]+$', re.IGNORECASE)
    m = r.search(target)
    if m:
        return target[0:m.start()+1:] + target[len(target)-1]
    else:
        return target


def kloofify_word(target):
    # String is already partially kloofified. Matching these will result in a recursive call, further
    # kloofifying the string. We have to go deeper.
    r_multi_1 = re.compile('[aeiouyåäö]+[^aeiouyåäö]+y*(oo)[^aeiouyåäö]+y$', re.IGNORECASE)
    r_multi_2 = re.compile('(oo)[^aeiouyåäö]+y$', re.IGNORECASE)
    # String ends with vowels, but has vowel(s)-consonant before that
    r1 = re.compile('[aeiouyåäö]+[^aeiouyåäö]+[aeiouyåäö]+$', re.IGNORECASE)
    # Same as previous, but only checks for a single preceding vowel
    r1s = re.compile('[aeiouyåäö][^aeiouyåäö]+[aeiouyåäö]+$', re.IGNORECASE)
    # String ends with consonants, but there are preceding vowels
    r2 = re.compile('[aeiouyåäö]+[^aeiouyåäö]+$', re.IGNORECASE)
    # Same as previous, but only checks for a single preceding vowel
    r2s = re.compile('[aeiouyåäö][^aeiouyåäö]+$', re.IGNORECASE)
    # String ends with vowels, with preceding consonant
    r3 = re.compile('[^aeiouyåäö][aeiouyåäö]+$', re.IGNORECASE)

    # Special case for strings matching "spotify"-like patterns
    spoof = check_spoofy(target)
    if (spoof != target):
        return spoof

    m_multi_1 = r_multi_1.search(target)
    m_multi_2 = r_multi_2.search(target)
    if m_multi_1:
        return kloofify_word(target[0:m_multi_2.start():]) + m_multi_2.group(0)

    m1 = r1.search(target)
    m1s = r1s.search(target)
    if m1:
        return strip_vowels_from_end(target[0:m1.start():] + "oo" + target[m1s.start()+1:m1.end()-1:] + "y")

    m2 = r2.search(target)
    m2s = r2s.search(target)
    if m2:
        return target[0:m2.start():] + "oo" + target[m2s.start()+1:m2.end():] + "y"

    m3 = r3.search(target)
    if m3:
        return target[0:m3.start()+1:] + "ooey"
    else:
        return target + "ooey"


def kloofify(target):
    new_str = ""
    for word in target.split(' '):
        new_str = new_str + strip_double_consonants(kloofify_word(word)) + " "
    return new_str.rstrip()


def vral(count, text):
    if len(text) < 8:
        multiplier = 4
    elif len(text) < 16:
        multiplier = 2
    else:
        multiplier = 1

    def replace(match):
        vowel = match.group(1)
        if count == 0:
            return ""
        else:
            times = ((count - 1) * multiplier) + 1
            return vowel * times

    # vrålify 'n' if there are no vowels
    if not re.search(r'([aeiouyåäö=\U0001f4e2])', text, flags=re.IGNORECASE):
        text = re.sub(r'(n)(?=[bcdfghjklmpqrstvzx])', replace, text, flags=re.IGNORECASE)
    else:
        text = re.sub(r'([aeiouyåäö=\U0001f4e2])(?=[bcdfghjklmnpqrstvzx]|$)', replace, text, flags=re.IGNORECASE)
    return text.upper()


def unicode(char_name):
    try:
        return unicodedata.lookup(char_name)
    except KeyError:
        raise ScriptError("Uknown Unicode character name: " + char_name)


def unicode_name(chars):
    return ", ".join(unicodedata.name(char, "(unknown)").lower() for char in chars)


def tijd():
    hours = ["twaalf", "één", "twee", "drie", "vier", "vijf", "zes", "zeven",
             "acht", "negen", "tien", "elf"]
    minutes = ["één", "twee", "drie", "vier", "vijf", "zes", "zeven", "acht",
               "negen", "tien", "elf", "twaalf", "dertien", "veertien",
               "kwaart", "zestien", "zeventien", "achttien", "negentien",
               "twintig"]

    now = datetime.now()
    this_hour = hours[now.hour % 12]
    next_hour = hours[(now.hour + 1) % 12]
    if now.minute == 0:
        return f"{this_hour} uur"
    elif now.minute <= 20:
        minute = minutes[now.minute - 1]
        return f"{minute} over {this_hour}"
    elif now.minute <= 29:
        minute = minutes[30 - now.minute - 1]
        return f"{minute} voor half{next_hour}"
    elif now.minute == 30:
        return f"half{next_hour}"
    elif now.minute <= 39:
        minute = minutes[now.minute - 30 - 1]
        return f"{minute} over half{next_hour}"
    elif now.minute <= 59:
        minute = minutes[60 - now.minute - 1]
        return f"{minute} voor {next_hour}"
    else:
        return "geen idee"


def vecka():
    return str(datetime.now().isocalendar()[1])


MORSE_CODE = [
    (" ", " "),
    ("a", ".-"), ("b", "-..."), ("c", "-.-."), ("d", "-.."), ("e", "."),
    ("f", "..-."), ("g", "--."), ("h", "...."), ("i", ".."), ("j", ".---"),
    ("k", "-.-"), ("l", ".-.."), ("m", "--"), ("n", "-."), ("o", "---"),
    ("p", ".--."), ("q", "--.-"), ("r", ".-."), ("s", "..."), ("t", "-"),
    ("u", "..-"), ("v", "...-"), ("w", ".--"), ("x", "-..-"), ("y", "-.--"),
    ("z", "--.."), ("å", ".--.-"), ("ä", ".-.-"), ("ö", "---."),
    ("1", ".----"), ("2", "..---"), ("3", "...--"), ("4", "....-"), ("5", "....."),
    ("6", "-...."), ("7", "--..."), ("8", "---.."), ("9", "----."), ("0", "-----"),
    (".", ".-.-.-"), (",", "--..--"), ("?", "..--.."), ("'", ".----."), ("!", "-.-.--"),
    ("/", "-..-."), ("(", "-.--."), (")", "-.--.-"), ("&", ".-..."), (":", "---..."),
    (";", "-.-.-."), ("=", "-...-"), ("+", ".-.-."), ("-", "-....-"), ("_", "..--.-"),
    ('"', ".-..-."), ("$", "...-..-"), ("@", ".--.-."),
]
CHAR_TO_MORSE = {char: morse for char, morse in MORSE_CODE}
MORSE_TO_CHAR = {morse: char for char, morse in MORSE_CODE}


def char_to_morse(c):
    if c in CHAR_TO_MORSE:
        return CHAR_TO_MORSE[c]
    else:
        return "".join(random.choice(".-") for _ in range(8))


def morse_to_char(m):
    if m in MORSE_TO_CHAR:
        return MORSE_TO_CHAR[m]
    else:
        return "🤷"


def morse(s):
    return " ".join(char_to_morse(c) for c in s.lower())


def unmorse(s):
    words = []
    for coded_word in re.split(r"\s{2,}", s):
        words.append("".join(morse_to_char(char) for char in coded_word.split(" ")))
    return " ".join(words)
