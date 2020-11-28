from pladder.plugin import Plugin

class BjukkifyPlugin(Plugin):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        bot.register_command("bjukkify", self.bjukkify)

    def _is_vowel(self, char):
        swedish_vowels = "aouåeiyäö"
        return char in swedish_vowels

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
            "hax": "hogz",
        }
        for sequence in special_sequences.items():
            word = word.replace(*sequence)
        return word

    def _lookup_and_replace(self, word, lut):
        if word in lut.keys():
            word = lut[word]
        return word

    def _soften_vowel(self, vowel):
        softened_vowels = {
            "i": "e",
        }
        return self._lookup_and_replace(vowel, softened_vowels)

    def _soften_last_vowel(self, vowel):
        softened_last_vowels = {
            "a": "e",
        }
        return self._lookup_and_replace(vowel, softened_last_vowels)

    def _soften_multiple_consonants(self, consonants):
        softened_multiple_consonants = {
            "zz": "ddz",
            "xx": "ggz",
        }
        return self._lookup_and_replace(consonants, softened_multiple_consonants)

    def _soften_single_consonant(self, consonant):
        softened_consonants = {
            "c": "g",
            "k": "g",
            "s": "z",
            "t": "d",
            "p": "b",
            "q": "g",
            "x": "gz",
        }
        return self._lookup_and_replace(consonant, softened_consonants)

    def _next_vowel_position(self, word):
        for pos, char in enumerate(word):
            if self._is_vowel(char):
                return pos
        return len(word)

    def _bjukkify_word(self, word):
        last_char = len(word) - 1
        bjukkified_word = ""
        skip_to = 0
        for pos, char in enumerate(word):
            if self._is_vowel(char) and pos < last_char:
                consonant_group_start = pos + 1
                consonant_group_end = consonant_group_start + \
                    self._next_vowel_position(word[(consonant_group_start):])
                consonant_group = word[consonant_group_start:consonant_group_end]
                softened_consonants = ""
                temp = self._soften_multiple_consonants(consonant_group)
                for temp_char in temp:
                    softened_consonants += self._soften_single_consonant(temp_char)
                vowel = word[pos]
                if softened_consonants != consonant_group:
                    vowel = self._soften_vowel(vowel)
                bjukkified_word += vowel
                bjukkified_word += softened_consonants
                skip_to = consonant_group_end
            elif skip_to <= pos:
                if pos == last_char:
                    char = self._soften_last_vowel(char)
                bjukkified_word += char
        return bjukkified_word

    def _should_be_caps(self, char):
        caps_chars = "acegmnopqrsuvwz"
        return char in caps_chars

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
            is_special, special_word = self._is_special_word(word)
            if is_special:
                bjukkified_words.append(special_word)
            else:
                word = self._replace_special_sequences(word)
                bjukkified_words.append(self._bjukkify_word(word))
        return self._capsify_text(" ".join(bjukkified_words))

if __name__ == "__main__":
    import sys
    from unittest.mock import Mock
    plugin = BjukkifyPlugin(Mock())
    print(plugin.bjukkify(sys.argv[1]))
