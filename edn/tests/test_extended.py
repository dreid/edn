from collections import namedtuple
import datetime
from decimal import Decimal
from StringIO import StringIO
import unittest
import uuid

import iso8601
from perfidy import frozendict

from edn import (
    dump,
    dumps,
    load,
    loads,
    Keyword,
    Symbol,
)
from .._ast import (
    Character,
    ExactFloat,
    List,
    Map,
    Nil,
    Set,
    String,
    TaggedValue,
    Vector,
)
from .._extended import (
    from_terms,
    to_terms,
    INST,
    UUID,
)


class DecoderTests(unittest.TestCase):

    def test_bool(self):
        self.assertEqual(True, from_terms(True))
        self.assertEqual(False, from_terms(False))

    def test_integers(self):
        self.assertEqual(42, from_terms(42))

    def test_floats(self):
        self.assertEqual(42.3, from_terms(42.3))
        self.assertEqual(-42.3, from_terms(-42.3))
        self.assertEqual(-42.3e3, from_terms(-42.3e3))

    def test_decimal(self):
        self.assertEqual(Decimal('42.3'), from_terms(Decimal('42.3')))
        self.assertEqual(Decimal('-42.3'), from_terms(Decimal('-42.3')))
        self.assertEqual(Decimal('-42.3e3'), from_terms(Decimal('-42.3e3')))

    def test_string(self):
        self.assertEqual("foo", from_terms(String("foo")))

    def test_character(self):
        self.assertEqual('f', from_terms(Character('f')))

    def test_none(self):
        self.assertEqual(None, from_terms(Nil))

    def test_vector(self):
        self.assertEqual((1, 2, 3), from_terms(Vector((1, 2, 3))))

    def test_list(self):
        self.assertEqual((1, 2, 3), from_terms(List((1, 2, 3))))

    def test_set(self):
        self.assertEqual(frozenset((1, 2, 3)), from_terms(Set((1, 2, 3))))

    def test_map(self):
        self.assertEqual(
            frozendict({1: 2, 3: 4}), from_terms(Map(((1, 2), (3, 4)))))

    def test_symbol(self):
        self.assertEqual(Symbol('foo'), from_terms(Symbol('foo')))
        self.assertEqual(
            Symbol('foo', 'bar'), from_terms(Symbol('foo', 'bar')))

    def test_keyword(self):
        self.assertEqual(
            Keyword(Symbol('foo')), from_terms(Keyword(Symbol('foo'))))
        self.assertEqual(
            Keyword(Symbol('foo', 'bar')),
            from_terms(Keyword(Symbol('foo', 'bar'))))

    def test_tagged_value(self):
        self.assertEqual(
            TaggedValue(Symbol('foo'), 'bar'),
            from_terms(TaggedValue(Symbol('foo'), String('bar'))))
        self.assertEqual(
            TaggedValue(Symbol('foo', 'qux'), 'bar'),
            from_terms(TaggedValue(Symbol('foo', 'qux'), String('bar'))))

    def test_readers(self):
        ast = TaggedValue(Symbol('foo'), String('bar'))
        result = from_terms(
            ast, frozendict({Symbol('foo'): lambda x: list(reversed(x))}))
        self.assertEqual([u'r', u'a', u'b'], result)

    def test_default_tagged_value(self):
        handler = lambda s, v: ('default', s, v)
        result = from_terms(
            TaggedValue(Symbol('foo'), String('bar')), default=handler)
        self.assertEqual(('default', Symbol('foo'), u'bar'), result)

    def test_inst(self):
        inst = TaggedValue(INST, String("1985-04-12T23:20:50.52Z"))
        result = from_terms(inst)
        self.assertEqual(
            datetime.datetime(
                1985, 4, 12, 23, 20, 50, 520000, tzinfo=iso8601.iso8601.UTC),
            result)

    def test_inst_with_tz(self):
        inst = TaggedValue(INST, String("1985-04-12T23:20:50.52-05:30"))
        result = from_terms(inst)
        expected_tz = iso8601.iso8601.FixedOffset(-5, -30, '-05:30')
        self.assertEqual(
            datetime.datetime(1985, 4, 12, 23, 20, 50, 520000,
                              tzinfo=expected_tz),
            result)

    def test_inst_without_fractional(self):
        inst = TaggedValue(INST, String("1985-04-12T23:20:50Z"))
        result = from_terms(inst)
        self.assertEqual(
            datetime.datetime(
                1985, 4, 12, 23, 20, 50, tzinfo=iso8601.iso8601.UTC),
            result)

    def test_uuid(self):
        uid = "f81d4fae-7dec-11d0-a765-00a0c91e6bf6"
        ast = TaggedValue(UUID, String(uid))
        self.assertEqual(uuid.UUID(uid), from_terms(ast))


def reverse(x):
    return list(reversed(x))


