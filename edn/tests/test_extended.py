from collections import namedtuple
import datetime
import unittest
import uuid

import iso8601
from perfidy import frozendict

from edn import (
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
from edn._extended import (
    decode,
    encode,
    INST,
    UUID,
)


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

    def test_default_tagged_value(self):
        handler = lambda s, v: ('default', s, v)
        result = decode(
            TaggedValue(Symbol('foo'), String('bar')), default=handler)
        self.assertEqual(('default', Symbol('foo'), u'bar'), result)

    def test_inst(self):
        inst = TaggedValue(INST, String("1985-04-12T23:20:50.52Z"))
        result = decode(inst)
        self.assertEqual(
            datetime.datetime(
                1985, 4, 12, 23, 20, 50, 520000, tzinfo=iso8601.iso8601.UTC),
            result)

    def test_inst_with_tz(self):
        inst = TaggedValue(INST, String("1985-04-12T23:20:50.52-05:30"))
        result = decode(inst)
        expected_tz = iso8601.iso8601.FixedOffset(-5, -30, '-05:30')
        self.assertEqual(
            datetime.datetime(1985, 4, 12, 23, 20, 50, 520000,
                              tzinfo=expected_tz),
            result)

    def test_inst_without_fractional(self):
        inst = TaggedValue(INST, String("1985-04-12T23:20:50Z"))
        result = decode(inst)
        self.assertEqual(
            datetime.datetime(1985, 4, 12, 23, 20, 50, tzinfo=iso8601.iso8601.UTC),
            result)

    def test_uuid(self):
        uid = "f81d4fae-7dec-11d0-a765-00a0c91e6bf6"
        ast = TaggedValue(UUID, String(uid))
        self.assertEqual(uuid.UUID(uid), decode(ast))


class LoadsTestCase(unittest.TestCase):

    def test_structure(self):
        self.assertEqual(set([1,2,3]), loads('#{1 2 3}'))
        self.assertEqual(frozendict({1: 2, 3: 4}), loads('{1 2, 3 4}'))

    def test_custom_tag(self):
        text = '#foo [1 2]'
        parsed = loads(text, {Symbol('foo'): lambda x: list(reversed(x))})
        self.assertEqual([2, 1], parsed)

    def test_custom_default(self):
        text = '#foo [1 2]'
        parsed = loads(text, default=lambda a, b: b)
        self.assertEqual((1, 2), parsed)

    def test_custom_tag_doesnt_mutate(self):
        foo = Symbol('foo')
        text = '#foo [1 2]'
        loads(text, {foo: lambda x: list(reversed(x))})
        parsed = loads(text)
        self.assertEqual(TaggedValue(foo, (1, 2)), parsed)


class EncoderTests(unittest.TestCase):

    def test_string(self):
        self.assertEqual(String(u"foo"), encode(u"foo"))
        self.assertEqual(String("foo"), encode("foo"))

    def test_symbol(self):
        self.assertEqual(Symbol("foo"), encode(Symbol("foo")))

    def test_keyword(self):
        self.assertEqual(
            Keyword(Symbol("foo")), encode(Keyword(Symbol("foo"))))

    def test_map(self):
        self.assertEqual(Map(((1, 2), (3, 4))), encode({1: 2, 3: 4}))
        self.assertEqual(
            Map(((1, 2), (3, 4))), encode(frozendict({1: 2, 3: 4})))

    def test_set(self):
        self.assertEqual(Set((1, 2, 3)), encode(frozenset([1, 2, 3])))
        self.assertEqual(Set((1, 2, 3)), encode(set([1, 2, 3])))

    def test_tuple(self):
        self.assertEqual(List((1, 2, 3)), encode((1, 2, 3)))
        self.assertEqual(Vector((1, 2, 3)), encode([1, 2, 3]))

    def test_datetime(self):
        # XXX: Maybe give Symbol a makeTag method, so that
        # INST.makeTag("2013-...") works?
        self.assertEqual(
            TaggedValue(INST, String("2013-12-25T19:32:55+00:00")),
            encode(datetime.datetime(2013, 12, 25, 19, 32, 55,
                                     tzinfo=iso8601.iso8601.UTC)))

    def test_uuid(self):
        uid = uuid.uuid4()
        self.assertEqual(TaggedValue(UUID, String(str(uid))), encode(uid))

    def test_nested_map(self):
        data = {'foo': 'bar'}
        encoded = encode(data)
        self.assertEqual(Map(((String('foo'), String('bar')),)), encoded)

    def test_nested_set(self):
        data = set([(1,), (2,)])
        encoded = encode(data)
        self.assertIn(
            encoded, (Set((List([1]), List([2]))),
                      Set((List([2]), List([1])))))

    def test_nested_vector(self):
        data = [[1], [2]]
        encoded = encode(data)
        self.assertEqual(encoded, Vector((Vector([1]), Vector([2]))))

    def test_nested_list(self):
        data = ("foo", "bar")
        encoded = encode(data)
        self.assertEqual(List((String('foo'), String('bar'))), encoded)


class DumpsTestCase(unittest.TestCase):

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

    def test_escaped_string(self):
        self.assertEqual('"foo\\nbar"', dumps('foo\nbar'))
