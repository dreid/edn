import datetime
import uuid

import iso8601
from perfidy import (
    caller,
    frozendict,
)

from ._ast import (
    Keyword,
    List,
    Map,
    Set,
    String,
    Symbol,
    TaggedValue,
    Vector,
    parse,
    unparse,
)


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


def decode(term, readers=frozendict(), default=None):
    """Take a parsed edn term and return a useful Python object.

    :param term: A parsed edn term, probably got from `edn.parse`.
    :param readers: A map from tag symbols to callables.  For '#foo bar'
        whatever callable the Symbol('foo') key is mapped to will be
        called with 'bar'.  There are default readers for #inst and #uuid,
        which can be overridden here.
    :param default: callable taking a symbol & value that's called when
        there's no tag symbol in the reader.
    :return: Whatever term gets decoded to.
    """
    builder = _Decoder(_DECODERS, DEFAULT_READERS.merge(readers), default)
    build = getattr(term, 'build', None)
    if build:
        return build(builder)
    return builder.leafData(term)(term)


def loads(string, readers=frozendict(), default=None):
    """Interpret an edn string.

    :param term: A parsed edn term, probably got from `edn.parse`.
    :param readers: A map from tag symbols to callables.  For '#foo bar'
        whatever callable the Symbol('foo') key is mapped to will be
        called with 'bar'.  There are default readers for #inst and #uuid,
        which can be overridden here.
    :return: Whatever the string is interpreted as.
    """
    return decode(parse(string), readers, default)


def _get_tag_name(obj):
    tag = getattr(obj, 'tag', None)
    if tag:
        return getattr(tag, 'name', None)


def _make_tag_rule(tag, writer):
    return lambda obj: TaggedValue(tag, encode(writer(obj)))


DEFAULT_WRITERS = (
    (datetime.datetime, INST, caller('isoformat')),
    (uuid.UUID, UUID, str),
)


def encode(obj, writers=()):
    """Take a Python object and return an edn AST."""
    # Basic mapping from core Python types to edn AST elements
    # Also includes logic on how to traverse down.
    _base_encoding_rules = (
        ((str, unicode), String),
        ((dict, frozendict),
         lambda x: Map(
             [(encode(k, writers), encode(v, writers))
              for k, v in obj.items()])),
        ((set, frozenset), lambda obj: Set([encode(x, writers) for x in obj])),
        (tuple, lambda obj: List([encode(x, writers) for x in obj])),
        (list,  lambda obj: Vector([encode(x, writers) for x in obj])),
    )

    rules = (
        tuple(
            (base_types, _make_tag_rule(tag, writer))
            for base_types, tag, writer in tuple(writers) + DEFAULT_WRITERS)
        + _base_encoding_rules)

    # Separate logic since we can't do isinstance checks on these.
    if _get_tag_name(obj) in ('Keyword', 'Symbol'):
        return obj
    else:
        for base_types, encoder in rules:
            if isinstance(obj, base_types):
                return encoder(obj)
        # For unknown types, just return the object and hope for the best.
        return obj


def dumps(obj, writers=()):
    return unparse(encode(obj, writers))
