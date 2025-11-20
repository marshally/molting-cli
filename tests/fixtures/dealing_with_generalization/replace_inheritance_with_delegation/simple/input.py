class Stack(list):
    def push(self, element):
        self.append(element)

    def pop(self):
        return super().pop()

    def size(self):
        return len(self)
