from collections import namedtuple
import datetime
import unittest
import uuid

import iso8601
from perfidy import frozendict

from edn import (
    DEFAULT_WRITE_HANDLERS,
    dumps,
    loads,
)
from edn._ast import (
    Character,
    Keyword,
    List,
    Map,
    Set,
    String,
    Symbol,
    TaggedValue,
    Vector,
)
from edn._extended import decode


class DecoderTests(unittest.TestCase):

    def test_bool(self):
        self.assertEqual(True, decode(True))
        self.assertEqual(False, decode(False))

    def test_int(self):
        self.assertEqual(42, decode(42))

    def test_string(self):
        self.assertEqual("foo", decode(String("foo")))

    def test_character(self):
        self.assertEqual('f', decode(Character('f')))

    def test_none(self):
        self.assertEqual(None, decode(None))

    def test_vector(self):
        self.assertEqual((1, 2, 3), decode(Vector((1, 2, 3))))

    def test_list(self):
        self.assertEqual((1, 2, 3), decode(List((1, 2, 3))))

    def test_set(self):
        self.assertEqual(frozenset((1, 2, 3)), decode(Set((1, 2, 3))))

    def test_map(self):
        self.assertEqual(
            frozendict({1: 2, 3: 4}), decode(Map(((1, 2), (3, 4)))))

    def test_symbol(self):
        self.assertEqual(Symbol('foo'), decode(Symbol('foo')))

    def test_keyword(self):
        self.assertEqual(
            Keyword(Symbol('foo')), decode(Keyword(Symbol('foo'))))

    def test_tagged_value(self):
        self.assertEqual(
            TaggedValue(Symbol('foo'), 'bar'),
            decode(TaggedValue(Symbol('foo'), String('bar'))))

    def test_readers(self):
        ast = TaggedValue(Symbol('foo'), String('bar'))
        result = decode(
            ast, frozendict({Symbol('foo'): lambda x: list(reversed(x))}))
        self.assertEqual([u'r', u'a', u'b'], result)


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

    def test_datetime(self):
        sometime = datetime.datetime(
            2012, 5, 12, 14, 30, 0, tzinfo=iso8601.iso8601.UTC)
        self.assertEqual('#inst "2012-05-12T14:30:00+00:00"', dumps(sometime))

    def test_datetime_with_tz(self):
        tz = iso8601.iso8601.FixedOffset(1, 0, '+01:00')
        sometime = datetime.datetime(2012, 5, 12, 14, 30, 0, tzinfo=tz)
        self.assertEqual('#inst "2012-05-12T14:30:00+01:00"', dumps(sometime))

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
