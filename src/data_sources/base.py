from abc import ABC, abstractmethod

from ..models.book import Book


class BaseDataSource(ABC):
    """数据源抽象基类"""

    @abstractmethod
    def fetch_new_books(self, months: int = 12) -> list[Book]:
        """抓取近期出版的书"""

    @abstractmethod
    def fetch_book_detail(self, book: Book) -> Book:
        """获取单本书的详情（简介+目录等）"""
