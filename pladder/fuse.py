import enum
import json
import os


ALLOWED_RUNS = float("inf")


class FuseResult(enum.Enum):
    INTACT = 0
    JUST_BLOWN = 1
    BLOWN = 2


class Fuse:
    def __init__(self, state_dir):
        self.state_file_path = os.path.join(state_dir, "fuse.json")

    def run(self, dt, network, channel):
        if not channel.startswith("#"):
            # Private chats are unfused
            return FuseResult.INTACT
        date = f"{dt.year}-{dt.month:02}-{dt.day:02}"
        state = self._load()
        state = self._prune_old(state, date)
        new_count = self._increase(state, network, channel, date)
        self._store(state)
        if new_count <= ALLOWED_RUNS:
            return FuseResult.INTACT
        elif new_count == ALLOWED_RUNS + 1:
            return FuseResult.JUST_BLOWN
        else:
            return FuseResult.BLOWN

    def _load(self):
        try:
            with open(self.state_file_path, "rt", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def _prune_old(self, state, date):
        result = {}
        for network, channels in state.items():
            channels = {channel: entry
                        for channel, entry in channels.items()
                        if entry["date"] == date}
            if channels:
                result[network] = channels
        return result

    def _increase(self, state, network, channel, date):
        default_entry = {
            "count": 0,
            "date": date,
        }
        entry = state.setdefault(network, {}).setdefault(channel, default_entry)
        entry["count"] += 1
        return entry["count"]

    def _store(self, state):
        with open(self.state_file_path, "wt", encoding="utf-8") as f:
            json.dump(state, f, sort_keys=True, indent=4)
