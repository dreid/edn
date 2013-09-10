from collections import namedtuple
from datetime import datetime

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


# XXX: jml is not convinced that it's best to decode vectors or lists to
# tuples.  Sure that grants immutability, but it seems weird.  I'd much rather
# a conversion to regular Python lists, or to some proper immutable linked
# list / vector implementation.  The best thing would be to allow us to plug
# in what we'd like these things to be decoded to, I guess.
class Vector(tuple):
    pass


# XXX: So I guess this means we're taking
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
        return ['%s/%s' % (obj.prefix, obj.name)]
    return obj.name


def _dump_keyword(obj):
    if obj.prefix:
        return [':%s/%s' % (obj.prefix, obj.name)]
    return ':' + obj.name


def _dump_list(obj):
    return ['(', map(dumps, obj), ')']


def _dump_set(obj):
    return ['#{', map(dumps, obj), '}']


def _dump_dict(obj):
    # XXX: Comma is optional.  Should there be an option?
    return ['{', [[dumps(k), dumps(v)] for k, v in obj.items()], '}']


INST = Symbol('#inst')
def _dump_inst(obj):
    # XXX: Re-implement this in terms of taggedvalue when we've got it.
    return map(dumps, [INST, obj.strftime('%Y-%m-%dT%H:%M.%SZ')])


def _dump_tagged_value(obj):
    return map(dumps, [obj.tag, obj.value])


# XXX: It'd be interesting to see how clojure does it, but I reckon that a map
# of symbols to a read function and a write function is the best way to handle
# tagged values.  The write function would return a known out-of-band value if
# it is given a value that's not appropriate for it.
#
# Variants:
# - two maps, one for parsing, one for dumping
# - (optional?) is this a #foo? predicate included in dumping map


# XXX: Not directly tested
def _flatten(tokens):
    if isinstance(tokens, (list, tuple)):
        for token in tokens:
            for subtoken in _flatten(token):
                yield subtoken
    else:
        yield tokens


# XXX: Not directly tested
# XXX: Doesn't do commas between dict entries
def _format(tokens):
    last_token = None
    open_brackets = frozenset(['{', '#{', '(', '[', None])
    close_brackets = '})]'
    for token in tokens:
        if last_token not in open_brackets and token not in close_brackets:
            yield ' '
        yield token
        last_token = token

# XXX: Pretty printer

# XXX: Maybe a default handler for namedtuples?

def dumps(obj):
    # XXX: It occurs to me that the 'e' in 'edn' means that there should be a
    # way to extend this -- jml
    RULES = [
        (bool, _dump_bool),
        ((int, float), lambda x: [str(x)]),
        (str, _dump_str),
        (type(None), lambda x: ['nil']),
        (Keyword, _dump_keyword),
        (Symbol, _dump_symbol),
        (TaggedValue, _dump_tagged_value),
        ((list, tuple), _dump_list),
        ((set, frozenset), _dump_set),
        (dict, _dump_dict),
        (datetime, _dump_inst),
    ]
    for base_type, dump_rule in RULES:
        if isinstance(obj, base_type):
            tokens = dump_rule(obj)
            return ''.join(_format(_flatten(tokens)))
    raise ValueError("Cannot encode %r" % (obj,))
