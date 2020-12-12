from unittest.mock import Mock
import pytest

from pladder.bjukkify import pladder_plugin, bjukkify

def test_registers_command():
    """
    Should register command bjukkify that calls the bjukkifier
    """
    mockbot = Mock()
    with pladder_plugin(mockbot):
        pass
    mockbot.register_command.assert_called_with("bjukkify", bjukkify, varargs=True)

examples = {
    "": "",
    "a": "A",
    "ab": "Ab",
    "b": "b",
    "bo": "bO",
    "apa": "AbE",
    "bjuckern": "bjUGGERN",
    "fiska": "fEZGE",
    "fika": "fEGE",
    "fiskbuk": "fEZGbUG",
    "friskis": "fREZGEZ",
    "hestar": "hEZdAR",
    "hest": "hEZd",
    "ingenting": "iNGENdENG",
    "läsa": "läZE",
    "läska": "läZGE",
    "kjol": "kjOl",
    "muxxern": "MUGGZERN",
    "netsplit": "NEdZblEd",
    "oxe": "OGZE",
    "patrik": "PAdREG",
    "pizza": "PEddZE",
    "pizzor": "PEddZOR",
    "ringklocka": "RENGGlOGGE",
    "spela": "SPElE",
    "Elon Musk": "ElON MUZG",
    "Mona Lisa": "MONE lEZE",
    "Morgon_kaffet, kanske i den sköna sängen idag":
        "MORGON_GAffEd, kANSkE i dEN SköNE SäNGEN idAG",
    "Platt, mjuk och frisk": "PlAdd, MjUG OG fREZG",
    "Du och jag trattern": "dU OG EG tRAddERN",
    "Jag ska haxxa en dattra": "EG SkE hOGGZE EN dAddRE"
}
test_data = examples.items()

@pytest.mark.parametrize("swedish,bjukkish", test_data)
def test_bjukkify(swedish, bjukkish):
    """
    Should bjukkify test data correctly
    """
    assert bjukkify(swedish) == bjukkish

if __name__ == '__main__':
    pytest.main([__file__])
