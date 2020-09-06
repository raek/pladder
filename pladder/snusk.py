import json
import random


class SnuskDb:
    def __init__(self, db_file_path):
        self._db_file_path = db_file_path
        with open(self._db_file_path, "rt", encoding="utf8") as f:
            self._entries = json.load(f)

    def _save(self):
        with open(self._db_file_path, "wt", encoding="utf8") as f:
            json.dump(self._entries, f, ensure_ascii=False, indent=True, sort_keys=True)

    def snusk(self):
        return self._format_quad(self._random_quad())

    def directed_snusk(self, target):
        quad = self._random_quad()
        i = random.choice([0, 1, 2, 3])
        if i % 2 == 0:
            part = target
        else:
            part = target + "ern"
        quad[i] = part
        return self._format_quad(quad)

    def example_snusk(self, a, b):
        quad = self._random_quad()
        if random.choice([False, True]):
            quad[0] = a
            quad[3] = b
        else:
            quad[1] = b
            quad[2] = a
        return self._format_quad(quad)

    def _format_quad(self, quad):
        return "{}{} i {}{}".format(*quad)

    def _random_quad(self):
        return [self._random_entry()[i % 2] for i in range(4)]

    def _random_entry(self):
        return random.choice(self._entries)

    def add_snusk(self, a, b):
        new_entry = [a, b]
        if new_entry in self._entries:
            return False
        self._entries.append(new_entry)
        self._save()
        return True


if __name__ == "__main__":
    db = SnuskDb("snusk_db.json")
    #db.add_snusk("kraft", "kraften")
    print(db.snusk())
    print(db.directed_snusk("raek"))
    print(db.example_snusk("don", "donet"))
    db._save()
