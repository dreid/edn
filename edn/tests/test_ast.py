from StringIO import StringIO
import unittest

import parsley

from .._ast import (
    Character,
    ExactFloat,
    List,
    Keyword,
    Map,
    Nil,
    Set,
    String,
    Symbol,
    TaggedValue,
    Vector,
    edn,
    parse,
    parse_stream,
    unparse,
    unparse_stream,
)


class EDNTestCase(unittest.TestCase):

    def assertInvalid(self, rule, inputs):
        for i in inputs:
            self.assertRaises(parsley.ParseError, getattr(edn(i), rule))

    def assertRuleProduces(self, rule, pairs):
        inputs, expected = zip(*pairs)
        observed = [getattr(edn(i), rule)() for i in inputs]
        self.assertEqual(list(expected), observed)

    def test_nil(self):
        self.assertEqual(edn("nil").nil(), Nil)

    def test_boolean(self):
        self.assertTrue(edn("true").boolean())
        self.assertFalse(edn("false").boolean())

    def test_string(self):
        self.assertEqual(edn('"foo"').string(), String("foo"))
        self.assertEqual(edn("""\"
foo
bar
baz\"""").string(), String('\nfoo\nbar\nbaz'))

    def test_unicode(self):
        # https://github.com/edn-format/edn/issues/59
        snowman = u'\u2603'
        encoded = snowman.encode('utf-8')
        quoted = '"' + encoded + '"'
        self.assertEqual(edn(quoted).string(), String(snowman))

    def test_character(self):
        self.assertEqual(edn(r"\c").character(), Character("c"))
        self.assertEqual(edn(r"\newline").character(), Character("\n"))
        self.assertEqual(edn(r"\tab").character(), Character("\t"))
        self.assertEqual(edn(r"\return").character(), Character("\r"))
        self.assertEqual(edn(r"\space").character(), Character(" "))

    def test_symbol(self):
        symbols = [
            ('foo', Symbol('foo')),
            ('.foo', Symbol('.foo')),
            ('/', Symbol('/')),
            ('foo/bar', Symbol('bar', 'foo')),
            ('a', Symbol('a')),
            ('predicate?', Symbol('predicate?')),
            ('+foo', Symbol('+foo')),
            ('a1', Symbol('a1')),
            ('!foo', Symbol('!foo')),
            ('-$foo', Symbol('-$foo')),
            ('foo:bar', Symbol('foo:bar')),
            ('foo#bar', Symbol('foo#bar')),
            ('+:foo', Symbol('+:foo')),
        ]
        self.assertRuleProduces('symbol', symbols)

    def test_invalid_symbols(self):
        invalid = [
            '9aeuoeu',
            '-9aou',
            'foo^bar',
            '#foo',
            ':foo',
            '/foo',
            'foo/',
        ]
        self.assertInvalid('symbol', invalid)

    def test_keyword(self):
        self.assertEqual(edn(":foo").keyword(), Keyword(Symbol("foo")))
        self.assertEqual(
            edn(":foo/bar").keyword(), Keyword(Symbol("bar", "foo")))
        self.assertNotEqual(edn("foo").symbol(), edn(":foo").keyword())

    def test_integer(self):
        integers = [("-0", -0),
                    ("-10", -10),
                    ("10", 10),
                    ("+10", 10),
                    ("4", 4),
                    ("10000N", 10000L)]

        for edn_str, expected in integers:
            self.assertEqual(edn(edn_str).integer(), expected)

    def test_float(self):
        floats = (
            ('3.2', 3.2),
            ('+4.7', 4.7),
            ('+4.7M', ExactFloat('+4.7')),
            ('-11.8', -11.8),
            ('-11.8e2', -1180.0),
            ('97.4E-02', 0.974),
            ('97.4E-02M', ExactFloat('97.4E-02')),
            ('32M', ExactFloat('32')),
        )
        for edn_str, expected in floats:
            self.assertEqual(edn(edn_str).float(), expected)

    def test_bad_floats(self):
        floats = ('04M', '04.51', '-023.0', '4')
        for string in floats:
            self.assertRaises(parsley.ParseError, edn(string).float)

    def test_list(self):
        lists = [
            ("()", List(())),
            ("(1)", List((1,))),
            ("(\"foo\" 1 foo :bar)",
             List((String("foo"), 1, Symbol("foo"), Keyword(Symbol("bar"))))),
            ("(((foo) bar)\n\t baz)",
             List((List((List((Symbol("foo"),)), Symbol("bar"))),
                   Symbol("baz")))),
        ]

        for edn_str, expected in lists:
            self.assertEqual(edn(edn_str).list(), expected)

    def test_vector(self):
        vectors = [
            ("[]", Vector(())),
            ("[1]", Vector((1,))),
            ("[foo]", Vector((Symbol("foo"),))),
            ("[[foo] [bar]]", Vector((Vector((Symbol("foo"),)),
                                      Vector((Symbol("bar"),))))),
        ]

        for edn_str, expected in vectors:
            self.assertEqual(edn(edn_str).vector(), expected)

    def test_map(self):
        maps = [
            ("{}", Map(())),
            ("{1 2}", Map(((1, 2),))),
            ("{[1] {2 3}, (4 5 6), 7}",
             Map(((Vector((1,)), Map(((2, 3),))), (List((4, 5, 6)), 7)))),
        ]

        for edn_str, expected in maps:
            self.assertEqual(edn(edn_str).map(), expected)

    def test_set(self):
        sets = [("#{}", Set(())),
                ("#{1 2 3 4 :foo}", Set((1, 2, 3, 4, Keyword(Symbol("foo"))))),
                ("#{#{1 2} 3}", Set((Set((1, 2)), 3)))]

        for edn_str, expected in sets:
            self.assertEqual(edn(edn_str).set(), expected)

    def test_tag(self):
        tags = [
            ('#foo/bar baz', TaggedValue(Symbol('bar', 'foo'), Symbol('baz'))),
            ('#foo     baz', TaggedValue(Symbol('foo'), Symbol('baz'))),
            ('#foo\n  baz', TaggedValue(Symbol('foo'), Symbol('baz'))),
            ('#foo ; comment\nbar', TaggedValue(Symbol('foo'), Symbol('bar'))),
        ]
        for edn_str, expected in tags:
            self.assertEqual(edn(edn_str).tag(), expected)

    def test_comment(self):
        self.assertEqual(
            edn('; foo bar baz bax\nbar ; this is bar\n').edn(), Symbol('bar'))

    def test_discard(self):
        self.assertEqual(edn('[1 2 #_foo 3]').edn(), Vector([1, 2, 3]))


