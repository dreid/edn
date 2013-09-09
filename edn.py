from collections import namedtuple

from parsley import makeGrammar

class Symbol(namedtuple("Symbol", "name prefix type")):
    _MARKER = object()

    def __new__(cls, name, prefix=None):
        return super(Symbol, cls).__new__(cls, name, prefix, Symbol._MARKER)


class Keyword(namedtuple("Keyword", "name prefix type")):
    _MARKER = object()

    def __new__(cls, name_or_symbol, prefix=None):
        name = name_or_symbol

        if isinstance(name_or_symbol, Symbol):
            name = name_or_symbol.name
            prefix = name_or_symbol.prefix

        return super(Keyword, cls).__new__(cls, name, prefix, Keyword._MARKER)


class Vector(tuple):
    pass


TaggedValue = namedtuple("TaggedValue", "tag value")

# XXX: There needs to be a character type and a string-that-escapes-newlines
# type in order to have full roundtripping.

edn = makeGrammar(open('edn.parsley').read(),
                  {
                    'Symbol': Symbol,
                    'Keyword': Keyword,
                    'Vector': Vector,
                    'TaggedValue': TaggedValue
                  },
                  name='edn')


def loads(string):
    return edn(string).edn()


def dumps(obj):
    if isinstance(obj, bool):
        if obj:
            return 'true'
        else:
            return 'false'
    elif isinstance(obj, int):
        return str(obj)
    elif isinstance(obj, float):
        # bwahahahahahaha
        return str(obj)
    elif isinstance(obj, str):
        return '"%s"' % (repr(obj)[1:-1].replace('"', '\\"'),)
    return 'nil'
