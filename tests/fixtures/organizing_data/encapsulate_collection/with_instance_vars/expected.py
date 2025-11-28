"""Example code for encapsulate-collection with instance variables."""


class Library:
    def __init__(self, name):
        self.name = name
        self._books = []
        self.member_count = 0

    def get_books(self):
        return tuple(self._books)

    def add_member(self):
        self.member_count += 1

    def get_summary(self):
        return f"{self.name}: {len(self.books)} books, {self.member_count} members"

    def add_book(self, book):
        self._books.append(book)

    def remove_book(self, book):
        self._books.remove(book)
