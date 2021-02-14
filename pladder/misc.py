from contextlib import contextmanager
from datetime import datetime
import re


@contextmanager
def pladder_plugin(bot):
    bot.register_command(re.compile("^kloo+fify$"), kloooofify, varargs=True, contextual=True)
    bot.register_command(re.compile("^vrå+lify$"), vraaaal, varargs=True, contextual=True)
    bot.register_command("time", time)
    bot.register_command("capify", capify, varargs=True)
    yield


def kloooofify(context, text):
    command = context['command']
    for _ in range(command.count("o")-1):
        text = kloofify(text)
    return text


def vraaaal(context, text):
    i = context['command'].lower().count("å")-1
    text = vral(i, text)
    return text


def time():
    now = datetime.now()
    t = now.strftime("%H:%M:%S.%f")
    return t


def capify(text):
    return text.title()


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


def dupe_vowel_pre_consonant(text):
    pattern = re.compile('([aeiouyåäö])([bcdfghjklmnpqrstvzx])', re.IGNORECASE)
    return pattern.sub(r"\1\1\2", text)


def vral(i, text):
    i = i*2 if len(text) < 16 else i
    i = i*2 if len(text) < 8 else i
    # vrålify 'n' if there are no vowels
    if not re.search(r'[aeiouyåäö]', text, re.I):
        for _ in range(i):
            text = re.sub(r'(n)([bcdfghjklmpqrstvzx])', r'\1\1\2', text, 0, re.IGNORECASE)
    for _ in range(i):
        text = dupe_vowel_pre_consonant(text)
    return text.upper()
