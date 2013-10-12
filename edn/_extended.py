"""Turns edn ASTs into Python objects and back.

An edn AST is a terml term that looks something like::

  Vector((String(u'foo'), String(u'bar'), 43))

Which can be turned into a Python object::

  [u"foo", u"bar", 43]
"""

import datetime
from decimal import Decimal
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
    Nil,
    Set,
    String,
    Symbol,
    TaggedValue,
    Vector,
    parse,
    unparse,
)


def identity(x):
    return x


def constantly(x):
    return lambda *a, **kw: x


_DECODERS = frozendict({
    '.tuple.': lambda *a: a,
    'Character': unicode,
    'ExactFloat': Decimal,
    'String': unicode,
    'Vector': tuple,
    'List': tuple,
    'Map': frozendict,
    'Nil': constantly(None),
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


def from_terms(term, readers=frozendict(), default=None):
    """Take a parsed edn term and return a useful Python object.

    :param term: A parsed edn term, probably got from `edn.parse`.
    :param readers: A map from tag symbols to callables.  For '#foo bar'
        whatever callable the Symbol('foo') key is mapped to will be
        called with 'bar'.  There are default readers for #inst and #uuid,
        which can be overridden here.
    :param default: callable taking a symbol & value that's called when
        there's no tag symbol in the reader.  It gets the symbol and the
        interpreted value, and can return whatever Python object it pleases.
    :return: Whatever term gets decoded to.
    """
    builder = _Decoder(_DECODERS, DEFAULT_READERS.merge(readers), default)
    build = getattr(term, 'build', None)
    if build:
        return build(builder)
    return builder.leafData(term)(term)


def loads(string, readers=frozendict(), default=None):
    """Interpret an edn string.

    See https://github.com/edn-format/edn.

    :param string: A UTF-8 encoded string containing edn data.
    :param readers: A map from tag symbols to callables.  For '#foo bar'
        whatever callable the Symbol('foo') key is mapped to will be
        called with 'bar'.  There are default readers for #inst and #uuid,
        which can be overridden here.
    :param default: Called whenever we come across a tagged value that is not
        mentioned in `readers'.  It gets the symbol and the interpreted value,
        and whatever it returns is how that value will be interpreted.
    :return: A Python object representing the edn element.
    """
    return from_terms(parse(string), readers, default)


def _get_tag_name(obj):
    tag = getattr(obj, 'tag', None)
    if tag:
        return getattr(tag, 'name', None)


def _make_tag_rule(tag, writer):
    return lambda obj: TaggedValue(tag, to_terms(writer(obj)))


DEFAULT_WRITERS = (
    (datetime.datetime, INST, caller('isoformat')),
    (uuid.UUID, UUID, str),
)


def _default_handler(obj):
    raise ValueError("Cannot convert %r to edn" % (obj,))


def to_terms(obj, writers=(), default=_default_handler):
    """Take a Python object and return an edn AST."""
    # Basic mapping from core Python types to edn AST elements
    # Also includes logic on how to traverse down.
    #
    # We can't define these externally yet because the definitions need to
    # refer to this function, along with custom writers.
    def recurse(x):
        return to_terms(x, writers, default)

    _base_encoding_rules = (
        ((str, unicode), String),
        ((dict, frozendict),
         lambda x: Map([(recurse(k), recurse(v)) for k, v in obj.items()])),
        ((set, frozenset), lambda obj: Set(map(recurse, obj))),
        (tuple, lambda obj: List(map(recurse, obj))),
        (list,  lambda obj: Vector(map(recurse, obj))),
        (type(None), constantly(Nil)),
        ((int, float), identity),
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
        return recurse(default(obj))


def dumps(obj, writers=(), default=_default_handler):
    return unparse(to_terms(obj, writers, default))
