from abc import ABC, abstractmethod


class KeyboardLayoutId(ABC):
    @property
    @abstractmethod
    def to_string(self) -> str:
        pass

    def __hash__(self):
        return hash(self.to_string)

    def __eq__(self, other: "KeyboardLayoutId"):
        return self.to_string == other.to_string

    def __repr__(self):
        return self.to_string
