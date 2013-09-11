import datetime
import unittest
import uuid

import pytz

from edn import (
    Keyword,
    Symbol,
    TaggedValue,
    Vector,
    dumps,
    edn,
    loads,
    make_tagged_value,
    _rfc_3339_grammar,
)


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

    def test_unicode(self):
        # https://github.com/edn-format/edn/issues/59
        snowman = u'\u2603'
        encoded = snowman.encode('utf-8')
        quoted = '"' + encoded + '"'
        self.assertEqual(edn(quoted).string(), snowman)

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


class TaggedValueTestCase(unittest.TestCase):

    def test_default(self):
        result = make_tagged_value({}, Symbol('foo'), 'bar')
        self.assertEqual(TaggedValue(Symbol('foo'), 'bar'), result)

    def test_custom(self):
        result = make_tagged_value(
            {Symbol('foo'): lambda x: list(reversed(x))},
            Symbol('foo'), 'bar')
        self.assertEqual(['r', 'a', 'b'], result)


class TestDatetimeParsing(unittest.TestCase):

    def test_date(self):
        self.assertEqual(
            datetime.date(2001, 12, 25),
            _rfc_3339_grammar('2001-12-25').date())

    def test_naive_time(self):
        self.assertEqual(
            datetime.time(13, 59, 43),
            _rfc_3339_grammar('13:59:43').naive_time())

    def test_fractional_naive_time(self):
        self.assertEqual(
            datetime.time(13, 59, 43, 880000),
            _rfc_3339_grammar('13:59:43.88').naive_time())

    def test_utc_time(self):
        self.assertEqual(
            datetime.time(13, 59, 43, tzinfo=pytz.UTC),
            _rfc_3339_grammar('13:59:43Z').time())

    def test_fractional_utc_time(self):
        self.assertEqual(
            datetime.time(13, 59, 43, 880000, tzinfo=pytz.UTC),
            _rfc_3339_grammar('13:59:43.88Z').time())

    def test_timezone_time(self):
        self.assertEqual(
            datetime.time(13, 59, 43, tzinfo=pytz.FixedOffset(60)),
            _rfc_3339_grammar('13:59:43+01:00').time())

    def test_fractional_timezone_time(self):
        self.assertEqual(
            datetime.time(13, 59, 43, 770000, tzinfo=pytz.FixedOffset(60)),
            _rfc_3339_grammar('13:59:43.77+01:00').time())

    def test_numeric_offset(self):
        get_offset = lambda x: _rfc_3339_grammar(x).numeric_offset()
        self.assertEqual(pytz.FixedOffset(0), get_offset('+00:00'))
        self.assertEqual(pytz.FixedOffset(90), get_offset('+01:30'))
        self.assertEqual(pytz.FixedOffset(-150), get_offset('-02:30'))

    def test_datetime(self):
        self.assertEqual(
            datetime.datetime(2001, 12, 25, 13, 59, 43, 770000, tzinfo=pytz.UTC),
            _rfc_3339_grammar('2001-12-25T13:59:43.77Z').datetime())


class LoadsTestCase(unittest.TestCase):

    def test_structure(self):
        self.assertEqual(set([1,2,3]), loads('#{1 2 3}'))
        self.assertEqual({1: 2, 3: 4}, loads('{1 2, 3 4}'))

    def test_custom_tag(self):
        text = '#foo [1 2]'
        parsed = loads(text, {Symbol('foo'): lambda x: list(reversed(x))})
        self.assertEqual([2, 1], parsed)

    def test_custom_tag_doesnt_mutate(self):
        foo = Symbol('foo')
        text = '#foo [1 2]'
        loads(text, {foo: lambda x: list(reversed(x))})
        parsed = loads(text)
        self.assertEqual(TaggedValue(foo, Vector([1, 2])), parsed)

    def test_inst(self):
        text = '#inst "1985-04-12T23:20:50.52Z"'
        parsed = loads(text)
        self.assertEqual(
            datetime.datetime(
                1985, 4, 12, 23, 20, 50, 520000, tzinfo=pytz.UTC), parsed)

    def test_inst_with_tz(self):
        text = '#inst "1985-04-12T23:20:50.52-05:30"'
        parsed = loads(text)
        expected_tz = pytz.FixedOffset(-5 * 60 - 30)
        self.assertEqual(
            datetime.datetime(1985, 4, 12, 23, 20, 50, 520000,
                              tzinfo=expected_tz),
            parsed)

    def test_inst_without_fractional(self):
        text = '#inst "1985-04-12T23:20:50Z"'
        parsed = loads(text)
        self.assertEqual(
            datetime.datetime(1985, 4, 12, 23, 20, 50, tzinfo=pytz.UTC),
            parsed)

    def test_uuid(self):
        uid = "f81d4fae-7dec-11d0-a765-00a0c91e6bf6"
        text = '#uuid "%s"' % (uid,)
        self.assertEqual(uuid.UUID(uid), loads(text))


class DumpsTestCase(unittest.TestCase):

    def test_nil(self):
        self.assertEqual('nil', dumps(None))

    def test_integer(self):
        self.assertEqual('1', dumps(1))

    def test_long(self):
        self.assertEqual('10000N', dumps(10000L))

    def test_float(self):
        # FIXME: At least I have some idea of how ignorant this makes me look.
        # Figure out what's required to do this rigorously.
        self.assertEqual('0.3', dumps(0.3))

    def test_booleans(self):
        self.assertEqual('true', dumps(True))
        self.assertEqual('false', dumps(False))

    def test_simple_strings(self):
        self.assertEqual('"foo"', dumps('foo'))

    def test_unicode(self):
        snowman = u'\u2603'
        encoded = snowman.encode('utf-8')
        self.assertEqual('"' + encoded + '"', dumps(snowman))

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
        sometime = datetime.datetime(2012, 5, 12, 14, 30, 0, tzinfo=pytz.UTC)
        self.assertEqual('#inst "2012-05-12T14:30:00+00:00"', dumps(sometime))

    def test_datetime_with_tz(self):
        sometime = datetime.datetime(
            2012, 5, 12, 14, 30, 0, tzinfo=pytz.FixedOffset(60))
        self.assertEqual('#inst "2012-05-12T14:30:00+01:00"', dumps(sometime))

    def test_tagged_value(self):
        self.assertEqual(
            '#foo bar',
            dumps(TaggedValue(Symbol('foo'), Symbol('bar'))))

    def test_uuid(self):
        uid = uuid.UUID("f81d4fae-7dec-11d0-a765-00a0c91e6bf6")
        text = '#uuid "%s"' % (uid,)
        self.assertEqual(text, dumps(uid))


if __name__ == '__main__':
    import unittest
    unittest.main()
