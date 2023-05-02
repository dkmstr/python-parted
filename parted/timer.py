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
Timer interface to "PedTimer" in parted

:author: Adolfo Gómez, dkmaster at dkmon dot com
"""
import typing
import logging
import cffi

from . import _parted  # type: ignore

from .util import ensure_obj, ensure_obj_or_default, make_destroyable
from . import exceptions

logger = logging.getLogger(__name__)


@_parted.ffi.def_extern()
def timer_handler(timer: 'cffi.FFI.CData', context: 'cffi.FFI.CData') -> None:
    """Timer handler, called by parted when timer is triggered
    
    Warning:
        This is the timer callback, it's called by parted. Not directly by the user.

    """
    try:
        # Context is a "Timer" object, cast it to a python object
        timer_instance = typing.cast(Timer, _parted.ffi.from_handle(context))
        if not timer_instance:  # Invoked during timer creation, ignore
            return
        timer_instance.process_event()
    except Exception as e:
        logger.error('Exception in timer_handler: %s', e, exc_info=True)


class Timer:
    """Timer interface to "PedTimer" in parted"""
    _timer: typing.Any = None  # PedTimer*
    _destroyable: bool
    _is_nested: bool
    _userdata: typing.Any
    _callback: typing.Optional[typing.Callable[['Timer'], typing.Any]] = None

    def __init__(self, timer: typing.Optional['cffi.FFI.CData'] = None) -> None:
        """Constructor

        Args:
            timer (cffi.FFI.CData, optional): PedTimer* to use. Defaults to None.
        """
        self._destroyable = False
        self._is_nested = False
        self._callback = None
        self._userdata = None
        self._timer = timer if timer else _parted.ffi.NULL

    def __del__(self):
        if self._timer and self._destroyable:
            if not self._is_nested:
                _parted.lib.ped_timer_destroy(self._timer)
                self._is_nested = False
            else:
                _parted.lib.ped_timer_destroy_nested(self._timer)
            self._timer = None
            self._destroyable = False

    def __bool__(self) -> bool:
        return bool(self._timer)

    @property
    def obj(self) -> 'cffi.FFI.CData':
        """Wrapped ``PedTimer*`` object"""
        return self._timer

    @property  # type: ignore
    @ensure_obj_or_default(0.0)
    def frac(self) -> float:
        """Fraction of the timer elapsed"""
        return typing.cast(float, self._timer.frac)

    @property  # type: ignore
    @ensure_obj_or_default(0)
    def start(self) -> int:
        """Start time of the timer"""
        return typing.cast(int, self._timer.start)

    @property  # type: ignore
    @ensure_obj_or_default(0)
    def now(self) -> int:
        """Current time of the timer"""
        return typing.cast(int, self._timer.now)

    @property  # type: ignore
    @ensure_obj_or_default(0)
    def predicted_end(self) -> int:
        """Predicted end time of the timer"""
        return typing.cast(int, self._timer.predicted_end)

    @property
    def state_name(self) -> typing.Optional[str]:
        """Returns the name of the current state of the timer"""
        if not self._timer or not self._timer.state_name:
            return None
        return typing.cast(str, _parted.ffi.string(self._timer.state_name))

    # Note: cffi will generate a temporary buffer, and setting the timer
    # to this buffer, that will be destroyed after the call, is not a good idea
    # so we comment this out
    # @state_name.setter
    # def state_name(self, value: str) -> None:
    #    if self.timer is None:
    #        raise ValueError("Timer not initialized")
    #    _parted.lib.ped_timer_set_state_name(self.timer, value.encode())

    @ensure_obj
    def touch(self) -> None:
        """Updates the timer
        
        Note:
            This is a wrapper for ``ped_timer_touch``
        """
        _parted.lib.ped_timer_touch(self._timer)

    @ensure_obj
    def reset(self) -> None:
        """Resets the timer"""
        _parted.lib.ped_timer_reset(self._timer)

    @ensure_obj
    def update(self, frac: float) -> None:
        """Updates the timer with a fraction

        Args:
            frac (float): Fraction to update the timer with

        Note:
            This is a wrapper for ``ped_timer_update``
        """
        _parted.lib.ped_timer_update(self._timer, frac)

    def process_event(self):
        """Processes the timer event
        
        Note:
            This method is invoked by the timer callback when the timer is triggered.
            By default, it just calls the callback, if any.
            You can override this method to do something else, but maybe easier to just
            set a callback
        """
        logger.debug('Timer event %f, %d/%d', self.frac, self.start, self.now)
        if self._callback:
            self._callback(self)

    @staticmethod
    def new(callback: typing.Optional[typing.Callable[['Timer'], None]] = None) -> 'Timer':
        """Creates a new timer

        Args:
            callback (typing.Optional[typing.Callable[['Timer'], None]], optional): Callback to invoke when the timer is triggered. Defaults to None.

        Returns:
            Timer: New timer

        Note:
            This is a wrapper for ``ped_timer_new``, that returns a python Timer object
        """

        timer = make_destroyable(Timer(None))  # With _destroyable = True
        # Have to store handle, because handle will be destroyed if not referenced
        timer._callback = callback
        timer._userdata = _parted.ffi.new_handle(timer)
        timer._timer = _parted.lib.ped_timer_new(_parted.lib.timer_handler, timer._userdata)
        # Invoke update to set start time
        timer.reset()
        return timer

    @staticmethod
    def new_nested(parent: 'Timer', nest_frac: float = 0, callback: typing.Optional[typing.Callable[['Timer'], None]] = None) -> 'Timer':
        """Creates a new nested timer

        Args:
            parent (Timer): Parent timer
            nest_frac (float, optional): Fraction of the parent timer to nest. Defaults to 0.
            callback (typing.Optional[typing.Callable[['Timer'], None]], optional): Callback to invoke when the timer is triggered. Defaults to None.

        Returns:
            Timer: New timer
        """
        if not parent:
            raise exceptions.InvalidObjectError('Parent timer is not initialized')

        timer = make_destroyable(Timer(None))
        timer._is_nested = True
        timer._callback = callback
        timer._timer = _parted.lib.ped_timer_new_nested(parent._timer, nest_frac)
        timer._userdata = _parted.ffi.new_handle(timer)
        return timer
