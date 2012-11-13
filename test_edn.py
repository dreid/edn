import unittest

from edn import edn, Symbol, Keyword, Vector, TaggedValue



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


if __name__ == '__main__':
    import unittest
    unittest.main()