def string(format, **kwargs):
    return format.format(**kwargs)

def object(object, format):
    if hasattr(object, '__format__'):
        return object.__format__(format)

    return None