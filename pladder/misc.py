import re

#TODO: Replace multiples of same consonants with single consonant (if between oo and y)
#TODO: Replace all vowels with oo in the vowel-consonant(-vowel) ender case

class MiscCmds():
    def kloofify_word(self, target):
        # String ends with vowels, but has vowel(s)-consonant before that
        w1 = re.compile('[aeiouyåäö]+[^aeiouyåäö]+[aeiouyåäö]+$', re.IGNORECASE)
        # Same as previous, but only checks for a single preceding vowel
        w1s = re.compile('[aeiouyåäö][^aeiouyåäö]+[aeiouyåäö]+$', re.IGNORECASE)
        # String ends with consonants, but there are preceding vowels
        w2 = re.compile('[aeiouyåäö]+[^aeiouyåäö]+$', re.IGNORECASE)
        # Same as previous, but only checks for a single preceding vowel
        w2s = re.compile('[aeiouyåäö][^aeiouyåäö]+$', re.IGNORECASE)
        # String ends with vowels, with preceding consonant
        w3 = re.compile('[^aeiouyåäö][aeiouyåäö]+$', re.IGNORECASE)
        
        s1 = w1.search(target)
        s1s = w1s.search(target)
        if s1:
            return target[0:s1.start():] + "oo" + target[s1s.start()+1:s1.end()-1:] + "y"
        
        s2 = w2.search(target)
        s2s = w2s.search(target)
        if s2:
            return target[0:s2.start():] + "oo" + target[s2s.start()+1:s2.end():] + "y"
        
        s3 = w3.search(target)
        if s3:
            return target[0:s3.start()+1:] + "ooey"
        else:
            return target + "ooey"
    
    def kloofify(self, target):
        new_str = ""
        for word in target.split(' '):
            new_str = new_str + self.kloofify_word(word) + " "
        return new_str.rstrip()