class LoadsTestCase(unittest.TestCase):

    def test_structure(self):
        self.assertEqual(set([1, 2, 3]), loads('#{1 2 3}'))
        self.assertEqual(frozendict({1: 2, 3: 4}), loads('{1 2, 3 4}'))
        self.assertEqual(
            frozendict({Keyword(Symbol('foo')): Symbol('bar')}),
            loads('{:foo bar}'))

    def test_custom_tag(self):
        text = '#foo [1 2]'
        parsed = loads(text, {Symbol('foo'): reverse})
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

    def test_nil(self):
        self.assertEqual(None, loads('nil'))

    def test_bool(self):
        self.assertEqual(True, loads('true'))
        self.assertEqual(False, loads('false'))

    def test_numbers(self):
        self.assertEqual(4.2, loads('4.2'))
        self.assertEqual((Symbol('amount'), -11.4), loads('[amount -11.4]'))

    def test_exact_floats(self):
        floats = [
            (Decimal('4.2'), '4.2M'),
            (Decimal('-4.2'), '-4.2M'),
            (Decimal('4.2'), '+4.2M'),
            (Decimal('412.2'), '4.122e2M'),
        ]
        for expected, edn_str in floats:
            self.assertEqual(expected, loads(edn_str))


class LoadTestCase(unittest.TestCase):

    def test_single_element(self):
        stream = load(StringIO('#{1 2 3}'))
        self.assertEqual(set([1, 2, 3]), next(stream))
        self.assertRaises(StopIteration, next, stream)

    def test_multiple_elements(self):
        stream = load(StringIO('#{1 2 3} "foo"\n43,32'))
        self.assertEqual(set([1, 2, 3]), next(stream))
        self.assertEqual(u"foo", next(stream))
        self.assertEqual(43, next(stream))
        self.assertEqual(32, next(stream))
        self.assertRaises(StopIteration, next, stream)

    def test_custom_tag(self):
        text = '#foo [1 2] #foo [3 4]'
        parsed = load(StringIO(text), {Symbol('foo'): reverse})
        self.assertEqual([[2, 1], [4, 3]], list(parsed))

    def test_custom_default(self):
        marker = object()
        handler = lambda a, b: (marker, b)
        stream = StringIO('#foo [1 2] #bar "qux"')
        parsed = list(load(stream, default=handler))
        self.assertEqual([(marker, (1, 2)), (marker, u"qux")], parsed)


class Custom(object):
    """Used in tests as an unrecognized object."""

    def __init__(self, x):
        self.x = x

    def __repr__(self):
        return '<Custom(%s)>' % (self.x,)


