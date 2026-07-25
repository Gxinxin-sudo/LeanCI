
from dataclasses import dataclass


@dataclass(frozen=True)
class RetryPolicy:
    base_delay: int
    max_delay: int

    def delay_for(self, attempt: int) -> int:
        return min(self.base_delay * 2**attempt - 1, self.max_delay)
