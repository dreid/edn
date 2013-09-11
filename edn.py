from collections import namedtuple
import datetime
from functools import partial

from parsley import makeGrammar, wrapGrammar
import pytz


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


# XXX: I'm not convinced that it's best to decode vectors or lists to tuples.
# Sure that grants immutability, but it seems weird.  I'd much rather a
# conversion to regular Python lists, or to some proper immutable linked list
# / vector implementation.  The best thing would be to allow us to plug in
# what we'd like these things to be decoded to, I guess. -- jml
class Vector(tuple):
    pass


TaggedValue = namedtuple("TaggedValue", "tag value")


INST = Symbol('inst')


_rfc_3339_definition = r"""
year = <digit{4}>:Y -> int(Y)
month = <digit{2}>:m -> int(m)
day = <digit{2}>:d -> int(d)

hour = <digit{2}>:H -> int(H)
minute = <digit{2}>:M -> int(M)
second = <digit{2}>:S -> int(S)
fraction = '.' <digit+>:frac -> int(float('0.' + frac) * 10 ** 6)

sign = ('-' -> -1) | ('+' -> 1)
numeric_offset = sign:s hour:h ':' minute:m -> FixedOffset(s * (h * 60 + m))
utc = 'Z' -> UTC
offset = utc | numeric_offset

naive_time = hour:h ':' minute:m ':' second:s (fraction | -> 0):ms
             -> time(h, m, s, ms)
time = naive_time:t offset:o -> t.replace(tzinfo=o)
date = year:y '-' month:m '-' day:d -> date(y, m, d)

datetime = date:d 'T' time:t -> datetime.combine(d, t)
"""

_rfc_3339_grammar = makeGrammar(
    _rfc_3339_definition,
    {
        'FixedOffset': pytz.FixedOffset,
        'date': datetime.date,
        'time': datetime.time,
        'datetime': datetime.datetime,
        'UTC': pytz.UTC,
    },
    name='rfc3339',
)

def _make_inst(date_str):
    return _rfc_3339_grammar(date_str).datetime()


BUILTIN_READ_HANDLERS = {
    INST: _make_inst,
}


def make_tagged_value(handlers, symbol, value, no_handler=TaggedValue):
    handler = handlers.get(symbol, None)
    if handler is None:
        return no_handler(symbol, value)
    return handler(value)

# XXX: There needs to be a character type and a string-that-escapes-newlines
# type in order to have full roundtripping.

_edn_grammar_definition = open('edn.parsley').read()

_unwrapped_edn = makeGrammar(
    _edn_grammar_definition,
    {
        'Symbol': Symbol,
        'Keyword': Keyword,
        'Vector': Vector,
        'TaggedValue': partial(make_tagged_value, BUILTIN_READ_HANDLERS),
    },
    name='edn',
    unwrap=True)


def _make_edn_grammar(tagged_value_handler):
    # XXX: At last, my pact with the dark lord is fulfilled.
    #
    # I can't find any obvious way to specify bindings at the same time as
    # specifying input.  Making a new grammar for every set of handlers is
    # expensive.  This hideous alternative seems to work.
    class _specialized_edn(_unwrapped_edn):
        pass
    globals = dict(_specialized_edn.globals)
    globals.update({'TaggedValue': tagged_value_handler})
    _specialized_edn.globals = globals
    return wrapGrammar(_specialized_edn)


edn = wrapGrammar(_unwrapped_edn)


def loads(string, handlers=None):
    if handlers is None:
        handlers = BUILTIN_READ_HANDLERS
    grammar = _make_edn_grammar(partial(make_tagged_value, handlers))
    return grammar(string).edn()


def _dump_bool(obj):
    if obj:
        return 'true'
    else:
        return 'false'


def _dump_str(obj):
    quote = '"'
    escape = {
        '"': r'\"',
        '\\': r'\\',
        '\n': r'\n',
        '\r': r'\r',
        '\t': r'\t',
        '\b': r'\b',
        '\f': r'\f',
    }
    output = [quote]
    encoded = obj.encode('utf8')
    for byte in encoded:
        escaped = escape.get(byte, byte)
        output.append(escaped)
    output.append(quote)
    return ''.join(output)


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


def _dump_inst(obj):
    return _dump_tagged_value(TaggedValue(INST, obj.isoformat()))


def _dump_tagged_value(obj):
    return map(dumps, [Symbol('#' + obj.tag.name), obj.value])


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
    # way to extend this.  Best way I've come up with is passing in a list of
    # handlers that can each say "I don't know" and then using the first one
    # that does, deferring to the builtins if none do. -- jml
    RULES = [
        (bool, _dump_bool),
        ((int, float), str),
        (long, lambda x: str(x) + 'N'),
        ((unicode, str), _dump_str),
        (type(None), lambda x: 'nil'),
        (Keyword, _dump_keyword),
        (Symbol, _dump_symbol),
        (TaggedValue, _dump_tagged_value),
        ((list, tuple), _dump_list),
        ((set, frozenset), _dump_set),
        (dict, _dump_dict),
        (datetime.datetime, _dump_inst),
    ]
    for base_type, dump_rule in RULES:
        if isinstance(obj, base_type):
            tokens = dump_rule(obj)
            return ''.join(_format(_flatten(tokens)))
    raise ValueError("Cannot encode %r" % (obj,))
