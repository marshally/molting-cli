from typing import Protocol


class Billable(Protocol):
    def get_rate(self) -> float: ...

    def has_special_skill(self) -> bool: ...


class Employee:
    def __init__(self, name, rate, special_skill):
        self.name = name
        self.rate = rate
        self.special_skill = special_skill

    def get_rate(self):
        return self.rate

    def has_special_skill(self):
        return self.special_skill is not None

    def get_name(self):
        return self.name