class EncoderTests(unittest.TestCase):

    def test_bool(self):
        self.assertEqual(True, to_terms(True))
        self.assertEqual(False, to_terms(False))

    def test_float(self):
        self.assertEqual(4.2, to_terms(4.2))

    def test_decimal(self):
        self.assertEqual(ExactFloat('4.2'), to_terms(Decimal('4.2')))
        self.assertEqual(ExactFloat('42'), to_terms(Decimal('4.2e1')))

    def test_none(self):
        self.assertEqual(Nil, to_terms(None))
        self.assertEqual(List((String('b'), Nil)), to_terms(('b', None)))

    def test_string(self):
        self.assertEqual(String(u"foo"), to_terms(u"foo"))
        self.assertEqual(String("foo"), to_terms("foo"))

    def test_symbol(self):
        self.assertEqual(Symbol("foo"), to_terms(Symbol("foo")))

    def test_keyword(self):
        self.assertEqual(
            Keyword(Symbol("foo")), to_terms(Keyword(Symbol("foo"))))

    def test_map(self):
        self.assertEqual(Map(((1, 2), (3, 4))), to_terms({1: 2, 3: 4}))
        self.assertEqual(
            Map(((1, 2), (3, 4))), to_terms(frozendict({1: 2, 3: 4})))

    def test_set(self):
        self.assertEqual(Set((1, 2, 3)), to_terms(frozenset([1, 2, 3])))
        self.assertEqual(Set((1, 2, 3)), to_terms(set([1, 2, 3])))

    def test_tuple(self):
        self.assertEqual(List((1, 2, 3)), to_terms((1, 2, 3)))
        self.assertEqual(Vector((1, 2, 3)), to_terms([1, 2, 3]))

    def test_datetime(self):
        self.assertEqual(
            TaggedValue(INST, String("2013-12-25T19:32:55+00:00")),
            to_terms(datetime.datetime(2013, 12, 25, 19, 32, 55,
                                       tzinfo=iso8601.iso8601.UTC)))

    def test_uuid(self):
        uid = uuid.uuid4()
        self.assertEqual(TaggedValue(UUID, String(str(uid))), to_terms(uid))

    def test_nested_map(self):
        data = {'foo': 'bar'}
        encoded = to_terms(data)
        self.assertEqual(Map(((String('foo'), String('bar')),)), encoded)

    def test_nested_set(self):
        data = set([(1,), (2,)])
        encoded = to_terms(data)
        expecteds = (Set((List([1]), List([2]))), Set((List([2]), List([1]))))
        self.assertTrue(
            encoded in expecteds, '%r not in %r' % (encoded, expecteds))

    def test_nested_vector(self):
        data = [[1], [2]]
        encoded = to_terms(data)
        self.assertEqual(encoded, Vector((Vector([1]), Vector([2]))))

    def test_nested_list(self):
        data = ("foo", "bar")
        encoded = to_terms(data)
        self.assertEqual(List((String('foo'), String('bar'))), encoded)

    def test_custom_writer(self):
        point = namedtuple('point', 'x y')
        writer = lambda p: (p.x, p.y)
        encoded = to_terms(point(2, 3), [(point, Symbol('point'), writer)])
        self.assertEqual(TaggedValue(Symbol('point'), List((2, 3))), encoded)

    def test_nested_custom_writer(self):
        point = namedtuple('point', 'x y')
        writer = lambda p: (p.x, p.y)
        encoded = to_terms(
            {1: point(2, 3)}, [(point, Symbol('point'), writer)])
        self.assertEqual(
            Map(((1, TaggedValue(Symbol('point'), List((2, 3)))),)), encoded)

    def test_unknown_type(self):
        self.assertRaises(ValueError, to_terms, Custom(42))

    def test_unknown_type_handler(self):
        result = to_terms(Custom(42), default=repr)
        self.assertEqual(String("<Custom(42)>"), result)

    def test_nested_unknown_type_handler(self):
        result = to_terms([Custom(42)], default=repr)
        self.assertEqual(Vector([String("<Custom(42)>")]), result)


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
        # be dumped as lists.  Since they are very often used for specific
        # types, that might be surprising.
        foo = namedtuple('foo', 'x y')
        a = foo(1, 2)
        self.assertEqual('(1 2)', dumps(a))

    def test_escaped_string(self):
        self.assertEqual('"foo\\nbar"', dumps('foo\nbar'))

    def test_custom_writer(self):
        point = namedtuple('point', 'x y')
        writer = lambda p: (p.x, p.y)
        output = dumps(point(2, 3), [(point, Symbol('point'), writer)])
        self.assertEqual('#point (2 3)', output)

    def test_unknown_handler(self):
        output = dumps(Custom(42), default=repr)
        self.assertEqual('"<Custom(42)>"', output)

    def test_null(self):
        self.assertEqual('nil', dumps(None))
        self.assertEqual('("b" nil)', dumps(('b', None)))

    def test_decimal(self):
        self.assertEqual('4.1234M', dumps(Decimal('4.1234')))
        self.assertEqual('4M', dumps(Decimal('4')))

    def test_complex(self):
        writers = (
            (datetime.date, Symbol('day'), lambda x: x.strftime('%Y-%m-%d')),
        )
        uid = uuid.uuid4()
        data = [
            ('username', "joe.random"),
            ('time_finished', datetime.date(2013, 9, 21)),
            ('specified_end_date', None),
            ('time_started', datetime.date(2013, 9, 21)),
            ('end_date', datetime.date(2013, 9, 21)),
            ('data_file', "/tmp/path/output/%s" % (str(uid,))),
            ("specified_start_date", None),
            ("start_date", datetime.date(2013, 9, 1)),
            ("id", str(uid)),
            ("foo", "bar"),
        ]
        expected = (
            '[("username" "joe.random") ("time_finished" #day "2013-09-21") '
            '("specified_end_date" nil) ("time_started" #day "2013-09-21") '
            '("end_date" #day "2013-09-21") '
            '("data_file" "/tmp/path/output/%s") '
            '("specified_start_date" nil) ("start_date" #day "2013-09-01") '
            '("id" "%s") ("foo" "bar")]'
        ) % (str(uid), str(uid))
        self.assertEqual(expected, dumps(data, writers))


class TestDump(unittest.TestCase):

    def test_dump(self):
        inputs = [{'foo': 42}, set([2, 3, 7])]
        output = StringIO()
        dump(inputs, output)
        self.assertEqual(
            '{"foo" 42}\n#{2 3 7}\n',
            output.getvalue())

    def test_custom_writer(self):
        point = namedtuple('point', 'x y')
        writer = lambda p: (p.x, p.y)
        output = StringIO()
        dump([point(2, 3)], output, [(point, Symbol('point'), writer)])
        self.assertEqual('#point (2 3)\n', output.getvalue())

    def test_unknown_handler(self):
        output = StringIO()
        dump([Custom(42)], output, default=repr)
        self.assertEqual('"<Custom(42)>"\n', output.getvalue())
