import datetime
from functools import partial
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


def _wrap(start, end, middle):
    return ''.join([start] + middle + [end])


class _Builder(object):

    PRIMITIVES = (
        (bool, _dump_bool),
        ((int, float), str),
        (long, lambda x: str(x) + 'N'),
        (type(None), lambda x: 'nil'),
        (unicode, unicode),
        (str, str),
    )

    def _dump_Character(self, obj):
        return '\\' + obj[0]

    def _dump_Keyword(self, obj):
        return ':' + obj[0]

    def _dump_Symbol(self, obj):
        if len(obj) == 2:
            return '%s/%s' % (obj[1], obj[0])
        elif len(obj) == 1:
            return obj[0]
        else:
            raise ValueError("Invalid symbol: %r" % (obj,))

    def _dump_TaggedValue(self, obj):
        [tag, value] = obj
        return '#%s %s' % (tag, value)

    def _dump_String(self, obj):
        obj = obj[0]
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

    _dump_List = partial(_wrap, '(', ')')
    _dump_Vector = partial(_wrap, '[', ']')
    _dump_Set = partial(_wrap, '#{', '}')
    _dump_Map = partial(_wrap, '{', '}')

    def leafTag(self, tag, span):
        if tag.name == '.tuple.':
            return ' '.join
        return getattr(self, '_dump_%s' % (tag.name,))

    def leafData(self, data, span=None):
        for base_type, dump_rule in self.PRIMITIVES:
            if isinstance(data, base_type):
                return lambda args: dump_rule(data)
        raise ValueError("Cannot encode %r" % (data,))

    def term(self, f, built_terms):
        return f(built_terms)


def serialize(obj):
    builder = _Builder()
    build = getattr(obj, 'build', None)
    if build:
        return build(builder)
    return builder.leafData(obj)(obj)


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

    return serialize(obj)
