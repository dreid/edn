import datetime
import uuid

import iso8601
from perfidy import frozendict

from ._ast import (
    Keyword,
    Symbol,
    TaggedValue,
    parse,
    unparse,
)


# TODO(jml):
# - write code that turns AST into Python objects
#   - perfidious ones
#   - regular ones
#   [probably parametrize with some term -> constructor map]
# - write code that turns Python objects into AST
# - probably put the top level of convenience (dumps/loads) in
#   yet another module

# TODO(jml)
#
# Almost 100% of the extension is going to be turning a domain-specific object
# into a tagged value and back.  Make sure there's a good API for that.



def constantly(x):
    return lambda *a, **kw: x


_DECODERS = frozendict({
    '.tuple.': lambda *a: a,
    'Character': unicode,
    'String': unicode,
    'Vector': tuple,
    'List': tuple,
    'Map': frozendict,
    'Set': frozenset,
    'Symbol': Symbol,
    'Keyword': Keyword,
})


INST = Symbol('inst')
UUID = Symbol('uuid')


DEFAULT_READERS = frozendict({
    INST: iso8601.parse_date,
    UUID: uuid.UUID,
})


class _Decoder(object):

    def __init__(self, decoders, readers, default):
        if not readers:
            readers = frozendict()
        self._readers = readers
        self._decoders = decoders.with_pair(
            'TaggedValue', self._handle_tagged_value)
        if not default:
            default = TaggedValue
        self._default = default

    def _handle_tagged_value(self, symbol, value):
        reader = self._readers.get(symbol)
        if reader:
            return reader(value)
        return self._default(symbol, value)

    def leafTag(self, tag, span):
        decoder = self._decoders.get(tag.name, None)
        if not decoder:
            raise ValueError("Cannot decode %r" % (tag.name,))
        return decoder

    def leafData(self, data, span=None):
        return constantly(data)

    def term(self, f, terms):
        return f(*terms)


def decode(obj, readers=frozendict(), default=None):
    # XXX: Maybe leave this level policy-free, passing in _DECODERS and
    # DEFAULT_READERS and leave the default policy shenanigans up to loads
    builder = _Decoder(_DECODERS, DEFAULT_READERS.merge(readers), default)
    build = getattr(obj, 'build', None)
    if build:
        return build(builder)
    return builder.leafData(obj)(obj)


def loads(string, readers=frozendict()):
    return decode(parse(string), readers)


def tagger(tag, function):
    def wrapped(*args, **kwargs):
        return TaggedValue(tag, function(*args, **kwargs))
    return wrapped


# XXX: This is a poor way of doing type-based dispatch.  Some thoughts:
# - are we sure that we _always_ want to do type-based dispatch?  the
#   most flexible way to do this is to have arbritrary predicates, or
#   a list of functions that return some marker value if they don't
#   know what to do
# - clojure does typed-based dispatch, but it has multimethods
# - if we did type-based dispatch, we could use Python's ABC, I guess.
# - does it make sense to allow callers to override the behaviour of
#   the standard types, e.g. to encode bools differently
# - does it even make sense to allow callers to overwrite the
#   built-in write handlers?  the current API requires you specify them.
# - perhaps a global registry wouldn't be such a bad thing?


DEFAULT_WRITE_HANDLERS = [
    (datetime.datetime, tagger(INST, lambda x: x.isoformat())),
    (uuid.UUID, tagger(UUID, str)),
]


def dumps(obj, write_handlers=None):
    if write_handlers is None:
        write_handlers = DEFAULT_WRITE_HANDLERS

    for base_type, function in write_handlers:
        if isinstance(obj, base_type):
            obj = function(obj)
            break

    return unparse(obj)