class ParseTestCase(unittest.TestCase):

    def test_structure(self):
        self.assertEqual(Set([1, 2, 3]), parse('#{1 2 3}'))
        self.assertEqual(Map([(1, 2), (3, 4)]), parse('{1 2, 3 4}'))


class ParseStreamTestCase(unittest.TestCase):

    def test_iterator(self):
        stream = StringIO('1 2 #{4 5} "foo" [bar qux]')
        output = parse_stream(stream)
        self.assertEqual(1, next(output))
        self.assertEqual(2, next(output))
        self.assertEqual(Set([4, 5]), next(output))
        self.assertEqual(String("foo"), next(output))
        self.assertEqual(Vector((Symbol('bar'), Symbol('qux'))), next(output))
        self.assertRaises(StopIteration, next, output)


class UnparseTestCase(unittest.TestCase):

    def assertIn(self, needle, haystack):
        self.assertTrue(
            needle in haystack, '%r not in %r' % (needle, haystack))

    def test_nil(self):
        self.assertEqual('nil', unparse(Nil))
        self.assertEqual('("b" nil)', unparse(List((String('b'), Nil))))

    def test_integer(self):
        self.assertEqual('1', unparse(1))
        self.assertEqual('(1 2)', unparse(List((1, 2))))

    def test_long(self):
        self.assertEqual('10000N', unparse(10000L))

    def test_decimal(self):
        self.assertEqual('4.2M', unparse(ExactFloat('4.2')))
        self.assertEqual('42M', unparse(ExactFloat('42')))

    def test_float(self):
        self.assertEqual('0.3', unparse(0.3))

    def test_booleans(self):
        self.assertEqual('true', unparse(True))
        self.assertEqual('false', unparse(False))

    def test_simple_strings(self):
        self.assertEqual('"foo"', unparse(String('foo')))

    def test_unicode(self):
        snowman = u'\u2603'
        encoded = snowman.encode('utf-8')
        self.assertEqual('"' + encoded + '"', unparse(String(snowman)))

    def test_newlines(self):
        # It doesn't have to be this way.  EDN allows literal newlines in
        # strings, but the equality definition says that 'foo\nbar' is not
        # equal to 'foo
        # bar'.  Thus, it's equally valid to not escape the newline but to
        # instead insert a literal space.  This is possibly a bug in the
        # spec.
        self.assertEqual('"foo\\nbar"', unparse(String('foo\nbar')))

    def test_escaping(self):
        self.assertEqual('"foo\\rbar"', unparse(String('foo\rbar')))
        self.assertEqual(r'"foo\\bar"', unparse(String(r'foo\bar')))
        self.assertEqual('"foo\\"bar"', unparse(String('foo"bar')))

    def test_character(self):
        self.assertEqual(r'\a', unparse(Character('a')))

    def test_symbol(self):
        self.assertEqual("foo", unparse(Symbol("foo")))
        self.assertEqual(".foo", unparse(Symbol(".foo")))
        self.assertEqual("/", unparse(Symbol("/")))
        self.assertEqual("foo/bar", unparse(Symbol("bar", "foo")))

    def test_keyword(self):
        self.assertEqual(":foo", unparse(Keyword(Symbol("foo"))))
        self.assertEqual(":my/foo", unparse(Keyword(Symbol("foo", "my"))))

    def test_vector(self):
        self.assertEqual("[]", unparse(Vector()))
        self.assertEqual("[a]", unparse(Vector(Symbol('a'),)))
        self.assertEqual("[[] ()]", unparse(Vector((Vector(), List()))))

    def test_list(self):
        self.assertEqual("(a)", unparse(List((Symbol('a'),))))
        self.assertEqual("()", unparse(List()))
        self.assertEqual("(() ())", unparse(List((List(), List()))))

    def test_set(self):
        self.assertEqual("#{}", unparse(Set()))
        self.assertIn(
            unparse(Set([1, 2, 3])),
            frozenset(["#{1 2 3}", "#{1 3 2}",
                       "#{2 1 3}", "#{2 3 1}",
                       "#{3 1 2}", "#{3 2 1}"]))

    def test_map(self):
        self.assertEqual("{}", unparse(Map()))
        self.assertEqual(
            '{:foo "bar"}',
            unparse(
                Map(((Keyword(Symbol('foo')), String('bar')),))))
        self.assertIn(
            unparse(
                Map(((Keyword(Symbol('foo')), String('bar')),
                     (Keyword(Symbol('baz')), String('qux'))))),
            set(['{:foo "bar" :baz "qux"}', '{:baz "qux" :foo "bar"}']))

    def test_tagged_value(self):
        self.assertEqual(
            '#foo "bar"',
            unparse(TaggedValue(Symbol('foo'), String('bar'))))


class UnparseStreamTestCase(unittest.TestCase):

    def test_unparse_stream(self):
        output_stream = StringIO()
        input_elements = iter([Symbol('foo'), String("bar")])
        unparse_stream(input_elements, output_stream)
        self.assertEqual('foo\n"bar"\n', output_stream.getvalue())
