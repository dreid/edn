from functools import partial
import os

from parsley import makeGrammar
from terml.nodes import coerceToTerm, termMaker as t


Character = t.Character
Keyword = t.Keyword
List = t.List
Map = t.Map
Set = t.Set
String = t.String
Symbol = t.Symbol
TaggedValue = t.TaggedValue
Vector = t.Vector


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


def parse(string):
    return edn(string).edn()


def _dump_bool(obj):
    if obj:
        return 'true'
    else:
        return 'false'


def _wrap(start, end, middle):
    return ''.join([start] + middle + [end])


class _Builder(object):

    PRIMITIVES = (
        ((int, float), str),
        (long, lambda x: str(x) + 'N'),
        (unicode, unicode),
        (str, str),
    )

    def _dump_true(self, obj):
        return 'true'

    def _dump_false(self, obj):
        return 'false'

    def _dump_null(self, obj):
        return 'nil'

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


def unparse(obj):
    builder = _Builder()
    return coerceToTerm(obj).build(builder)
