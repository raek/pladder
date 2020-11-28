import re

from pladder.plugin import Plugin
from datetime import datetime

class MiscPlugin(Plugin):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.misc_cmds = MiscCmds()
        bot.register_command("kloo+fify", self.kloofify, varargs=True, regex=True, contextual=True)
        bot.register_command("vrå+lify", self.vral, varargs=True, regex=True, contextual=True)
        bot.register_command("time", self.time)
        bot.register_command("capify", self.capify, varargs=True, regex=False, contextual=False)

    def kloofify(self, context, text):
        command = context['command']
        for _ in range(command.count("o")-1):
            text = self.misc_cmds.kloofify(text)
        return text
    
    def vral(self, context, text):
        i = context['command'].lower().count("å")-1
        text = self.misc_cmds.vral(i, text)
        return text
    
    def time(self):
        now = datetime.now()
        t = now.strftime("%H:%M:%S.%f")
        return t

    def capify(self, text):
        return text.title()



class MiscCmds:
    def check_spoofy(self, target):
        r_spoof = re.compile('[aeiouyåäö]+[^aeiouyåäö]+i(?=[^aeiouyåäö]+y$)')
        m_spoof = r_spoof.search(target)

        if (m_spoof):
            return target[0:m_spoof.start()] + 'oo' + target[m_spoof.end():len(target)]

        return target

    def strip_double_consonants(self, target):
        r = re.compile('oo(bb|cc|ck|dd|ff|gg|hh|jj|kk|ll|mm|nn|pp|qq|rr|ss|tt|vv|ww|xx|zz)y$', re.IGNORECASE)
        m = r.search(target)
        if m:
            return target[0:m.start()+2:] + target[m.end()-2:len(target):]
        else:
            return target

    def strip_vowels_from_end(self, target):
        r = re.compile('[^aeiouyåäö][aeiouyåäö]+$', re.IGNORECASE)
        m = r.search(target)
        if m:
            return target[0:m.start()+1:] + target[len(target)-1]
        else:
            return target

    def kloofify_word(self, target):
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
        spoof = self.check_spoofy(target)
        if (spoof != target):
            return spoof

        m_multi_1 = r_multi_1.search(target)
        m_multi_2 = r_multi_2.search(target)
        if m_multi_1:
            return self.kloofify_word(target[0:m_multi_2.start():]) + m_multi_2.group(0)

        m1 = r1.search(target)
        m1s = r1s.search(target)
        if m1:
            return self.strip_vowels_from_end(target[0:m1.start():] + "oo" + target[m1s.start()+1:m1.end()-1:] + "y")

        m2 = r2.search(target)
        m2s = r2s.search(target)
        if m2:
            return target[0:m2.start():] + "oo" + target[m2s.start()+1:m2.end():] + "y"

        m3 = r3.search(target)
        if m3:
            return target[0:m3.start()+1:] + "ooey"
        else:
            return target + "ooey"

    def kloofify(self, target):
        new_str = ""
        for word in target.split(' '):
            new_str = new_str + self.strip_double_consonants(self.kloofify_word(word)) + " "
        return new_str.rstrip()

    def dupe_vowel_pre_consonant(self, text):
        pattern = re.compile('([aeiouyåäö])([bcdfghjklmnpqrstvzx])', re.IGNORECASE)
        return pattern.sub(r"\1\1\2", text)

    def vral(self, i, text):
        i = i*2 if len(text)<16 else i
        i = i*2 if len(text)<8 else i
        # vrålify 'n' if there are no vowels
        if not re.search(r'[aeiouyåäö]', text, re.I):
            for _ in range(i):
                text = re.sub(r'(n)([bcdfghjklmpqrstvzx])', r'\1\1\2', text, 0, re.IGNORECASE)
        for _ in range(i):
            text = self.dupe_vowel_pre_consonant(text)
        return text.upper()
