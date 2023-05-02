# Copyright (c) 2023 Adolfo Gómez
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
@author: Adolfo Gómez, dkmaster at dkmon dot com
"""
import typing
import random
import logging
import unittest
import contextlib

from parted import excpt

logger = logging.getLogger(__name__)

class PartedTestCase(unittest.TestCase):
    GiB = 1<<30
    MiB = 1<<20
    KiB = 1<<10

    total_exceptions = 0  # number of exceptions got

    # Basic exception handler
    def exception_handler(self, exc: excpt.PedException) -> excpt.PedException.Option:
        logger.error('Exception from Parted library: %s', exc)
        self.total_exceptions += 1
        return excpt.PedException.Option.UNHANDLED

    @contextlib.contextmanager
    def exception_context(self) -> typing.Iterator[None]:
        self.total_exceptions = 0
        with excpt.PedException.with_handler(self.exception_handler):
            yield

    def zeroed_bytes(self, size: int) -> bytes:
        return bytes(size)

    def random_bytes(self, size: int) -> bytes:
        return random.randbytes(size)

    @contextlib.contextmanager
    def override_init_del_add_counter(self, cls: typing.Type) -> typing.Iterator[None]:
        # override __init__ to increase a counter and __del__ to decrement it
        cls._counter = 0
        cls._old_init = cls.__init__
        cls._old_del = cls.__del__

        def __init__(self, *args, **kwargs) -> None:
            cls._counter += 1
            cls._old_init(self, *args, **kwargs)

        def __del__(self) -> None:
            cls._counter -= 1
            cls._old_del(self)

        cls.__init__ = __init__
        cls.__del__ = __del__

        yield

        cls.__init__ = cls._old_init
        cls.__del__ = cls._old_del
        del cls._old_init
        del cls._old_del
        del cls._counter

    def get_counter(self, cls: typing.Type) -> int:
        return cls._counter
