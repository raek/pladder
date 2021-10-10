# https://github.com/OpenTTD/OpenTTD/blob/master/src/table/townname.h
# https://github.com/OpenTTD/OpenTTD/blob/master/src/townname.cpp

from contextlib import contextmanager
import random


@contextmanager
def pladder_plugin(bot):
    cmds = bot.new_command_group("ttd")
    cmds.register_command("ttd", gentown)
    yield


se1 = ["Gamla ", "Lilla ", "Nya ", "Stora "]
se2 = ["Boll", "Bor", "Ed", "En", "Erik", "Es", "Fin", "Fisk", "Grön", "Hag", "Halm", "Karl", "Kram", "Kung", "Land",
       "Lid", "Lin", "Mal", "Malm", "Marie", "Ner", "Norr", "Oskar", "Sand", "Skog", "Stock", "Stor", "Ström", "Sund",
       "Söder", "Tall", "Tratt", "Troll", "Upp", "Var", "Väster", "Ängel", "Öster", "Strut"]
se2a = ["B", "Br", "D", "Dr", "Dv", "F", "Fj", "Fl", "Fr", "G", "Gl", "Gn", "Gr", "H", "J", "K", "Kl", "Kn", "Kr", "Kv",
        "L", "M", "N", "P", "Pl", "Pr", "R", "S", "Sk", "Skr", "Sl", "Sn", "Sp", "Spr", "St", "Str", "Sv", "T", "Tr",
        "Tv", "V", "Vr"]
se2b = ["a", "e", "i", "o", "u", "y", "å", "ä", "ö"]
se2c = ["ck", "d", "dd", "g", "gg", "l", "ld", "m", "n", "nd", "ng", "nn",
        "p", "pp", "r", "rd", "rk", "rp", "rr", "rt", "s", "sk", "st", "t", "tt", "v"]
se3 = ["arp", "berg", "boda", "borg", "bro", "bukten", "by", "byn", "fors", "hammar", "hamn", "holm", "hus", "hättan",
       "kulle", "köping", "lund", "löv", "sala", "skrona", "slätt", "spång", "stad", "sund", "svall", "svik", "såker",
       "udde", "valla", "viken", "älv", "ås"]


def gentown():
    town = ""
    if (random.random() > 0.7):
        town += random.choice(se1)
    if (random.random() > 0.6):
        town += random.choice(se2)
    else:
        town += random.choice(se2a)
        town += random.choice(se2b)
        town += random.choice(se2c)
    town += random.choice(se3)
    return town
