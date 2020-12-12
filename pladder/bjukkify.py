from contextlib import contextmanager

@contextmanager
def pladder_plugin(bot):
    bot.register_command("bjukkify", bjukkify, varargs=True)
    yield

def _should_be_caps(char):
    caps_chars = "acegmnopqrsuvwyz"
    return char in caps_chars

def _replace_occurences(word, lut):
    for item in lut.items():
        word = word.replace(*item)
    return word

def _is_vowel(char):
    swedish_vowels = "aouåeiyäö"
    return char in swedish_vowels

def _find_first_vowel(word):
    last_char = len(word) - 1
    for pos, char in enumerate(word):
        if _is_vowel(char):
            return pos
    return last_char

def _lookup_and_replace(char, lut):
    if char in lut.keys():
        char = lut[char]
    return char

def _soften_other_vowels(word):
    softened_vowels = {
        "i": "e",
    }
    return _replace_occurences(word, softened_vowels)

def _soften_last_vowel(char):
    softened_last_vowels = {
        "a": "e",
    }
    return _lookup_and_replace(char, softened_last_vowels)

def _is_special_word(word):
    special_words = {
        "jag": "eg",
        "kanske": "kanske",
        "och": "og",
    }
    found = word in special_words.keys()
    if found:
        word = special_words[word]
    return found, word

def _replace_special_sequences(word):
    special_sequences = {
        "haxx": "hoggz",
    }
    return _replace_occurences(word, special_sequences)

def _soften_consonants(word):
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
    first_vowel = _find_first_vowel(word)
    return word[:first_vowel] \
        + _replace_occurences(word[first_vowel:], softened_consonants)

def _soften_vowels(word):
    if len(word) >= 3:
        word = word[0] \
            + _soften_other_vowels(word[1:-1]) \
            + _soften_last_vowel(word[-1])
    return word

def _capsify_text(text):
    capsified_text = ""
    for char in text:
        if _should_be_caps(char):
            char = char.upper()
        capsified_text += char
    return capsified_text

def bjukkify(text):
    """
    Returns a bjukkified version of the provided text
    """
    text = text.lower()
    words = text.split(" ")
    bjukkified_words = []
    for word in words:
        if word == "":
            continue
        is_special, special_word = _is_special_word(word)
        if is_special:
            bjukkified_words.append(special_word)
        else:
            word = _replace_special_sequences(word)
            word = _soften_consonants(word)
            word = _soften_vowels(word)
            bjukkified_words.append(word)
    return _capsify_text(" ".join(bjukkified_words))

if __name__ == "__main__":
    import sys
    print(bjukkify(sys.argv[1]))
