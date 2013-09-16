from collections import namedtuple
import datetime
from functools import partial
import os
import uuid

from parsley import makeGrammar, wrapGrammar
import iso8601


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


INST = Symbol('inst')
UUID = Symbol('uuid')


BUILTIN_READ_HANDLERS = {
    INST: iso8601.parse_date,
    UUID: uuid.UUID,
}


def make_tagged_value(handlers, symbol, value, no_handler=TaggedValue):
    handler = handlers.get(symbol, None)
    if handler is None:
        return no_handler(symbol, value)
    return handler(value)

# XXX: There needs to be a character type and a string-that-escapes-newlines
# type in order to have full roundtripping.

_edn_grammar_file = os.path.join(os.path.dirname(__file__), 'edn.parsley')
_edn_grammar_definition = open(_edn_grammar_file).read()

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


def _dump_list(xs, write_handlers=None):
    return ['(', [dumps(x, write_handlers) for x in xs], ')']


def _dump_set(xs, write_handlers=None):
    return ['#{', [dumps(x, write_handlers) for x in xs], '}']


def _dump_dict(obj, write_handlers=None):
    # XXX: Comma is optional.  Should there be an option?
    return ['{', [[dumps(k, write_handlers), dumps(v, write_handlers)]
                  for k, v in obj.items()], '}']


def _dump_tagged_value(obj):
    return map(dumps, [Symbol('#' + obj.tag.name), obj.value])


# XXX: Not directly tested
def _flatten(tokens):
    if isinstance(tokens, (list, tuple)):
        for token in tokens:
            for subtoken in _flatten(token):
                yield subtoken
    else:
        yield tokens


# XXX: Not directly tested
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


def tagger(tag, function):
    def wrapped(*args, **kwargs):
        return TaggedValue(tag, function(*args, **kwargs))
    return wrapped


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

    RULES = [
        (bool, _dump_bool),
        ((int, float), str),
        (long, lambda x: str(x) + 'N'),
        ((unicode, str), _dump_str),
        (type(None), lambda x: 'nil'),
        (Keyword, _dump_keyword),
        (Symbol, _dump_symbol),
        (TaggedValue, _dump_tagged_value),
        ((list, tuple), lambda x: _dump_list(x, write_handlers)),
        ((set, frozenset), lambda x: _dump_set(x, write_handlers)),
        (dict, lambda x: _dump_dict(x, write_handlers)),
    ]
    for base_type, dump_rule in RULES:
        if isinstance(obj, base_type):
            tokens = dump_rule(obj)
            return ''.join(_format(_flatten(tokens)))
    raise ValueError("Cannot encode %r" % (obj,))
