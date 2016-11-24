# -*- coding: utf-8 -*-
# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import io
import signal
import os
import mock

from awscli.testutils import unittest, skip_if_windows
from awscli.utils import split_on_commas, ignore_ctrl_c
from awscli.utils import find_service_and_method_in_event_name, uni_print


class TestCSVSplit(unittest.TestCase):

    def test_normal_csv_split(self):
        self.assertEqual(split_on_commas('foo,bar,baz'),
                         ['foo', 'bar', 'baz'])

    def test_quote_split(self):
        self.assertEqual(split_on_commas('foo,"bar",baz'),
                         ['foo', 'bar', 'baz'])

    def test_inner_quote_split(self):
        self.assertEqual(split_on_commas('foo,bar="1,2,3",baz'),
                         ['foo', 'bar=1,2,3', 'baz'])

    def test_single_quote(self):
        self.assertEqual(split_on_commas("foo,bar='1,2,3',baz"),
                         ['foo', 'bar=1,2,3', 'baz'])

    def test_mixing_double_single_quotes(self):
        self.assertEqual(split_on_commas("""foo,bar="1,'2',3",baz"""),
                         ['foo', "bar=1,'2',3", 'baz'])

    def test_mixing_double_single_quotes_before_first_comma(self):
        self.assertEqual(split_on_commas("""foo,bar="1','2',3",baz"""),
                         ['foo', "bar=1','2',3", 'baz'])

    def test_inner_quote_split_with_equals(self):
        self.assertEqual(split_on_commas('foo,bar="Foo:80/bar?a=b",baz'),
                         ['foo', 'bar=Foo:80/bar?a=b', 'baz'])

    def test_single_quoted_inner_value_with_no_commas(self):
        self.assertEqual(split_on_commas("foo,bar='BAR',baz"),
                         ['foo', 'bar=BAR', 'baz'])

    def test_escape_quotes(self):
        self.assertEqual(split_on_commas('foo,bar=1\,2\,3,baz'),
                         ['foo', 'bar=1,2,3', 'baz'])

    def test_no_commas(self):
        self.assertEqual(split_on_commas('foo'), ['foo'])

    def test_trailing_commas(self):
        self.assertEqual(split_on_commas('foo,'), ['foo', ''])

    def test_escape_backslash(self):
        self.assertEqual(split_on_commas('foo,bar\\\\,baz\\\\,qux'),
                         ['foo', 'bar\\', 'baz\\', 'qux'])

    def test_square_brackets(self):
        self.assertEqual(split_on_commas('foo,bar=["a=b",\'2\',c=d],baz'),
                         ['foo', 'bar=a=b,2,c=d', 'baz'])

    def test_quoted_square_brackets(self):
        self.assertEqual(split_on_commas('foo,bar="[blah]",c=d],baz'),
                         ['foo', 'bar=[blah]', 'c=d]', 'baz'])

    def test_missing_bracket(self):
        self.assertEqual(split_on_commas('foo,bar=[a,baz'),
                         ['foo', 'bar=[a', 'baz'])

    def test_missing_bracket2(self):
        self.assertEqual(split_on_commas('foo,bar=a],baz'),
                         ['foo', 'bar=a]', 'baz'])

    def test_bracket_in_middle(self):
        self.assertEqual(split_on_commas('foo,bar=a[b][c],baz'),
                         ['foo', 'bar=a[b][c]', 'baz'])

    def test_end_bracket_in_value(self):
        self.assertEqual(split_on_commas('foo,bar=[foo,*[biz]*,baz]'),
                         ['foo', 'bar=foo,*[biz]*,baz'])


@skip_if_windows("Ctrl-C not supported on windows.")
class TestIgnoreCtrlC(unittest.TestCase):
    def test_ctrl_c_is_ignored(self):
        with ignore_ctrl_c():
            # Should have the noop signal handler installed.
            self.assertEqual(signal.getsignal(signal.SIGINT), signal.SIG_IGN)
            # And if we actually try to sigint ourselves, an exception
            # should not propogate.
            os.kill(os.getpid(), signal.SIGINT)


class TestFindServiceAndOperationNameFromEvent(unittest.TestCase):
    def test_finds_service_and_operation_name(self):
        event_name = "foo.bar.baz"
        service, operation = find_service_and_method_in_event_name(event_name)
        self.assertEqual(service, "bar")
        self.assertEqual(operation, "baz")

    def test_returns_none_if_event_is_too_short(self):
        event_name = "foo.bar"
        service, operation = find_service_and_method_in_event_name(event_name)
        self.assertEqual(service, "bar")
        self.assertIs(operation, None)

        event_name = "foo"
        service, operation = find_service_and_method_in_event_name(event_name)
        self.assertIs(service, None)
        self.assertIs(operation, None)


class MockPipedStdout(io.BytesIO):
    """Mocks `sys.stdout`.
    We can't use `TextIOWrapper` because calling
    `TextIOWrapper(.., encoding=None)` sets the ``encoding`` attribute to
    `UTF-8`.
    The attribute is also `readonly` in `TextIOWrapper` and `TextIOBase` so it
    cannot be overwritten in subclasses. For these reasons we mock `sys.stdout`
    """
    def __init__(self):
        self.encoding = None

        super(MockPipedStdout, self).__init__()

    def write(self, str):
        # sys.stdout.write() will default to encoding to ascii, when its
        # `encoding` is `None`.
        if self.encoding is None:
            str = str.encode('ascii')
        else:
            str = str.encode(self.encoding)
        super(MockPipedStdout, self).write(str)


class TestUniPrint(unittest.TestCase):

    def test_out_file_with_encoding_attribute(self):
        buf = io.BytesIO()
        out = io.TextIOWrapper(buf, encoding='utf-8')
        uni_print(u'\u2713', out)
        self.assertEqual(buf.getvalue(), u'\u2713'.encode('utf-8'))

    def test_encoding_with_encoding_none(self):
        '''When the output of the aws command is being piped,
        the `encoding` attribute of `sys.stdout` is `None`.'''
        out = MockPipedStdout()
        uni_print(u'SomeChars\u2713\u2714OtherChars', out)
        self.assertEqual(out.getvalue(), b'SomeChars??OtherChars')

    def test_encoding_statement_fails_are_replaced(self):
        buf = io.BytesIO()
        out = io.TextIOWrapper(buf, encoding='ascii')
        uni_print(u'SomeChars\u2713\u2714OtherChars', out)
        # We replace the characters that can't be encoded
        # with '?'.
        self.assertEqual(buf.getvalue(), b'SomeChars??OtherChars')
