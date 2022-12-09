"""
An class which wraps an iterator and stores the next item in a field
calling next will return the already stored item and store the next item
next returns the items of the underlying iterator and a boolean which is True as long there is a next item
"""
primitives = (int, float, str, bool, type(None))

class LastItemIterator:
    def __init__(self, iterator):
        self.iterator = iterator
        try:
            self.next_item = next(iterator)
        except StopIteration:
            self.next_item = None
        except TypeError:
            self.iterator = None
            self.next_item = None

    def __next__(self):
        if self.next_item is None:
            raise StopIteration

        item = self.next_item
        try:
            self.next_item = next(self.iterator)
        except StopIteration:
            self.next_item = None

        if hasattr(item, "__iter__") and type(item) not in primitives:
            return self.next_item is None, *item
        else:
            return self.next_item is None, item

    def __iter__(self):
        return self

def lii(data):
    try:
        return LastItemIterator(iter(data))
    except TypeError:
        return LastItemIterator(data)
