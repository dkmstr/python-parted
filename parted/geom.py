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
import logging

from . import _parted  # type: ignore

from . import exceptions, timer
from .util import ensure_obj, ensure_obj_or_default, make_destroyable, cache_on, OpenContext

from . import device

if typing.TYPE_CHECKING:
    import cffi

logger = logging.getLogger(__name__)


class Geometry:
    """This class represents a Geometry"""

    _geometry: typing.Any
    _destroyable: bool

    def __init__(
        self,
        geom_or_device: typing.Union['device.Device', 'cffi.FFI.CData', None] = None,
        start: int = 0,
        length: int = 0,
    ) -> None:
        """Creates a new Geometry object

        Args:
            geom_or_device (typing.Optional[typing.Union['device.Device', 'cffi.FFI.CData']], optional): A geometry or a device to create the geometry from. Defaults to None.
            start (int, optional): Start of the geometry. Defaults to 0.
            length (int, optional): Length of the geometry. Defaults to 0.
        """ """"""
        self._destroyable = False
        if isinstance(geom_or_device, device.Device):
            # If not a velid device, return an empty geometry
            if not geom_or_device:
                self._geometry = _parted.ffi.NULL
                return
            self._geometry = _parted.lib.ped_geometry_new(geom_or_device.obj, start, length)
            self._destroyable = True
        else:
            geom = typing.cast(typing.Any, _parted.ffi.NULL if not geom_or_device else geom_or_device)

            if geom and _parted.ffi.typeof(geom).cname == 'struct _PedGeometry':
                # If we get a PedGeometry, we need to copy it (may come from "partition" or "disk")
                self._geometry = _parted.lib.ped_geometry_new(geom.dev, geom.start, geom.length)
                self._destroyable = True
            else:
                self._geometry = geom

    def __del__(self) -> None:
        if self._geometry and self._destroyable:
            _parted.lib.ped_geometry_destroy(self._geometry)
            self._geometry = _parted.ffi.NULL

    def __bool__(self) -> bool:
        return bool(self._geometry)

    def __eq__(self, other: typing.Any) -> bool:
        if not isinstance(other, Geometry):
            return False

        if not self and not other:
            return True

        if not self or not other:
            return False

        return bool(_parted.lib.ped_geometry_test_equal(self._geometry, other._geometry))

    @property
    def obj(self) -> 'cffi.FFI.CData':
        """Wrapped ``PedGeometry*`` object"""
        return self._geometry

    @property  # type: ignore  # mypy does not like property decorators
    @cache_on('_cached_device')
    @ensure_obj_or_default(lambda: device.Device())
    def dev(self) -> 'device.Device':
        """Device of the geometry"""
        return device.Device(self._geometry.dev)

    @property  # type: ignore  # mypy does not like property decorators
    @ensure_obj_or_default(0)
    def start(self) -> int:
        """Start of the geometry"""
        return self._geometry.start

    @start.setter
    def start(self, value: int) -> None:
        """Sets the start of the geometry"""
        if not self._geometry:
            return  # Nothing to do

        if _parted.lib.ped_geometry_set_start(self._geometry, value) == 0:
            raise exceptions.PartedException("Invalid start sector")

    @property  # type: ignore  # mypy does not like property decorators
    @ensure_obj_or_default(0)
    def length(self) -> int:
        """Length of the geometry"""
        return self._geometry.length

    @length.setter
    def length(self, value: int) -> None:
        """Sets the length of the geometry"""
        if not self._geometry:
            return  # Nothing to do

        if _parted.lib.ped_geometry_set(self._geometry, self.start, value) == 0:
            raise exceptions.PartedException("Invalid length")

    @property  # type: ignore  # mypy does not like property decorators
    @ensure_obj_or_default(0)
    def end(self) -> int:
        """End of the geometry"""
        return self._geometry.end

    @end.setter
    def end(self, value: int) -> None:
        """Sets the end of the geometry"""
        if not self._geometry:
            return  # Nothing to do
        if _parted.lib.ped_geometry_set_end(self._geometry, value) == 0:
            raise exceptions.PartedException("Invalid end sector")

    @ensure_obj
    def __contains__(self, other: typing.Any) -> bool:
        """Checks if a geometry is contained in this geometry

        Args:
            other (typing.Any): The geometry to check

        Raises:
            exceptions.PartedException: If the geometry is not valid

        Returns:
            bool: True if the geometry is contained in this geometry, False otherwise

        Note:
            This is a wrapper for ``ped_geometry_test_inside``
        """
        if not isinstance(other, (Geometry, int)):
            return False

        if isinstance(other, Geometry):
            return bool(_parted.lib.ped_geometry_test_inside(self._geometry, other._geometry))
        elif isinstance(other, int):
            return bool(_parted.lib.ped_geometry_test_sector_inside(self._geometry, other))

        raise exceptions.PartedException("Invalid type {}".format(type(other)))

    @ensure_obj
    def __xor__(self, other: 'Geometry') -> 'Geometry':
        return self.intersect(other)

    @ensure_obj
    def intersect(self, other: 'Geometry') -> 'Geometry':
        """Returns the intersection of this geometry with another one

        Args:
            other (Geometry): The other geometry

        Returns:
            Geometry: The intersection geometry

        Note:
            This is a wrapper around ``ped_geometry_intersect``.
        """
        return make_destroyable(Geometry(_parted.lib.ped_geometry_intersect(self._geometry, other._geometry)))

    @ensure_obj
    def overlap(self, other: 'Geometry') -> bool:
        """Returns True if this geometry overlaps with another one

        Args:
            other (Geometry): The other geometry

        Returns:
            bool: True if the geometries overlap

        Note:
            This is a wrapper around the ``ped_geometry_test_overlap`` function.
        """
        return bool(_parted.lib.ped_geometry_test_overlap(self._geometry, other._geometry))

    @ensure_obj
    def duplicate(self) -> 'Geometry':
        """Returns a copy of this geometry

        Returns:
            Geometry: The copy

        Note:
            This is a wrapper around the ``ped_geometry_duplicate`` function.
        """
        return make_destroyable(Geometry(_parted.lib.ped_geometry_duplicate(self._geometry)))

    @ensure_obj
    def map(self, other: 'Geometry', sector: int) -> int:
        """
        This function takes a sector inside the region described by src, and
        returns that sector's address inside dst.
        The two geometries must be on the same device and, must overlap.

        Args:
            other: The geometry to map to
            sector: The sector to map
        Returns:
            The mapped sector or -1 if error
        """
        return _parted.lib.ped_geometry_map(other._geometry, self._geometry, sector)

    @ensure_obj
    def check(
        self,
        sector_offset: int,
        granularity: int = 1,  # Sectors to group on error
        count: int = 1,
        buffer_size: int = 1024,  # Buffer size, in sectors
        tmr: typing.Optional['timer.Timer'] = None,
    ) -> int:
        """Checks for physical disk errors.

        granularity specificies how sectors should be grouped together.
        The first bad sector to be returned will always be in the form:
        * offset + n * granularity

        return the first bad sector, or 0 if there were no physical errors

        Args:
            sector_offset (int): The sector offset to start checking
            granularity (int, optional): The granularity of how to group sectors. Defaults to 1.
            buffer_size (int, optional): The buffer size to use in sectors. Defaults to 1024.
            insectorstmr (typing.Optional["timer.Timer"], optional): The timer to use. Defaults to None.

        Returns:
            The first bad sector, or 0 if there were no physical errors

        Raises:
            exceptions.InvalidObjectError: If "self" geometry is invalid
            exceptions.NotOpenedError: If device is not opened
            exceptions.PartedException: If error

        Note:
            This is a wrapper around the ``ped_geometry_check`` function.
        """
        self.dev.wants_access()
        tmr = tmr or timer.Timer()

        buffer = _parted.ffi.new('char[]', buffer_size * self.dev.sector_size)  # 32K buffer

        return _parted.lib.ped_geometry_check(
            self._geometry, buffer, buffer_size, sector_offset, granularity, count, tmr.obj
        )

    @ensure_obj
    def set(self, start: int = -1, length: int = -1) -> None:
        """Sets the geometry

        Args:
            start (int): The start sector
            length (int): The length in sectors

        Raises:
            exceptions.InvalidDeviceError: If the device is invalid
            exceptions.PartedException: If any other error

        """
        if not self.dev:
            raise exceptions.InvalidDeviceError("Invalid device")
        if start == -1:
            start = self.start
        if length == -1:
            length = self.length
        
        # any other start will fail
        if start <= 0:
            raise exceptions.PartedException("Invalid start sector")
        if length <= 0:
            raise exceptions.PartedException("Invalid length")

        if _parted.lib.ped_geometry_set(self._geometry, start, length) == 0:
            raise exceptions.PartedException("Invalid geometry")

    @ensure_obj
    def sync(self) -> None:
        """Flushes the cache on geom.

        From the parted documentation:
            This function flushes all write-behind caches that might be holding
            writes made by ped_geometry_write() to geom.  It is slow, because
            it guarantees cache coherency among all relevant caches.

        Raises:
            exceptions.NotOpenedError: If the device is not opened
            exceptions.ReadOnlyError: If the device is read-only
            exceptions.PartedException: If any other error

        Note:
            This is a wrapper around the ``ped_geometry_sync`` function.
        """
        self.dev.wants_access(for_writing=True)
        if _parted.lib.ped_geometry_sync(self._geometry) == 0:
            raise exceptions.PartedException("Failed to sync geometry")

    @ensure_obj
    def sync_fast(self) -> None:
        """Flushes the cache on geom. ("Fast" version)

        From the parted documentation:
            This function flushes all write-behind caches that might be holding writes
            made by ped_geometry_write() to geom.  It does NOT ensure cache coherency
            with other caches that cache data in the region described by geom.
            If you need cache coherency, use sync() instead.

        Raises:
            exceptions.NotOpenedError: _description_
            exceptions.ReadOnlyError: _description_
            exceptions.IOError: _description_

        Note:
            This is a wrapper around the ``ped_geometry_sync_fast`` function.
        """
        self.dev.wants_access(for_writing=True)
        if _parted.lib.ped_geometry_sync_fast(self._geometry) == 0:
            raise exceptions.IOError("Failed to sync geometry")

    @ensure_obj
    def open(self) -> 'OpenContext':
        """Opens to read/write the geometry

        Returns:
            OpenContext: The context
        """
        self.dev.open()
        return OpenContext(self)

    @ensure_obj
    def close(self) -> None:
        """Closes the stream

        Raises:
            exceptions.NotOpenedError: If the device is not opened
        """
        self.dev.close()

    @ensure_obj
    def read(self, sector_offset: int, sector_count: int = 1) -> bytes:
        """Reads data from the geometry

        Args:
            sector_offset (int): The sector offset to start reading
            sector_count (int, optional): The number of sectors to read. Defaults to 1.

        Raises:
            exceptions.NotOpenedError: if the device is not opened
            exceptions.PartedException: if any other error

        Returns:
            bytes: _description_

        Note:
            This is a wrapper around the ``ped_geometry_read`` function.
        """
        self.dev.wants_access()

        if sector_offset < 0:
            raise exceptions.PartedException("Invalid sector offset")
        if sector_count < 0:
            raise exceptions.PartedException("Invalid sector count")

        buffer = _parted.ffi.new('char[]', sector_count * self.dev.sector_size)

        if _parted.lib.ped_geometry_read(self._geometry, buffer, sector_offset, sector_count) == 0:
            raise exceptions.PartedException("Failed to read geometry")

        return _parted.ffi.buffer(buffer)[:]  # a copy of the buffer

    @ensure_obj
    def write(self, data: bytes, sector_offset: int) -> None:
        """Writes data to the geometry

        Args:
            data (bytes): The data to write
            sector_offset (int): The sector offset to start writing  (from the beginning of the geometry)

        Raises:
            exceptions.PartedException: If any error
        """
        self.dev.wants_access(for_writing=True)

        if sector_offset < 0:
            raise exceptions.PartedException("Invalid sector offset")

        dev = self.dev
        sector_count = (len(data) + dev.sector_size - 1) // dev.sector_size
        buf = data[:]
        # If buf size is less than sector_count * sector_size, do a read-modify-write
        if len(buf) < sector_count * dev.sector_size:
            # Read last sector
            buffer = self.read(sector_offset + sector_count - 1)
            # add data to buffer
            buf += buffer[len(buf) % dev.sector_size:]

        _parted.lib.ped_geometry_write(self._geometry, buf, sector_offset, sector_count)

    @staticmethod
    def new(device: 'device.Device', start: int, length: int) -> 'Geometry':
        """
        Create a new PedGeometry object on disk, starting at start with a size of length sectors.

        Args:
            device (device.Device): The device to create the geometry on
            start (int): The start sector
            length (int): The length in sectors

        Returns:
            Geometry: The new geometry object
        """
        return make_destroyable(Geometry(_parted.lib.ped_geometry_new(device._device, start, length)))

    def __str__(self) -> str:
        return f'Geometry(start={self.start}, end={self.end}, length={self.length})'

    def __repr__(self) -> str:
        return self.__str__()
