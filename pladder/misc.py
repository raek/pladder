import re

class MiscCmds():
    def kloofify_word(self, target):
        # String ends with vowels, but has vowel-consonant before that
        w1 = re.compile('[aeiouyåäö]+[^aeiouyåäö]+[aeiouyåäö]+$')
        s1 = w1.search(target)
        if s1:
            return target[0:s1.start():] + "oo" + target[s1.start()+1:s1.end()-1:] + "y"
        # String ends with a consonant, but there are preceding vowels
        w2 = re.compile('[aeiouyåäö]+[^aeiouyåäö]+$')
        s2 = w2.search(target)
        if s2:
            return target[0:s2.start():] + "oo" + target[s2.start()+1:s2.end():] + "y"
        w3 = re.compile('[^aeiouyåäö]+[aeiouyåäö]+$')
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
