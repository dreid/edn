from collections import namedtuple
import datetime
import unittest
import uuid

import iso8601
from perfidy import frozendict

from edn import (
    Character,
    DEFAULT_WRITE_HANDLERS,
    List,
    Keyword,
    Map,
    Set,
    String,
    Symbol,
    TaggedValue,
    Vector,
    dumps,
    edn,
    loads,
)


class EDNTestCase(unittest.TestCase):
    def test_nil(self):
        self.assertEqual(edn("nil").nil(), None)

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
        self.assertEqual(edn("foo").symbol(), Symbol("foo"))
        self.assertEqual(edn(".foo").symbol(), Symbol(".foo"))
        self.assertEqual(edn("/").symbol(), Symbol("/"))
        self.assertEqual(edn("foo/bar").symbol(), Symbol("bar", "foo"))

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
                    ("10000N", 10000L)]

        for edn_str, expected in integers:
            self.assertEqual(edn(edn_str).integer(), expected)

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
        self.assertEqual(edn('#foo/bar baz').tag(),
                         TaggedValue(Symbol('bar', 'foo'), Symbol('baz')))

    def test_comment(self):
        self.assertEqual(
            edn('; foo bar baz bax\nbar ; this is bar\n').edn(), Symbol('bar'))

    def test_discard(self):
        self.assertEqual(edn('[1 2 #_foo 3]').edn(), Vector([1, 2, 3]))


class LoadsTestCase(object):
    # DISABLED for the moment

    def test_structure(self):
        self.assertEqual(set([1,2,3]), loads('#{1 2 3}'))
        self.assertEqual(frozendict({1: 2, 3: 4}), loads('{1 2, 3 4}'))

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
                1985, 4, 12, 23, 20, 50, 520000, tzinfo=iso8601.iso8601.UTC), parsed)

    def test_inst_with_tz(self):
        text = '#inst "1985-04-12T23:20:50.52-05:30"'
        parsed = loads(text)
        expected_tz = iso8601.iso8601.FixedOffset(-5, -30, '-05:30')
        self.assertEqual(
            datetime.datetime(1985, 4, 12, 23, 20, 50, 520000,
                              tzinfo=expected_tz),
            parsed)

    def test_inst_without_fractional(self):
        text = '#inst "1985-04-12T23:20:50Z"'
        parsed = loads(text)
        self.assertEqual(
            datetime.datetime(1985, 4, 12, 23, 20, 50, tzinfo=iso8601.iso8601.UTC),
            parsed)

    def test_uuid(self):
        uid = "f81d4fae-7dec-11d0-a765-00a0c91e6bf6"
        text = '#uuid "%s"' % (uid,)
        self.assertEqual(uuid.UUID(uid), loads(text))


class DumpsTestCase(object):
    # DISABLED for now

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
        sometime = datetime.datetime(
            2012, 5, 12, 14, 30, 0, tzinfo=iso8601.iso8601.UTC)
        self.assertEqual('#inst "2012-05-12T14:30:00+00:00"', dumps(sometime))

    def test_datetime_with_tz(self):
        tz = iso8601.iso8601.FixedOffset(1, 0, '+01:00')
        sometime = datetime.datetime(2012, 5, 12, 14, 30, 0, tzinfo=tz)
        self.assertEqual('#inst "2012-05-12T14:30:00+01:00"', dumps(sometime))

    def test_tagged_value(self):
        self.assertEqual(
            '#foo bar',
            dumps(TaggedValue(Symbol('foo'), Symbol('bar'))))

    def test_uuid(self):
        uid = uuid.UUID("f81d4fae-7dec-11d0-a765-00a0c91e6bf6")
        text = '#uuid "%s"' % (uid,)
        self.assertEqual(text, dumps(uid))

    def test_arbitrary_namedtuple(self):
        # Documenting a potentially unexpected behaviour.  Because dumps
        # figures out how to write something based on type, namedtuples will
        # be dumped as lists.  Since they are very often used for specific types,
        # that might be surprising.
        foo = namedtuple('foo', 'x y')
        a = foo(1, 2)
        self.assertEqual('(1 2)', dumps(a))

    def test_custom_handler(self):
        foo = namedtuple('foo', 'x y')
        handler = lambda x: TaggedValue(Symbol('foo'), (x.x, x.y))
        handlers = DEFAULT_WRITE_HANDLERS + [(foo, handler)]
        self.assertEqual('#foo (2 3)', dumps(foo(2, 3), handlers))

    def test_nested_custom_handler(self):
        foo = namedtuple('foo', 'x y')
        handler = lambda x: TaggedValue(Symbol('foo'), (x.x, x.y))
        handlers = DEFAULT_WRITE_HANDLERS + [(foo, handler)]
        self.assertEqual('(#foo (2 3))', dumps([foo(2, 3)], handlers))


if __name__ == '__main__':
    import unittest
    unittest.main()
