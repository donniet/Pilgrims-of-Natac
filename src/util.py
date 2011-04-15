__author__ = 'scott'

def enum(name, *sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    return type(name, (), enums)

