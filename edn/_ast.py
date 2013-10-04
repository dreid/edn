"""Abstract syntax for edn."""

from functools import partial
import os

from parsley import makeGrammar
from terml.nodes import coerceToTerm, termMaker as t


Character = t.Character
Keyword = t.Keyword
List = t.List
Map = t.Map
Nil = t.Nil()
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
        'Nil': Nil,
        'Set': Set,
        'List': List,
    },
    name='edn')


def parse(string):
    """Parse a single edn element.

    Returns an abstract representation of a single edn element.
    """
    return edn(string).edn()


def _wrap(start, end, *middle):
    return ''.join([start] + list(middle) + [end])


class _Builder(object):

    PRIMITIVES = (
        ((int, float), str),
        (long, lambda x: str(x) + 'N'),
        (unicode, unicode),
        (str, str),
    )

    def _dump_true(self):
        return 'true'

    def _dump_false(self):
        return 'false'

    def _dump_Nil(self):
        return 'nil'

    def _dump_Character(self, obj):
        return '\\' + obj

    def _dump_Keyword(self, obj):
        return ':' + obj

    def _dump_Symbol(self, name, prefix=None):
        if prefix:
            return '%s/%s' % (prefix, name)
        else:
            return name

    def _dump_TaggedValue(self, tag, value):
        return '#%s %s' % (tag, value)

    def _dump_String(self, obj):
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

    def _merge_elements(self, *elements):
        return ' '.join(elements)

    def leafTag(self, tag, span):
        if tag.name == '.tuple.':
            return self._merge_elements
        return getattr(self, '_dump_%s' % (tag.name,))

    def leafData(self, data, span=None):
        for base_type, dump_rule in self.PRIMITIVES:
            if isinstance(data, base_type):
                return lambda *args: dump_rule(data)
        raise ValueError("Cannot encode %r" % (data,))

    def term(self, f, built_terms):
        return f(*built_terms)


def unparse(obj):
    """Turn an abstract edn element into a string.

    Returns a valid edn string representing 'obj'.
    """
    builder = _Builder()
    return coerceToTerm(obj).build(builder)
