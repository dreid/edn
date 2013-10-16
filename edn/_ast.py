"""Abstract syntax for edn.

Roughly speaking, every edn element gets its own terml symbol.  Thus, an edn
stream consisting of a vector of two strings, e.g.::

  ["foo" "bar"]

Will be mapped to::

  Vector((String(u'foo'), String(u'bar')))

Beyond that::

  #foo 42 <=> TaggedValue(Symbol('foo'), 42)
  :my/keyword <=> Keyword(Symbol('keyword', 'my'))
  my/symbol <=> Symbol('symbol', 'my')
"""

from functools import partial
import os

from parsley import makeGrammar
from terml.nodes import coerceToTerm, termMaker as t

from ._parsley import iterGrammar, parseGrammar


Character = t.Character
ExactFloat = t.ExactFloat
Keyword = t.Keyword
List = t.List
Map = t.Map
Nil = t.Nil()
Set = t.Set
String = t.String
Symbol = t.Symbol
TaggedValue = t.TaggedValue
Vector = t.Vector


def Float(value, exact):
    if exact:
        return ExactFloat(value)
    return float(value)


_edn_grammar_file = os.path.join(os.path.dirname(__file__), 'edn.parsley')
_edn_grammar_definition = open(_edn_grammar_file).read()

_edn_bindings = {
    'Character': Character,
    'Float': Float,
    'String': String,
    'Symbol': Symbol,
    'Keyword': Keyword,
    'Vector': Vector,
    'TaggedValue': TaggedValue,
    'Map': Map,
    'Nil': Nil,
    'Set': Set,
    'List': List,
}

_parsed_edn = parseGrammar(_edn_grammar_definition, 'edn')
edn = makeGrammar(_edn_grammar_definition, _edn_bindings, name='edn')


def parse(string):
    """Parse a single edn element.

    Returns an abstract representation of a single edn element.
    """
    return edn(string).edn()


def parse_stream(stream):
    return iterGrammar(_parsed_edn, _edn_bindings, 'edn', stream)


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

    def _dump_ExactFloat(self, obj):
        return '%sM' % (obj,)

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


def unparse_stream(input_elements, output_stream):
    """Write abstract edn elements out as edn to a file-like object.

    Elements will be separated by UNIX newlines.  This may change in future
    versions.
    """
    separator = u'\n'.encode('utf8')
    builder = _Builder()
    for element in input_elements:
        output_stream.write(coerceToTerm(element).build(builder))
        output_stream.write(separator)
