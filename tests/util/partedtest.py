# -*- coding: utf-8 -*-
#
# Copyright (c) 2022 Adolfo Gómez García <dkmaster at dkmon dot com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright notice,
#      this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright notice,
#      this list of conditions and the following disclaimer in the documentation
#      and/or other materials provided with the distribution.
#    * Neither the name of Adolfo Gómez García nor the names of its contributors
#      may be used to endorse or promote products derived from this software
#      without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
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
