import datetime
import os
import uuid

import iso8601
from parsley import makeGrammar
from terml.nodes import termMaker as t


Character = t.Character
Keyword = t.Keyword
List = t.List
Map = t.Map
Set = t.Set
String = t.String
Symbol = t.Symbol
TaggedValue = t.TaggedValue
Vector = t.Vector


INST = t.Symbol('inst')
UUID = t.Symbol('uuid')


BUILTIN_READ_HANDLERS = {
    INST: iso8601.parse_date,
    UUID: uuid.UUID,
}


_edn_grammar_file = os.path.join(os.path.dirname(__file__), 'edn.parsley')
_edn_grammar_definition = open(_edn_grammar_file).read()

edn = makeGrammar(
    _edn_grammar_definition,
    {
        'Character': Character,
        'String': String,
        'Symbol': Symbol,
        'Keyword': Keyword,
        'Vector': Vector,
        'TaggedValue': TaggedValue,
        'Map': Map,
        'Set': Set,
        'List': List,
    },
    name='edn')


def loads(string, handlers=None):
    if handlers is None:
        handlers = BUILTIN_READ_HANDLERS
    return edn(string).edn()


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
    return map(dumps, [t.Symbol('#' + obj.tag.name), obj.value])


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
        return t.TaggedValue(tag, function(*args, **kwargs))
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
        (t.Keyword, _dump_keyword),
        (t.Symbol, _dump_symbol),
        (t.TaggedValue, _dump_tagged_value),
        ((list, tuple), lambda x: _dump_list(x, write_handlers)),
        ((set, frozenset), lambda x: _dump_set(x, write_handlers)),
        (dict, lambda x: _dump_dict(x, write_handlers)),
    ]
    for base_type, dump_rule in RULES:
        if isinstance(obj, base_type):
            tokens = dump_rule(obj)
            return ''.join(_format(_flatten(tokens)))
    raise ValueError("Cannot encode %r" % (obj,))
