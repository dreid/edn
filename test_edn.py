import datetime
import unittest

from edn import edn, dumps, loads, Symbol, Keyword, Vector, TaggedValue



class EDNTestCase(unittest.TestCase):
    def test_nil(self):
        self.assertEqual(edn("nil").nil(), None)

    def test_boolean(self):
        self.assertTrue(edn("true").boolean())
        self.assertFalse(edn("false").boolean())

    def test_string(self):
        self.assertEqual(edn('"foo"').string(), "foo")
        self.assertEqual(edn("""\"
foo
bar
baz\"""").string(), '\nfoo\nbar\nbaz')

    def test_character(self):
        self.assertEqual(edn(r"\c").character(), "c")
        self.assertEqual(edn(r"\newline").character(), "\n")
        self.assertEqual(edn(r"\tab").character(), "\t")
        self.assertEqual(edn(r"\return").character(), "\r")
        self.assertEqual(edn(r"\space").character(), " ")

    def test_symbol(self):
        self.assertEqual(edn("foo").symbol(), Symbol("foo"))
        self.assertEqual(edn(".foo").symbol(), Symbol(".foo"))
        self.assertEqual(edn("/").symbol(), Symbol("/"))
        self.assertEqual(edn("foo/bar").symbol(), Symbol("bar", "foo"))

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


class LoadsTestCase(unittest.TestCase):

    def test_structure(self):
        self.assertEqual(set([1,2,3]), loads('#{1 2 3}'))
        self.assertEqual({1: 2, 3: 4}, loads('{1 2, 3 4}'))


class DumpsTestCase(unittest.TestCase):

    def test_nil(self):
        self.assertEqual('nil', dumps(None))

    def test_integer(self):
        self.assertEqual('1', dumps(1))

    def test_float(self):
        # At least I have some idea of how ignorant this makes me look.
        self.assertEqual('0.3', dumps(0.3))

    def test_booleans(self):
        self.assertEqual('true', dumps(True))
        self.assertEqual('false', dumps(False))

    # XXX: I wonder what edn does for unicode

    def test_simple_strings(self):
        self.assertEqual('"foo"', dumps('foo'))

    def test_newlines(self):
        # It doesn't have to be this way.  EDN allows literal newlines in
        # strings, but the equality definition says that 'foo\nbar' is not
        # equal to 'foo
        # bar'.  Thus, it's equally valid to not escape the newline but to
        # instead insert a literal space.  This is possibly a bug in the
        # spec.
        self.assertEqual('"foo\\nbar"', dumps('foo\nbar'))

    def test_escaping(self):
        self.assertEqual('"foo\\rbar"', dumps('foo\rbar'))
        self.assertEqual(r'"foo\\bar"', dumps(r'foo\bar'))
        self.assertEqual('"foo\\"bar"', dumps('foo"bar'))

    def test_character(self):
        # XXX: No character support yet.  Need a type for it or something.
        self.assertEqual('"a"', dumps('a'))

    def test_symbol(self):
        self.assertEqual("foo", dumps(Symbol("foo")))
        self.assertEqual(".foo", dumps(Symbol(".foo")))
        self.assertEqual("/", dumps(Symbol("/")))
        self.assertEqual("foo/bar", dumps(Symbol("bar", "foo")))

    def test_keyword(self):
        self.assertEqual(":foo", dumps(Keyword("foo")))
        self.assertEqual(":my/foo", dumps(Keyword("foo", "my")))

    def test_tuple(self):
        self.assertEqual("()", dumps(()))
        self.assertEqual("(() ())", dumps(((), ())))
        self.assertEqual("(a)", dumps((Symbol('a'),)))

    def test_list(self):
        self.assertEqual("()", dumps([]))
        self.assertEqual("(() ())", dumps([[], []]))
        self.assertEqual("(a)", dumps([Symbol('a')]))

    def test_set(self):
        self.assertEqual("#{}", dumps(frozenset()))
        self.assertIn(
            dumps(set([1, 2, 3])),
            set(["#{1 2 3}", "#{1 3 2}",
                 "#{2 1 3}", "#{2 3 1}",
                 "#{3 1 2}", "#{3 2 1}"]))

    def test_dict(self):
        self.assertEqual("{}", dumps({}))
        self.assertEqual('{:foo "bar"}', dumps({Keyword('foo'): 'bar'}))
        self.assertIn(
            dumps({Keyword('foo'): 'bar', Keyword('baz'): 'qux'}),
            set(['{:foo "bar" :baz "qux"}', '{:baz "qux" :foo "bar"}']))

    def test_datetime(self):
        # XXX: Hardcoding the timezone is so awfully wrong, but I've got no
        # net connection and no idea what rfc-3339-format does.
        sometime = datetime.datetime(2012, 5, 12, 14, 30, 0)
        self.assertEqual('#inst "2012-05-12T14:30.00Z"', dumps(sometime))


if __name__ == '__main__':
    import unittest
    unittest.main()
