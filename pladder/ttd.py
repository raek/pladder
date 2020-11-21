# https://github.com/OpenTTD/OpenTTD/blob/master/src/table/townname.h
# https://github.com/OpenTTD/OpenTTD/blob/master/src/townname.cpp

from pladder.plugin import Plugin
import random


class TTDPlugin(Plugin):
    def __init__(self, bot):
        super().__init__()
        self.se1 = ["Gamla ", "Lilla ", "Nya ", "Stora "]
        self.se2 = ["Boll", "Bor", "Ed", "En", "Erik", "Es", "Fin", "Fisk", "Grön", "Hag", "Halm", "Karl", "Kram", "Kung", "Land", "Lid", "Lin", "Mal", "Malm", "Marie",
                    "Ner", "Norr", "Oskar", "Sand", "Skog", "Stock", "Stor", "Ström", "Sund", "Söder", "Tall", "Tratt", "Troll", "Upp", "Var", "Väster", "Ängel", "Öster", "Strut"]
        self.se2a = ["B", "Br", "D", "Dr", "Dv", "F", "Fj", "Fl", "Fr", "G", "Gl", "Gn", "Gr", "H", "J", "K", "Kl", "Kn", "Kr", "Kv",
                     "L", "M", "N", "P", "Pl", "Pr", "R", "S", "Sk", "Skr", "Sl", "Sn", "Sp", "Spr", "St", "Str", "Sv", "T", "Tr", "Tv", "V", "Vr"]
        self.se2b = ["a", "e", "i", "o", "u", "y", "å", "ä", "ö"]
        self.se2c = ["ck", "d", "dd", "g", "gg", "l", "ld", "m", "n", "nd", "ng", "nn",
                     "p", "pp", "r", "rd", "rk", "rp", "rr", "rt", "s", "sk", "st", "t", "tt", "v"]
        self.se3 = ["arp", "berg", "boda", "borg", "bro", "bukten", "by", "byn", "fors", "hammar", "hamn", "holm", "hus", "hättan", "kulle", "köping",
                    "lund", "löv", "sala", "skrona", "slätt", "spång", "stad", "sund", "svall", "svik", "såker", "udde", "valla", "viken", "älv", "ås"]
        self.bot = bot
        bot.register_command("ttd", self.gentown)

    def gentown(self):
        town = ""
        if (random.random() > 0.7):
            town += random.choice(self.se1)
        if (random.random() > 0.6):
            town += random.choice(self.se2)
        else:
            town += random.choice(self.se2a)
            town += random.choice(self.se2b)
            town += random.choice(self.se2c)
        town += random.choice(self.se3)
        return town
