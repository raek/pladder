import re

#TODO: Replace multiples of same consonants with single consonant (if between oo and y)

class MiscCmds():
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
