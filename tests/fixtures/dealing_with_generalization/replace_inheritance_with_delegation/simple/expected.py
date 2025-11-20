class Stack:
    def __init__(self):
        self._items = []

    def push(self, element):
        self._items.append(element)

    def pop(self):
        return self._items.pop()

    def size(self):
        return len(self._items)
