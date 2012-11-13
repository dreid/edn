from collections import namedtuple

from parsley import makeGrammar

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

edn = makeGrammar(open('edn.parsley').read(),
                  {
                    'Symbol': Symbol,
                    'Keyword': Keyword,
                    'Vector': Vector,
                    'TaggedValue': TaggedValue
                  },
                  name='edn')


# Tests
import unittest


class EDNTestCase(unittest.TestCase):
    def test_nil(self):
        self.assertEqual(edn("nil").nil(), None)

    def test_boolean(self):
        self.assertTrue(edn("true").boolean())
        self.assertFalse(edn("false").boolean())

    def test_string(self):
        assert edn('"foo"').string() == "foo"
        assert edn("""\"
foo
bar
baz\"""").string() == '\nfoo\nbar\nbaz'

    def test_character(self):
        assert edn(r"\c").character() == "c"
        assert edn(r"\newline").character() == "\n"
        assert edn(r"\tab").character() == "\t"
        assert edn(r"\return").character() == "\r"
        assert edn(r"\space").character() == " "

    def test_symbol(self):
        assert edn("foo").symbol() == Symbol("foo")
        assert edn(".foo").symbol() == Symbol(".foo")
        assert edn("/").symbol() == Symbol("/")
        assert edn("foo/bar").symbol() == Symbol("bar", "foo")

    def test_keyword(self):
        assert edn(":foo").keyword() == Keyword("foo")
        assert edn("foo").symbol() != edn(":foo").keyword()

    def test_integer(self):
        integers = [("-0", -0),
                    ("-10", -10),
                    ("10", 10),
                    ("+10", 10),
                    ("10000N", 10000L)]

        for edn_str, expected in integers:
            self.assertEqual(edn(edn_str).integer(), expected)

    def test_list(self):
        lists = [("()", ()),
                 ("(1)", (1,)),
                 ("(\"foo\" 1 foo :bar)", ("foo", 1, Symbol("foo"), Keyword("bar"))),
                 ("(((foo) bar)\n\t baz)",
                  (((Symbol("foo"),), Symbol("bar")), Symbol("baz")))]

        for edn_str, expected in lists:
            self.assertEqual(edn(edn_str).list(), expected)

    def test_vector(self):
        vectors = [("[]", Vector()),
                   ("[1]", Vector((1,))),
                   ("[foo]", Vector((Symbol("foo"),))),
                   ("[[foo] [bar]]", Vector((Vector((Symbol("foo"),)),
                                             Vector((Symbol("bar"),)))))]

        for edn_str, expected in vectors:
            self.assertEqual(edn(edn_str).vector(), expected)

    def test_map(self):
        maps = [("{}", {}),
                ("{1 2}", {1: 2}),
                ("{[1] {2 3}, (4 5 6), 7}",
                 {(1,): {2: 3}, (4, 5, 6): 7})]

        for edn_str, expected in maps:
            self.assertEqual(edn(edn_str).map(), expected)

    def test_set(self):
        sets = [("#{}", frozenset([])),
                ("#{1 2 3 4 :foo}", frozenset([1, 2, 3, 4, Keyword("foo")])),
                ("#{#{1 2} 3}", frozenset([frozenset([1, 2]), 3]))]

        for edn_str, expected in sets:
            self.assertEqual(edn(edn_str).set(), expected)

    def test_tag(self):
        self.assertEqual(edn('#foo/bar baz').tag(),
                         TaggedValue(Symbol('bar', 'foo'), Symbol('baz')))

    def test_comment(self):
        self.assertEqual(edn('; foo bar baz bax\nbar ; this is bar\n').edn(), Symbol('bar'))

    def test_discard(self):
        self.assertEqual(edn('[1 2 #_foo 3]').edn(), Vector([1, 2, 3]))


if __name__ == '__main__':
    import unittest
    unittest.main()
