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


def _dump_bool(obj):
    if obj:
        return 'true'
    else:
        return 'false'


def _dump_str(obj):
    return '"%s"' % (repr(obj)[1:-1].replace('"', '\\"'),)


def _dump_symbol(obj):
    if obj.prefix:
        return '/'.join([obj.prefix, obj.name])
    return obj.name


def dumps(obj):
    # XXX: It occurs to me that the 'e' in 'edn' means that there should be a
    # way to extend this -- jml
    RULES = [
        (bool, _dump_bool),
        (int, str),
        (float, str),
        (str, _dump_str),
        (type(None), lambda x: 'nil'),
        (Symbol, _dump_symbol),
    ]
    for base_type, dump_rule in RULES:
        if isinstance(obj, base_type):
            return dump_rule(obj)
    raise ValueError("Cannot encode %r" % (obj,))
