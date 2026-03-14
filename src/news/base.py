"""
Abstract base for news sources.
Every news source must implement fetch() → list[RawNewsItem].
"""
from abc import ABC, abstractmethod

from src.models.events import RawNewsItem, SourceTier


class NewsSource(ABC):
    """Base class for all news sources."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable source name."""

    @property
    @abstractmethod
    def tier(self) -> SourceTier:
        """Reliability tier of this source."""

    @abstractmethod
    def fetch(self) -> list[RawNewsItem]:
        """Fetch latest news items from this source."""

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, tier={self.tier})"
