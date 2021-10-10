from typing import NamedTuple


class Token(NamedTuple):
    name: str
    used: int
    use_count: int
    created: int
    creator_network: str
    creator_user: str
