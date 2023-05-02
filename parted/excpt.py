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
Parted library exceptions control module.

This modules contains the mechanism to control exceptions raised by parted
library, and to threat them on a pythonic way.

:author: Adolfo Gómez, dkmaster at dkmon dot com
"""

import enum
import contextlib
import typing
import logging

from parted import _parted  # type: ignore

if typing.TYPE_CHECKING:
    import cffi

logger = logging.getLogger(__name__)

# Only one exception handler can be activated at a time
class PedException:
    """This class represents a parted library exception

    Also, provides the mechanism to control exceptions raised by parted library using a callback.

    Args:
        exception (cffi.FFI.CData): PedException to wrap

    """

    ExceptionHandler = typing.Callable[['PedException'], 'PedException.Option']

    class Option(enum.IntEnum):
        """PedException.Option enum

        Possible options available to handle exceptions raised by parted library.

        They are used as parameter (as a list of possible return values) for the exception handler callback,
        but also as return value for the exception handler callback.

        We can always, even if not passed as parameter, return PedException.Option.UNHANDLED, to notify parted
        library that we didn't handle the exception.
        """

        UNHANDLED = 0
        FIX = 1
        YES = 2
        NO = 4
        OK = 8
        RETRY = 16
        IGNORE = 32
        CANCEL = 64

        def __str__(self):
            return 'PedException.Option.' + self.name

        def __repr__(self) -> str:
            return self.__str__()

    class Type(enum.IntEnum):
        """PedException.Type enum

        Possible types of exceptions raised by parted library
        """

        INFORMATION = 1
        WARNING = 2
        ERROR = 3
        FATAL = 4
        BUG = 5
        FEATURE = 6

        def __str__(self):
            return 'PedException.Type.' + self.name

        def __repr__(self) -> str:
            return self.__str__()

    _exception_handler: typing.ClassVar[typing.Optional[typing.Callable[['PedException'], Option]]] = None
    _last_message: typing.ClassVar[str] = ''
    _exception: typing.Any = None

    def __init__(self, exception: typing.Optional['cffi.FFI.CData'] = None) -> None:
        """Creates a new PedException instance

        Args:
            exception (cffi.FFI.CData): PedException to wrap. Can be None.
        """
        self._exception = exception if exception else _parted.ffi.NULL

    def __bool__(self) -> bool:
        return bool(self._exception)

    @property
    def obj(self) -> 'cffi.FFI.CData':
        """wrapped ``PedException*`` object"""
        return self._exception

    @property
    def message(self) -> str:
        """Exception message"""
        if not self._exception:
            return ''
        return _parted.ffi.string(self._exception.message).decode()

    @property
    def type(self) -> Type:
        """Exception type"""
        if not self._exception:
            return PedException.Type.INFORMATION
        return self.Type(self._exception.type)

    @property
    def options(self) -> typing.Set[Option]:
        """Exception options"""
        if not self._exception:
            return set()
        return {x for x in self.Option if self._exception.options & x}

    @staticmethod
    def last_message() -> str:
        """Returns the last exception message

        Returns:
            str: Last exception message
        """
        return PedException._last_message

    @staticmethod
    def register_handler(handler: typing.Callable[['PedException'], 'PedException.Option']) -> None:
        """Register an exception handler

        Registers an exception handler, that will be called when a parted exception is raised.
        Note that exception handlers MUST return always a value in PedException.Option, or Option.UNHANDLED

        Args:
            handler (typing.Callable[[&#39;PedException&#39;], &#39;PedException.Option&#39;]): _description_
        """
        PedException._exception_handler = handler

    @staticmethod
    def restore_handler() -> None:
        """Restores the default exception handler"""
        PedException._exception_handler = None

    @staticmethod
    @contextlib.contextmanager
    def with_handler(handler: typing.Callable[['PedException'], 'PedException.Option']) -> typing.Iterator[None]:
        """Context manager to set a handler for exceptions, and restore it when exit.

        Args:
            handler (typing.Callable[[PedException], PedException.Option]): Exception handler to set

        Yields:
            None
        
        Note:
            This is a context manager, so it can be used with the ``with`` statement
        """
        old_handler = PedException._exception_handler
        PedException.register_handler(handler)
        try:
            yield
        finally:
            PedException.restore_handler()
            if old_handler is not None:
                PedException.register_handler(old_handler)

    @staticmethod
    def throw(type: 'PedException.Type', option: 'PedException.Option', message: str) -> None:
        """Throws a ``PedException``

        Args:
            type (PedException.Type): Exception type
            option (PedException.Option): Exception option
            message (str): Exception message

        Note:
            This is a wrapper around the ``ped_exception_throw`` function. See the parted documentation for more information.
        """
        _parted.lib.ped_exception_throw(type.value, option.value, message.encode())

    def __str__(self) -> str:
        return 'PedException: {} ({})'.format(self.message, self.type)


@_parted.ffi.def_extern()
def exception_handler(exc: 'cffi.FFI.CData') -> int:
    """Overriden default exception handler

    Warning:
        This function is called by parted library, and should not be called directly.

    Args:
        exc (cffi.FFI.CData): The exception raised by parted library (PedException)

    Returns:
        int: The option to use to handle the exception

    """
    try:  # pragma: no cover
        pedex = PedException(exc)
        
        # Save the last message thrown
        PedException._last_message = pedex.message

        if PedException._exception_handler is None:
            if pedex.type == PedException.Type.ERROR:
                logger.error('Error: %s', pedex.message)
            elif pedex.type == PedException.Type.WARNING:
                logger.warning('Warning: %s', pedex.message)
            elif pedex.type == PedException.Type.INFORMATION:
                logger.info('Information: %s', pedex.message)
            elif pedex.type == PedException.Type.FATAL:
                logger.critical('Fatal: %s', pedex.message)
            elif pedex.type == PedException.Type.BUG:
                logger.critical('Bug: %s', pedex.message)
            elif pedex.type == PedException.Type.FEATURE:
                logger.critical('No feature: %s', pedex.message)
            else:
                logger.critical('Unknown exception: %s', pedex.message)
            return PedException.Option.UNHANDLED.value

        value = PedException._exception_handler(pedex)
        # Value must be in received options
        if value in pedex.options or value == PedException.Option.UNHANDLED:
            return value.value

        logger.warning('Invalid exception handler return value: %s (must be one of %s)', value, pedex.options)
    except Exception as e:  # pragma: no cover
        logger.exception('Exception in PedException handler')

    return PedException.Option.UNHANDLED.value


# Install OUR default exception handler
_parted.lib.ped_exception_set_handler(_parted.lib.exception_handler)
