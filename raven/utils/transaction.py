from __future__ import absolute_import

from threading import local


class TransactionStack(local):
    def __init__(self):
        self.stack = []

    def __len__(self):
        return len(self.stack)

    def __iter__(self):
        return iter(self.stack)

    def peek(self):
        try:
            return self.stack[-1]
        except IndexError:
            return None

    def push(self, context):
        self.stack.append(context)
        return context

    def pop(self, context=None):
        if context is None:
            return self.stack.pop()

        while self.stack:
            if self.stack.pop() is context:
                return context
