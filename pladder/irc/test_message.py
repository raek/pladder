from pladder.irc.message import decode_utf8_with_fallback


def test_decoding_ascii():
    assert decode_utf8_with_fallback(b"Hello") == "Hello"


def test_decoding_swedish_utf8():
    assert decode_utf8_with_fallback(b"\xc3\xa5 \xc3\xa4 \xc3\xb6") == "å ä ö"


def test_decoding_swedish_latin1_cp1252():
    assert decode_utf8_with_fallback(b"\xe5 \xe4 \xf6") == "å ä ö"


def test_decoding_exotic_diacritics():
    assert decode_utf8_with_fallback(b"i\xcc\x87") == "i\u0307"  # i + combining dot above
