from typing import NamedTuple

from pladder.misc import vraaaal


class DummyContext(NamedTuple):
    command_name: str


def run(command_name, argument):
    return vraaaal(DummyContext(command_name), argument)


def test_one_aa_short_word():
    assert run("vrålify", "hej") == "HEJ"


def test_two_aa_short_word():
    assert run("vråålify", "hej") == "HEEEEEJ"


def test_three_aa_short_word():
    assert run("vrååålify", "hej") == "HEEEEEEEEEJ"


def test_one_aa_medium_word():
    assert run("vrålify", "bananarama") == "BANANARAMA"


def test_two_aa_medium_word():
    assert run("vråålify", "bananarama") == "BAAANAAANAAARAAAMAAA"


def test_three_aa_medium_word():
    assert run("vrååålify", "bananarama") == "BAAAAANAAAAANAAAAARAAAAAMAAAAA"


def test_one_aa_long_word():
    assert run("vrålify", "bananaramabandana") == "BANANARAMABANDANA"


def test_two_aa_long_word():
    assert run("vråålify", "bananaramabandana") == "BAANAANAARAAMAABAANDAANAA"


def test_three_aa_long_word():
    assert run("vrååålify", "bananaramabandana") == "BAAANAAANAAARAAAMAAABAAANDAAANAAA"


def test_one_aa_hng():
    assert run("vrålify", "hng") == "HNG"


def test_two_aa_hng():
    assert run("vråålify", "hng") == "HNNNNNG"


def test_three_aa_hng():
    assert run("vrååålify", "hng") == "HNNNNNNNNNG"


def test_zero_aa_long_word():
    assert run("vrlify", "bananaramabandana") == "BNNRMBNDN"
