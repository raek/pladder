from contextlib import contextmanager


a = [
    'ba',
    'hababa',
    'hababadagada',
    'ba',
    'babababa',
    'hababababa',
    'habababa',
    'hababa',
    'hababakadaka',
    'hakadah',
    'baba',
    'hababadakadaka',
]


b = [
    'ha',
    'haba',
    'hababakadoodaka',
    'habawadarabawahahadabagadababa',
    'ha',
    'haba',
    'hababakadoodaka',
    'habawadadoobawahahadabagadababaah',
]


stanzas = [' / '.join(lines) for lines in [a, a, b, b, a, a, a, b, b, ['ba']]]

@contextmanager
def pladder_plugin(bot):
    bot.register_command('bah', bah)
    yield


def bah():
    """
    Returns the wisdom of dog
    """
    return ' // '.join(stanzas)
