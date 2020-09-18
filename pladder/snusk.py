import json
import random



class SnuskDb:
    def __init__(self, db_file_path, prep_db_file_path=None):
        self._db_file_path = db_file_path
        with open(self._db_file_path, "rt", encoding="utf8") as f:
            self._entries = json.load(f)

        self._prep_db_file_path = prep_db_file_path
        with open(self._prep_db_file_path, "rt", encoding="utf8") as f:
            self._prep_entries = json.load(f)

    def _save(self):
        with open(self._db_file_path, "wt", encoding="utf8") as f:
            json.dump(self._entries, f, ensure_ascii=False, indent=True, sort_keys=True)

        with open(self._prep_db_file_path, "wt", encoding="utf8") as f:
            json.dump(self._prep_entries, f, ensure_ascii=False, indent=True, sort_keys=True)

    def snusk(self):
        return self._format_parts(self._random_parts())

    def directed_snusk(self, target):
        parts = self._random_parts()
        i = random.choice([0, 1, 3, 4])
        if i in [0, 3]:
            part = target
        else:
            part = target + "ern"
        parts[i] = part
        return self._format_parts(parts)

    def example_snusk(self, a, b):
        parts = self._random_parts()
        if random.choice([False, True]):
            parts[0] = a
            parts[4] = b
        else:
            parts[1] = b
            parts[3] = a
        return self._format_parts(parts)

    def _format_parts(self, parts):
        return "{}{} {} {}{}".format(*parts)

    def _random_parts(self):
        return [
            self._random_a_entry(),
            self._random_b_entry(),
            self._random_prep(),
            self._random_a_entry(),
            self._random_b_entry(),
        ]

    def _random_a_entry(self):
        return random.choice(self._entries)[0]

    def _random_b_entry(self):
        return random.choice(self._entries)[1]

    def _random_prep(self):
        return random.choice(self._prep_entries)

    def add_snusk(self, a, b):
        new_entry = [a, b]
        if new_entry in self._entries:
            return False
        self._entries.append(new_entry)
        self._save()
        return True

    def add_preposition(self, prep):
        if prep in self._prep_entries:
            return False
        self._prep_entries.append(prep)
        self._save()
        return True


if __name__ == "__main__":
    db = SnuskDb("snusk_db.json", "prepositions_db.json")
    #db = SnuskDb("snusk_db.json", "prepositions_db.json")
    print(db.snusk())
    print(db.directed_snusk("raek"))
    print(db.example_snusk("don", "donet"))
    db._save()
