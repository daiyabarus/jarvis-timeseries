from enum import Enum


class ExlEnum(str, Enum):
    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))

    def __str__(self) -> str:
        return str.__str__(self)


class EnumLower(ExlEnum):
    def _generate_next_value_(name, start, count, last_values):
        return f"{str(name).lower()}"


class EnumUpper(ExlEnum):
    def _generate_next_value_(name, start, count, last_values):
        return f"{str(name).upper()}"
