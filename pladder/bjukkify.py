from pladder.plugin import Plugin

class BjukkifyPlugin(Plugin):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        bot.register_command("bjukkify", self.bjukkify, varargs=True)

    def _should_be_caps(self, char):
        caps_chars = "acegmnopqrsuvwz"
        return char in caps_chars

    def _replace_occurences(self, word, lut):
        for item in lut.items():
            word = word.replace(*item)
        return word

    def _is_vowel(self, char):
        swedish_vowels = "aouåeiyäö"
        return char in swedish_vowels

    def _find_first_vowel(self, word):
        last_char = len(word) - 1
        for pos, char in enumerate(word):
            if self._is_vowel(char):
                return pos
        return last_char

    def _lookup_and_replace(self, char, lut):
        if char in lut.keys():
            char = lut[char]
        return char

    def _soften_other_vowels(self, word):
        softened_vowels = {
            "i": "e",
        }
        return self._replace_occurences(word, softened_vowels)

    def _soften_last_vowel(self, char):
        softened_last_vowels = {
            "a": "e",
        }
        return self._lookup_and_replace(char, softened_last_vowels)

    def _is_special_word(self, word):
        special_words = {
            "jag": "eg",
            "kanske": "kanske",
            "och": "og",
        }
        found = word in special_words.keys()
        if found:
            word = special_words[word]
        return found, word

    def _replace_special_sequences(self, word):
        special_sequences = {
            "haxx": "hoggz",
        }
        return self._replace_occurences(word, special_sequences)

    def _soften_consonants(self, word):
        softened_consonants = {
            "zz": "ddz",
            "xx": "ggz",
            "c": "g",
            "k": "g",
            "s": "z",
            "t": "d",
            "p": "b",
            "q": "g",
            "x": "gz",
        }
        first_vowel = self._find_first_vowel(word)
        return word[:first_vowel] \
            + self._replace_occurences(word[first_vowel:], softened_consonants)

    def _soften_vowels(self, word):
        if len(word) >= 3:
            word = word[0] \
                + self._soften_other_vowels(word[1:-1]) \
                + self._soften_last_vowel(word[-1])
        return word

    def _capsify_text(self, text):
        capsified_text = ""
        for char in text:
            if self._should_be_caps(char):
                char = char.upper()
            capsified_text += char
        return capsified_text

    def bjukkify(self, text):
        """
        Returns a bjukkified version of the provided text
        """
        text = text.lower()
        words = text.split(" ")
        bjukkified_words = []
        for word in words:
            if word == "":
                continue
            is_special, special_word = self._is_special_word(word)
            if is_special:
                bjukkified_words.append(special_word)
            else:
                word = self._replace_special_sequences(word)
                word = self._soften_consonants(word)
                word = self._soften_vowels(word)
                bjukkified_words.append(word)
        return self._capsify_text(" ".join(bjukkified_words))

if __name__ == "__main__":
    import sys
    from unittest.mock import Mock
    plugin = BjukkifyPlugin(Mock())
    print(plugin.bjukkify(sys.argv[1]))
