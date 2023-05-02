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
This module contains Device and Device related classes

:author: Adolfo Gómez, dkmaster at dkmon dot com
"""
import typing
import logging
import enum

from . import _parted  # type: ignore

from . import exceptions, disk as mdisk
from .util import ensure_obj, ensure_root, ensure_obj_or_default, make_destroyable, OpenContext

if typing.TYPE_CHECKING:
    import cffi
    from . import geom
    from . import timer
    from . import disk

logger = logging.getLogger(__name__)


class DeviceType(enum.IntEnum):
    """Device types"""

    UNKNOWN = 0
    SCSI = 1
    IDE = 2
    DAC960 = 3
    CPQARRAY = 4
    FILE = 5
    ATARAID = 6
    I2O = 7
    UBD = 8
    DASD = 9
    VIODASD = 10
    SX8 = 11
    DM = 12
    XVD = 13
    SDMMC = 14
    VIRTBLK = 15
    AOE = 16
    MD = 17
    LOOP = 18
    NVME = 19
    RAM = 20
    PMEM = 21

    @staticmethod
    def from_string(s: str) -> 'DeviceType':
        """Returns a DeviceType from a string
        
        Args:
            s (str): String to convert

        Returns:
            DeviceType: DeviceType from string

        Raises:
            ValueError: If string is not a valid DeviceType
        
        """
        return DeviceType.__members__[s.upper()]

    def __str__(self) -> str:
        return f"DeviceType.{self.name}"

    def __repr__(self) -> str:
        return self.__str__()


class CHSGeometry:
    """Cylinders, heads and sectors geometry of a device"""

    cylinders: int
    heads: int
    sectors: int

    def __init__(self, cylinders: int, heads: int, sectors: int):
        """Creates a new CHSGeometry object

        Args:
            cylinders (int): Number of cylinders
            heads (int): Number of heads
            sectors (int): Number of sectors
        """
        self.cylinders = cylinders
        self.heads = heads
        self.sectors = sectors

    @property
    def total_sectors(self) -> int:
        """Total number of sectors in the device"""
        return self.cylinders * self.heads * self.sectors

    @staticmethod
    def from_partitiontable_msdos(data: bytes) -> 'CHSGeometry':
        """
        Creates a CHSGeometry from a partition table msdos data
        """
        return CHSGeometry(cylinders=data[0], heads=data[1] & 0x3F, sectors=((data[1] & 0xC0) << 2) | data[2])

    def __str__(self) -> str:
        return f"CHSGeometry(cylinders={self.cylinders}, heads={self.heads}, sectors={self.sectors})"

    def __repr__(self) -> str:
        return str(self)


class Device:
    """Wrapper for PedDevice*

    This class is a wrapper for the PedDevice* type, and provides a more pythonic interface to it.
    """

    _device: typing.Any  # PedDevice*
    def __init__(self, device: typing.Union[str, 'cffi.FFI.CData', 'Device', None] = None) -> None:
        """Creates a new Device object, if device is a string, it will be used as the path and create a new device

        Args:
            device (typing.Union[str, &#39;cffi.FFI.CData&#39;], optional): Device path or PedDevice*. Defaults to None.
        """
        if isinstance(device, str):
            self._device = _parted.lib.ped_device_get(device.encode())
        elif isinstance(device, Device):
            self._device = device._device
        else:
            self._device = device if device else _parted.ffi.NULL

    def __bool__(self) -> bool:
        """Returns True if the device is valid, False otherwise

        Returns:
            bool: True if the device is valid, False otherwise
        """
        return bool(self._device)

    def __eq__(self, other: typing.Any) -> bool:
        """Returns True if the other object is a Device and has the same underlying PedDevice* or it other is a string and
        the path of the device is the same as the other string

        Args:
            other (typing.Any): Other object to compare (must be a Device or a string)

        Returns:
            bool: True if the other object is a Device and has the same underlying PedDevice* or it other is a string and
            the path of the device is the same as the other string
        """
        if isinstance(other, Device):
            return self._device == other._device
        elif isinstance(other, str):
            return self.path == other
        return False

    @property
    def obj(self) -> 'cffi.FFI.CData':
        """Wrapped ``PedDevice*`` object"""
        return self._device

    @property  # type: ignore # (mypy does not recognizes properties and decorators)
    @ensure_obj_or_default('Unknown')
    def model(self) -> str:
        """device model(e.g. ""ATA ST4000VN008-2DR1", "Linux device-mapper (linear)", "QEMU HARDDISK", "Unknown")"""
        return _parted.ffi.string(self._device.model).decode()

    @property  # type: ignore # (mypy does not recognizes properties and decorators)
    @ensure_obj_or_default('')
    def path(self) -> str:
        """device path (e.g. /dev/sda, file.img, etc)"""
        return _parted.ffi.string(self._device.path).decode()

    @property  # type: ignore # (mypy does not recognizes properties and decorators)
    @ensure_obj_or_default(DeviceType.UNKNOWN)
    def type(self) -> DeviceType:
        """Device type"""
        return DeviceType(self._device.type)

    @property  # type: ignore # (mypy does not recognizes properties and decorators)
    @ensure_obj_or_default(0)
    def sector_size(self) -> int:
        """The device sector size (e.g. 512, 4096, etc)"""
        return self._device.sector_size

    @property  # type: ignore # (mypy does not recognizes properties and decorators)
    @ensure_obj_or_default(0)
    def phys_sector_size(self) -> int:
        """The device physical sector size (e.g. 512, 4096, etc)"""
        return self._device.phys_sector_size

    @property  # type: ignore # (mypy does not recognizes properties and decorators)
    @ensure_obj_or_default(0)
    def length(self) -> int:
        """Device length in sectors"""
        return self._device.length

    @property
    def size(self) -> int:
        """Device size in bytes"""
        return self.sector_size * self.length

    @property  # type: ignore # (mypy does not recognizes properties and decorators)
    @ensure_obj_or_default(0)
    def open_count(self) -> int:
        """number of times the device has been opened"""
        return self._device.open_count

    @property  # type: ignore # (mypy does not recognizes properties and decorators)
    @ensure_obj_or_default(True)
    def read_only(self) -> bool:
        """if the device is read only"""
        return bool(self._device.read_only)

    @property  # type: ignore # (mypy does not recognizes properties and decorators)
    @ensure_obj_or_default(False)
    def external_mode(self) -> bool:
        """if the device is in external access mode"""
        return bool(self._device.external_mode)

    @property  # type: ignore # (mypy does not recognizes properties and decorators)
    @ensure_obj_or_default(False)
    def dirty(self) -> bool:
        """if the device is dirty"""
        return bool(self._device.dirty)

    @property  # type: ignore # (mypy does not recognizes properties and decorators)
    @ensure_obj_or_default(False)
    def boot_dirty(self) -> bool:
        """Returns:
        bool: True if the device is set to boot dirty
        """
        return bool(self._device.boot_dirty)

    @property  # type: ignore # (mypy does not recognizes properties and decorators)
    @ensure_obj_or_default(lambda: CHSGeometry(0, 0, 0))
    def hw_geom(self) -> CHSGeometry:
        """Returns:
        CHSGeometry: The device hardware geometry
        """
        return CHSGeometry(
            self._device.hw_geom.cylinders,
            self._device.hw_geom.heads,
            self._device.hw_geom.sectors,
        )

    @property  # type: ignore # (mypy does not recognizes properties and decorators)
    @ensure_obj_or_default(lambda: CHSGeometry(0, 0, 0))
    def bios_geom(self) -> CHSGeometry:
        """Returns:
        CHSGeometry: The device BIOS geometry
        """
        return CHSGeometry(
            self._device.bios_geom.cylinders,
            self._device.bios_geom.heads,
            self._device.bios_geom.sectors,
        )

    @property  # type: ignore # (mypy does not recognizes properties and decorators)
    @ensure_obj_or_default(0)
    def host(self) -> int:
        """The host number of the device"""
        return self._device.host

    @property  # type: ignore # (mypy does not recognizes properties and decorators)
    @ensure_obj_or_default(0)
    def did(self) -> int:
        """The device id of the device"""
        return self._device.did

    @property  # type: ignore # (mypy does not recognizes properties and decorators)
    @ensure_obj_or_default(False)
    def is_busy(self) -> bool:
        """If the device

        Note:
            This is a wrapper around the ``ped_device_is_busy`` function
        """
        return bool(_parted.lib.ped_device_is_busy(self._device))

    @property  # type: ignore # (mypy does not recognizes properties and decorators)
    @ensure_obj_or_default(False)
    def is_opened(self) -> bool:
        """Returns True if the device is opened

        Returns:
            bool: True if the device is opened
        """
        return bool(self._device.open_count)

    @ensure_obj
    def wants_access(self, for_writing: bool = False) -> None:
        """Raises an exception if the device cannot be accesed
        
        The device is "accesible" if it's opened and not is in external access mode.
        if "for_writing" is True, the device must be opened not read only.

        Args:
            for_writing (bool, optional): If the device is opened for writing. Defaults to False.

        Raises:
            exceptions.InvalidDeviceError: If the device is not accesible

        """
        if not self.is_opened:
            raise exceptions.NotOpenedError(
                "Device is not opened", self.path
            )
        if self.external_mode != 0:
            raise exceptions.InvalidDeviceError(
                "Device is in external access mode", self.path
            )
        if for_writing and self.read_only:
            raise exceptions.ReadOnlyError(
                "Device is opened read only", self.path
            )

    def next(self) -> 'Device':
        """Returns:
            Device: The next device in the list, if any, or a Device with _device set to NULL

        Note:
            This is a wrapper around the ``ped_device_get_next`` function

        """
        if not self._device:
            return Device()
        return Device(_parted.lib.ped_device_get_next(self._device))

    @ensure_obj
    def open(self, mode: typing.Literal['r', 'rw'] = 'rw') -> 'OpenContext':
        """Opens the device, allowing read/write access

        Args:
            for_writing (bool): True if the device should be opened for writing (default: True)

        Raises:
            exceptions.InvalidObjectError: If the wrapped device is not valid
            exceptions.IOError: If the device cannot be opened

        Note:
            This is a wrapper around the ``ped_device_open`` function
        """
        if _parted.lib.ped_device_open(self._device) == 0:  # pragma: no cover
            raise exceptions.IOError("Failed to open device")

        self._device.read_only = mode == 'r'
        logger.debug('Opened device %s', self.path)

        return OpenContext(self)

    @ensure_obj
    def close(self) -> None:
        """Closes the device, disallowing read/write access.

        Raises:
            exceptions.InvalidObjectError: If the wrapped device is not valid
            exceptions.IOError: If the device cannot be closed

        Note:
            This is a wrapper around the ``ped_device_close`` function
        """
        if not self.is_opened:
            return

        if _parted.lib.ped_device_close(self._device) == 0:  # pragma: no cover
            raise exceptions.IOError("Failed to close device")

        logger.debug('Closed device %s', self.path)
        return

    @ensure_obj
    def read(self, sector_start: int, sector_count: int) -> bytes:
        """Reads the specified number of sectors from the device, starting at the specified sector

        Args:
            sector_start (int): The sector to start reading from
            sector_count (int): The number of sectors to read

        Returns:
            bytes: The data read from the device

        Raises:
            exceptions.InvalidObjectError: If the wrapped device is not valid
            exceptions.IOError: If the read fails

        Note:
            This is a wrapper around the ``ped_device_read`` function
        """
        self.wants_access()

        if sector_start < 0:
            sector_start = self.length + sector_start  # from end

        buffer = _parted.ffi.new("char[]", sector_count * self.sector_size)

        if _parted.lib.ped_device_read(self._device, buffer, sector_start, sector_count) == 0:
            raise exceptions.IOError("Failed to read from device")

        return _parted.ffi.buffer(buffer)[:]

    @ensure_obj
    def write(self, buffer: bytes, sector_start: int, sector_count: int) -> None:
        """Write buffer to device.

        Args:
            buffer (bytes): Buffer to write to device.
            sector_start (int): Sector to start writing at.
            sector_count (int): Number of sectors to write.

        Raises:
            exceptions.InvalidObjectError: If the wrapped device is not valid
            exceptions.IOError: If the write fails
            exceptions.NotOpenedError: If the device is not opened

        Note:
            This is a wrapper around the ``ped_device_write`` function
        """
        self.wants_access(for_writing=True)

        if sector_start < 0:
            sector_start = self.length + sector_start  # from end

        # If buffer size is less than sector_count * sector_size, pad with zeros
        buf = buffer
        if len(buf) < sector_count * self.sector_size:
            buf += b"\0" * (sector_count * self.sector_size - len(buf))

        if _parted.lib.ped_device_write(self._device, buf, sector_start, sector_count) == 0:
            raise exceptions.IOError("Failed to write to device")

    @ensure_obj
    def copy(
        self, source: 'geom.Geometry', to: int, tm: typing.Optional['timer.Timer'] = None, sectors_block: int = 32
    ) -> None:
        """Copies the data from one region to another

        Args:
            from (geom.Geometry): The geometry to copy from
            to (int): The sector to start copying to

        Raises:
            exceptions.InvalidObjectError: If the wrapped device is not valid
            exceptions.NotOpenedError: If the device is not opened
            exceptions.IOError: If the copy fails

        Important:
             The device needs to be opened before calling this function.
        """
        if source.start == to:  # same region
            return

        self.wants_access(for_writing=True)

        # Determine direction of the copy (from start to end or end to start)
        # so we don't overwrite data we're copying
        def do_copy(sector_num: int, size: int):
            if tm:
                tm.update(float(sector_num) / source.length)
            self.write(
                self.read(source.start + sector_num, size),
                to + sector_num,
                size,
            )

        block_count = source.length // sectors_block  # for copying block_size sectors per block
        block_rest = source.length % sectors_block  # for copying the rest of sectors

        if source.start > to:
            range_block = range(block_count)
        else:
            range_block = range(block_count - 1, -1, -1)

        for blk in range_block:
            do_copy(blk * sectors_block, sectors_block)
        # Last block
        if block_rest:
            do_copy(block_count * sectors_block, block_rest)

    @ensure_obj
    def sync(self) -> None:
        """Flushes the device's write cache

        Raises:
            exceptions.InvalidObjectError: If the wrapped device is not valid
            exceptions.NotOpenedError: If the device is not opened
            exceptions.IOError: If the sync fails

        Important:
            The device needs to be opened before calling this function.

        Note:
            This is a wrapper around the ``ped_device_sync`` function       
        """
        self.wants_access(for_writing=True)

        if _parted.lib.ped_device_sync(self._device) == 0:  # pragma: no cover
            raise exceptions.IOError("Failed to sync device")

    @ensure_obj
    def sync_fast(self) -> None:
        """Flushes the device's write cache

        Raises:
            exceptions.InvalidObjectError: If the wrapped device is not valid

        Important:
            The device needs to be opened before calling this function

        Note:
            This is a wrapper around the ``ped_device_sync_fast`` function
        """
        self.wants_access(for_writing=True)

        if _parted.lib.ped_device_sync_fast(self._device) == 0:  # pragma: no cover
            raise exceptions.IOError("Failed to fast sync device")

    @ensure_obj
    def begin_external_access(self, read_only: bool = False) -> None:  # pragma: no cover
        """Begins external access to the device
        Invokes the ``ped_device_begin_external_access`` function

        Args:
            read_only (bool): Whether the device is opened read-only

        Raises:
            exceptions.InvalidObjectError: If the wrapped device is not valid
            exceptions.PartedException: If the access could not be granted

        Note:
            This is a wrapper around the ``ped_device_begin_external_access`` function

        """
        if _parted.lib.ped_device_begin_external_access(self._device, read_only) == 0:
            raise exceptions.PartedException("Failed to begin external access")

    @ensure_obj
    def end_external_access(self) -> None:
        """Ends external access to the device

        Invokes the ``ped_device_end_external_access`` function

        Raises:
            exceptions.InvalidObjectError: If the wrapped device is not valid
            exceptions.PartedException: If the access could not be ended

        Note:
            This is a wrapper around the ``ped_device_end_external_access`` function
        """
        if _parted.lib.ped_device_end_external_access(self._device) == 0:  # pragma: no cover
            raise exceptions.PartedException("Failed to end external access")

    @ensure_obj
    def probe(self) -> 'mdisk.DiskType':
        """Get the partition table type of the device.

        Args:
            device (device.Device): The device to probe

        Returns:
            DiskType: The disk type

        Note:
            This is a wrapper around the ``ped_disk_probe`` function
        """
        return mdisk.DiskType(_parted.lib.ped_disk_probe(self._device))

    @ensure_obj
    def clobber(self) -> None:
        """Clobber the partition table on the device. Does not need to be opened before.

        As a protection, the device must be opened for writing before calling this function.
        Args:
            device (device.Device): The device to clobber

        Returns:
            bool: True on success, False on error

        Warning:
            Handle with care! will destroy all the partions on the device!!.
            Data will be written to the device as soon as this function is called.

        Note:
            This is a wrapper around the ``ped_disk_clobber`` function

        """
        self.wants_access(for_writing=True)
        
        if _parted.lib.ped_disk_clobber(self._device) == 0:
            raise exceptions.PartedException("Failed to clobber device")

    @ensure_obj
    def read_table(self) -> 'mdisk.Disk':
        """Reads the partition table from the device and returns a new Disk object.

        Args:
            dev (device.Device): The device to read the partition table from.

        Returns:
            Disk: A new Disk object.

        Warning:
            The device object cilinders, heads and sectors can be modified by this call
            if the partition table indicates that the existing values are incorrect.

        Note:
            This is a wrapper around the ``ped_disk_new`` function
        """
        return mdisk.Disk(self)

    @ensure_obj
    def new_table(self, type: typing.Union[str, 'mdisk.DiskType', 'mdisk.DiskType.WNT']) -> 'mdisk.Disk':
        """
        Creates a new partition table on the disk.

        Args:
            dev (device.Device): The device to create the partition table on.
            type (DiskType): The type of partition table to create. (e.g. 'gpt', 'msdos', 'bsd', ...)

        Returns:
            Partition: The new partition.

        Important:
            The new table is created "in memory" only. You must call the commit_to_dev() method to write it to the device.

        Note:
            This is a wrapper around the ``ped_disk_new_fresh`` function

        Raises:
            exceptions.InvalidDeviceError: if the device is invalid
        """
        type = mdisk.DiskType(type) if not isinstance(type, mdisk.DiskType) else type
        if not self:
            raise exceptions.InvalidDeviceError('Invalid device: {}'.format(self))
        dsk = make_destroyable(mdisk.Disk(_parted.lib.ped_disk_new_fresh(self._device, type.obj)))
        return dsk

    @staticmethod
    def get(name: str) -> 'Device':
        """Get device by name.

        Args:
            name (str): Name of device. (i.e. filename, '/dev/sda', etc.)

        Returns:
            Device: Device object.

        Note:
            This is a wrapper around the ``ped_device_get`` function
        """
        return Device(_parted.lib.ped_device_get(name.encode()))

    @staticmethod
    @ensure_root
    def enumerate() -> typing.Iterator['Device']:
        """Enumerate all devices.

        Yields:
            Device: Device object.

        Raises:
            exceptions.PartedException: If the device could not be enumerated (e.g. permission denied)

        Note:
            This is a wrapper around the ``ped_device_get_next`` function
        """
        device = _parted.lib.ped_device_get_next(_parted.ffi.NULL)
        while device:
            yield Device(device)
            device = _parted.lib.ped_device_get_next(device)

    @staticmethod
    @ensure_root
    def probe_all() -> None:
        """Probe all devices. (needs to be root)

        Raises:
            exceptions.PartedException: If the device could not be probed (e.g. permission denied)

        Note:
            This is a wrapper around the ``ped_device_probe_all`` function
        """
        _parted.lib.ped_device_probe_all()

    @staticmethod
    def free_all() -> None:
        """Clear all devices from memory

        Note:
            This is a wrapper around the ``ped_device_free_all`` function
        """
        _parted.lib.ped_device_free_all()

    def __str__(self) -> str:
        return (
            f'Device: path: {self.path}, type: {self.type.name}, model: '
            f'"{self.model}", length: {self.length}, '
            f'size: {self.sector_size*self.hw_geom.sectors*self.hw_geom.heads*self.hw_geom.cylinders}'
        )

    def __repr__(self) -> str:
        return self.__str__()
