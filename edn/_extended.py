import datetime
import uuid

import iso8601
from perfidy import frozendict

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


# TODO(jml):
# - write code that turns Python objects into AST
# - probably put the top level of convenience (dumps/loads) in
#   yet another module

# TODO(jml)
#
# Almost 100% of the extension is going to be turning a domain-specific object
# into a tagged value and back.  Make sure there's a good API for that.

# XXX: Should there be exposed Keyword and Symbol objects that are *not*
# terms, but rather representing actual keywords and symbols?  Would make some
# things (e.g. type-based dispatch in encode) easier.

# XXX: Clarify what's exported at the top package level.


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


# XXX: This and the builder in _ast have roughly the same shape and similar
# problems (leafData is weird, shouldn't even need to handle '.tuple.',
# dispatch is inevitably on tag.name, 'term' method is almost guaranteed
# useless).  Muck around a bit with making a better direct API for term
# traversal in terml.

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
    # XXX: Maybe leave this level policy-free, passing in _DECODERS and
    # DEFAULT_READERS and leave the default policy shenanigans up to loads
    builder = _Decoder(_DECODERS, DEFAULT_READERS.merge(readers), default)
    build = getattr(term, 'build', None)
    if build:
        return build(builder)
    return builder.leafData(term)(term)


# XXX: 'decode' and 'encode' aren't great names.

# XXX: 'reader' terminology lifted from
# http://clojure.github.io/clojure/clojure.edn-api.html but the format talks
# of 'handlers'.


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


def _encode_map(obj):
    return Map([(encode(k), encode(v)) for k, v in obj.items()])


# Basic mapping from core Python types to edn AST elements
# Also includes logic on how to traverse down.
_BASE_ENCODING_RULES = (
    ((str, unicode), String),
    ((dict, frozendict), _encode_map),
    ((set, frozenset), lambda obj: Set(map(encode, obj))),
    (tuple, lambda obj: List(map(encode, obj))),
    (list,  lambda obj: Vector(map(encode, obj))),
    (datetime.datetime,
     lambda obj: TaggedValue(INST, String(obj.isoformat()))),
    (uuid.UUID,
     lambda obj: TaggedValue(UUID, String(str(obj)))),
)


def encode(obj):
    """Take a Python object and return an edn AST."""
    # TODO(jml): Handle custom writers
    # TODO(jml): Use a frozendict rather than if/else
    # TODO(jml): Possibly refactor to separate Python object traversal
    # Separate logic since we can't do isinstance checks on these.
    if _get_tag_name(obj) in ('Keyword', 'Symbol'):
        return obj
    else:
        for base_types, encoder in _BASE_ENCODING_RULES:
            if isinstance(obj, base_types):
                return encoder(obj)
        # For unknown types, just return the object and hope for the best.
        #
        # XXX: Perhaps create an unknown_handler, and also base rules for
        # encoding supported types like int, float, and so forth.
        return obj


def dumps(obj):
    return unparse(encode(obj))
