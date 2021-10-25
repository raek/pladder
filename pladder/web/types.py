from typing import NamedTuple


NETWORK = "Web"
UNKNOWN_USER = "(unknown user)"


class Token(NamedTuple):
    name: str
    used: int
    use_count: int
    created: int
    creator_network: str
    creator_user: str
