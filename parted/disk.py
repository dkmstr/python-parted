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
This module contains Disk and Partition related classes

:author: Adolfo Gómez, dkmaster at dkmon dot com
"""
import enum
import logging
from turtle import st
import typing

from . import _parted  # type: ignore
from . import constraint, device, exceptions, filesys, geom, alignment
from .util import ensure_obj, ensure_obj_or_default, ensure_valid_or_default, make_destroyable, cache_on

if typing.TYPE_CHECKING:
    import cffi

    from . import excpt

logger = logging.getLogger(__name__)


class PartitionType(enum.Flag):
    """Type of partition"""

    NORMAL = 0x00
    LOGICAL = 0x01
    EXTENDED = 0x02
    FREE = 0x04
    METADATA = 0x08  # Metadata is not a real partition type, but a flag. The Partition Table itself is a metadata partition i.e.
    PROTECTED = 0x10

    LOGICAL_METADATA = LOGICAL | METADATA
    LOGICAL_FREE = LOGICAL | FREE

    @staticmethod
    def from_string(ptype: str) -> 'PartitionType':
        """Returns a PartitionType from a name
        
        Args:
            name (str): Name of the PartitionType to get

        Returns:
            PartitionType: The PartitionType with the given name

        Raises:
            ValueError: If the name is not a valid PartitionType name
        """
        return PartitionType[ptype.upper()]

    def __str__(self) -> str:
        return f'PartitionType.{self.name}'

    def __repr__(self) -> str:
        return self.__str__()

    @property
    def is_valid(self) -> bool:
        return not (self.value & PartitionType.FREE.value | self.value & PartitionType.METADATA.value)


class PartitionFlag(enum.IntEnum):
    """Partition flags"""

    BOOT = 1
    ROOT = 2
    SWAP = 3
    HIDDEN = 4
    RAID = 5
    LVM = 6
    LBA = 7
    HPSERVICE = 8
    PALO = 9
    PREP = 10
    MSFT_RESERVED = 11
    BIOS_GRUB = 12
    APPLE_TV_RECOVERY = 13
    DIAG = 14
    LEGACY_BOOT = 15
    MSFT_DATA = 16
    IRST = 17
    ESP = 18
    CHROMEOS_KERNEL = 19
    BLS_BOOT = 20
    LINUX_HOME = 21

    @staticmethod
    def from_string(flag: str) -> 'PartitionFlag':
        """Returns a PartitionFlag from its name if exits, else raises an exception
        
        Args:
            name (str): Name of the PartitionFlag to get

        Returns:
            PartitionFlag: The PartitionFlag with the given name

        Raises:
            ValueError: If the name is not a valid PartitionFlag name
        """
        return PartitionFlag.__members__[flag.upper()]

    def __str__(self) -> str:
        return 'PartitionFlag.{}'.format(self.name)

    def __repr__(self) -> str:
        return self.__str__()


class Partition:
    """Wrapper for PedPartition
    A partition is a contiguous region of a disk.  It has a type, a
    filesystem type, a name, and a geometry.  It also has flags.
    """

    _partition: typing.Any = None
    _destroyable: bool = False

    def __init__(self, partition: typing.Optional['cffi.FFI.CData']):
        """Creates a new partition from a PedPartition object

        Args:
            partition (cffi.FFI.CData): PedPartition object or None
        """
        self._partition = partition if partition else _parted.ffi.NULL

    def __bool__(self) -> bool:
        return bool(self._partition)

    def __del__(self):
        # Only partitions created with "new" will be needed to "destroy"
        if self._destroyable and self._partition:
            _parted.lib.ped_partition_destroy(self._partition)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Partition):
            return str(self) == str(other)
        return False

    @property
    def obj(self) -> 'cffi.FFI.CData':
        """Wrapped ``PedPartition*`` object"""
        return self._partition

    @property  # type: ignore  # mypy does not like properties with decorators
    @ensure_obj_or_default(lambda: Disk(None))
    @cache_on('cached_disk')
    def disk(self) -> 'Disk':
        """The disk this partition belongs to"""
        return Disk(self._partition.disk)

    @property  # type: ignore  # mypy does not like properties with decorators
    @ensure_obj_or_default(lambda: geom.Geometry(None))
    def geometry(self) -> 'geom.Geometry':
        """The geometry of this partition"""
        return geom.Geometry(self._partition.geom).duplicate()

    @property  # type: ignore  # mypy does not like properties with decorators
    @ensure_obj_or_default(-9999)
    def num(self) -> int:
        """The number of this partition"""
        return self._partition.num

    @property  # type: ignore  # mypy does not like properties with decorators
    @ensure_obj_or_default(PartitionType.FREE)
    @cache_on('cached_type')
    def type(self) -> PartitionType:
        """The type of this partition"""
        return PartitionType(self._partition.type)

    @property  # type: ignore  # mypy does not like properties with decorators
    @ensure_obj_or_default(lambda: filesys.FileSystemType())
    @cache_on('cached_filesystemtype')
    def fs_type(self) -> 'filesys.FileSystemType':
        """The filesystem type of this partition"""
        return filesys.FileSystemType(self._partition.fs_type)

    @property  # type: ignore  # mypy does not like properties with decorators
    @ensure_valid_or_default('is_valid', '')
    def path(self) -> str:
        """The path of this partition"""
        return _parted.ffi.string(_parted.lib.ped_partition_get_path(self._partition)).decode()

    @property  # type: ignore  # mypy does not like properties with decorators
    @ensure_valid_or_default('is_valid', lambda: set())
    def flags(self) -> typing.Set[PartitionFlag]:
        """The flags of this partition

        Only valid partitions, with valid disk and type of partitions that support flags will be considered

        Returns:
            set of PartitionFlag
        """
        if not self._partition.disk.type.ops.partition_get_flag:
            return set()
        return {flag for flag in PartitionFlag if _parted.lib.ped_partition_get_flag(self._partition, flag.value)}

    @property
    def name(self) -> str:
        """The name of this partition"""
        if not self.is_valid or DiskType.Feature.NAME not in self.disk.type.features:
            return ''
        _name = _parted.lib.ped_partition_get_name(self._partition)
        if _name:
            return _parted.ffi.string(_name).decode()
        return ''  # pragma: no cover

    @name.setter
    def name(self, name: str) -> None:
        """Sets the name of this partition

        Args:
            name (str): The new name

        Note:
            This is a wrapper around the ``ped_partition_set_name`` function

        """
        if not self.is_valid or DiskType.Feature.NAME not in self.disk.type.features:
            return
        _parted.lib.ped_partition_set_name(self._partition, name.encode())

    @property  # type: ignore  # mypy does not like properties with decorators
    @ensure_valid_or_default('is_valid', False)
    def busy(self) -> bool:
        """Whether this partition is busy"""
        if not self.is_valid:
            return False
        return bool(_parted.lib.ped_partition_is_busy(self._partition))

    @property  # type: ignore  # mypy does not like properties with decorators
    @ensure_obj_or_default(False)
    def active(self) -> bool:
        """True if the partition is active, False otherwise
        A partition is active is it not a metadata or free space partition
        """
        # Active partitions are not metadata or free space partitions
        return self.type.is_valid
        # return _parted.lib.ped_partition_is_active(self._partition):

    @property
    def extended_list(self) -> typing.List['Partition']:
        """List of extended partitions

        Returns:
            typing.List[Partition]: List of extended partitions

        Note:
            Maybe this parition is not an extended partition. In this case, the list will be empty
        """
        ret: typing.List['Partition'] = []
        if self._partition and PartitionType.EXTENDED in self.type:
            part = self._partition.part_list  # first
            while part:
                ret.append(Partition(part))
                part = part.next

        return ret

    @property
    def extended_list_active(self) -> typing.List['Partition']:
        """List of active extended partitions

        Returns:
            typing.List[Partition]: List of active extended partitions

        Note:
            Maybe this parition is not an extended partition. In this case, the list will be empty
        """
        return [part for part in self.extended_list if part.active]

    @property
    def extended_list_free(self) -> typing.List['Partition']:
        """List of free extended partitions

        Returns:
            typing.List[Partition]: List of free extended partitions

        Note:
            Maybe this parition is not an extended partition. In this case, the list will be empty
        """
        return [part for part in self.extended_list if part.type & PartitionType.FREE]

    @property
    def is_valid(self) -> bool:
        """True if the partition is validself.
        A partition will be considered valid if it's not freespace, is not metadata, is attached to a disk and can be operated)
        """
        return bool(
            self._partition
            and self.active
            and self._partition.disk
            and self._partition.disk.type
            and self._partition.disk.type.ops
        )

    @ensure_obj
    def add_to_disk(self, constraint: 'constraint.Constraint') -> None:
        """Adds this partition to the disk

        Args:
            constraint (Constraint): The constraint to use
        """
        if not self.is_valid:
            raise exceptions.InvalidPartitionError('Could not operate on this partition type')

        self.disk.add_partition(self, constraint)

    @ensure_obj
    def delete(self) -> None:
        '''Deletes the partition

        Note:
            After deleting the partition, the object will be set to NULL.
            The changes are done "in memory" and will be written to disk only if you call the ``commit_to_dev`` method of the disk
        '''
        if not self.is_valid:
            raise exceptions.InvalidPartitionError('Could not operate on this partition type')

        self.disk.delete_partition(self)  # will reset _partition and _destroyable

    @ensure_obj
    def set_geometry(self, const: 'constraint.Constraint', sector_start: int, sector_end: int) -> None:
        """Sets the geometry of this partition

        Args:
            const (Constraint): The constraint to use
            sector_start (int): The new start sector
            sector_end (int): The new end sector

        Raises:
            exceptions.InvalidPartitionError: If the partition is not valid for this operation

        Note:
            This is a wrapper around the ``ped_partition_set_geometry`` function
        """
        if not self.is_valid:
            raise exceptions.InvalidPartitionError('Could not operate on this partition type')

        self.disk.set_partition_geometry(self, const, sector_start, sector_end)

    @ensure_obj
    def set_flag(self, flag: PartitionFlag, state: bool = True) -> None:
        """Sets the flag of this partition

        Args:
            flag (PartitionFlag): The flag to set
            state (bool): The state of the flag

        Raises:
            exceptions.InvalidPartitionError: If the partition is not valid for this operation

        Note:
            This is a wrapper around the ``ped_partition_set_flag`` function
        """
        if not self.is_valid:
            raise exceptions.InvalidPartitionError('Could not operate on this partition type')

        if _parted.lib.ped_partition_is_flag_available(self._partition, flag.value):
            _parted.lib.ped_partition_set_flag(self._partition, flag.value, state)

    @ensure_obj
    def max_geometry(self, constraint: 'constraint.Constraint') -> 'geom.Geometry':
        """Returns the maximum geometry of this partition

        Args:
            constraint (Constraint): The constraint to use

        Returns:
            geom.Geometry: The maximum geometry

        Raises:
            exceptions.InvalidPartitionError: If the partition is not valid for this operation

        Note:
            This is a wrapper around the ``ped_partition_maximize`` function
        """
        if not self.is_valid:
            raise exceptions.InvalidPartitionError('Could not operate on this partition type')
        return self.disk.get_max_partition_geometry(self, constraint)

    @ensure_obj
    def maximize(self, constraint: 'constraint.Constraint') -> None:
        """Maximizes the geometry of this partition

        Args:
            constraint (Constraint): The constraint to use

        Raises:
            exceptions.InvalidPartitionError: If the partition is not valid for this operation

        Note:
            This is a wrapper around the ``ped_partition_maximize`` function
        """
        if not self.is_valid:
            raise exceptions.InvalidPartitionError('Could not operate on this partition type')

        self.disk.maximize_partition_geometry(self, constraint)

    def __str__(self) -> str:
        return 'Partition(num={}, type={}, fs_type={}, path={}, flags={}, name={}, geometry={})'.format(
            self.num, self.type, self.fs_type, self.path, self.flags, self.name, self.geometry
        )

    def __repr__(self) -> str:
        return self.__str__()


class DiskType:
    """Represents a disk type"""

    class Feature(enum.Flag):
        """Represents a disk type feature"""

        NONE = 0  # No features
        EXTENDED = 1  # supports extended partitions
        NAME = 2  # supports partition names
        ID = 4  # supports partition type-ids
        UUID = 8  # supports partition type-uuids

        @staticmethod
        def from_string(feature: str) -> 'DiskType.Feature':
            """Returns the feature from a string

            Args:
                feature (str): The feature to get

            Returns:
                DiskType.Feature: The feature

            Raises:
                ValueError: If the feature is not found
            """
            return DiskType.Feature[feature.upper()]

        def __str__(self) -> str:
            return 'DiskType.Feature.{}'.format(self.name)

        def __repr__(self) -> str:
            return self.__str__()

    class WNT(enum.Enum):
        """Represents Well Known Type names"""

        AIX = 'aix'
        AMIGA = 'amiga'
        BSD = 'bsd'
        DASD = 'dasd'
        DM = 'dm'
        GPT = 'gpt'
        LOOP = 'loop'
        MAC = 'mac'
        MSDOS = 'msdos'
        PC98 = 'pc98'
        SUN = 'sun'
        UNKNOWN = 'unknown'

        @staticmethod
        def from_string(wnt: str) -> 'DiskType.WNT':
            """Returns the WNT from a string

            Args:
                wnt (str): The WNT to get

            Returns:
                DiskType.WNT: The WNT

            Raises:
                ValueError: If the WNT is not found
            """
            return DiskType.WNT[wnt.upper()]

        def __eq__(self, __o: object) -> bool:
            if isinstance(__o, str):
                return self.value == __o
            return super().__eq__(__o)

        def __str__(self) -> str:
            return 'DiskType.KnownType.{}'.format(self.name)

        def __repr__(self) -> str:
            return self.__str__()

    _disktype: typing.Any

    def __init__(self, disktype: typing.Union[str, 'DiskType.WNT', 'cffi.FFI.CData', None] = None) -> None:
        """Initializes a new disk type

        Args:
            disktype (typing.Union[str, parted.disk.DiskType.WNT, cffi.FFI.CData]): The disk type to use

        Note:
            This is a wrapper around the ``ped_disk_type_get`` function for for the str and parted.disk.DiskType.WNT types
        """

        if isinstance(disktype, str):
            disktype = _parted.lib.ped_disk_type_get(disktype.encode())
        elif isinstance(disktype, DiskType.WNT):
            disktype = _parted.lib.ped_disk_type_get(disktype.value.encode())
        self._disktype = disktype if disktype else _parted.ffi.NULL

    def __bool__(self):
        return bool(self._disktype)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, DiskType):
            return self._disktype == other._disktype
        elif isinstance(other, str):
            return self.name == other
        elif isinstance(other, DiskType.WNT):
            return self.name == other.value
        return False

    @property
    def obj(self) -> 'cffi.FFI.CData':
        """Wrapped ``PedDiskType*`` object"""
        return self._disktype

    @property
    def name(self) -> str:
        """The name of the disk type"""
        if not self._disktype:
            return ''
        return _parted.ffi.string(self._disktype.name).decode()

    @property
    def features(self) -> Feature:
        """The features of the disk type"""
        if not self._disktype:
            return DiskType.Feature(0)
        return DiskType.Feature(self._disktype.features)

    @ensure_obj
    def next_type(self) -> 'DiskType':
        """Next disk type in the parted list

        This is mean to be used for enumerating all disk types

        Returns:
            DiskType: The next disk type
        """
        return DiskType(_parted.lib.ped_disk_type_get_next(self._disktype))

    @staticmethod
    def enumerate() -> typing.Iterable['DiskType']:
        """Enumerates all disk types

        Yields:
            DiskType: An iterable of all disk types

        """
        current = DiskType.first_type()
        while True:
            yield current
            current = current.next_type()
            if not current:
                break

    @staticmethod
    def first_type() -> 'DiskType':
        """First disk type in the parted list

        Returns:
            DiskType: The first disk type

        Note:
            This is a wrapper around the ``ped_disk_type_get_next`` function with a NULL argument
        """
        return DiskType(_parted.lib.ped_disk_type_get_next(_parted.ffi.NULL))

    @staticmethod
    def from_name(name: typing.Union[WNT, str]) -> 'DiskType':
        """
        Returns the disk type with the given name

        Args:
            name (str): disk type name (e.g. 'gpt', 'msdos', 'bsd', ...)

        Returns:
            DiskType: disk type structure for the given name
        """
        n: str = name.value if isinstance(name, DiskType.WNT) else name
        return DiskType(_parted.lib.ped_disk_type_get(n.encode()))

    def __str__(self):
        return 'DiskType(name={}, features={})'.format(self.name, self.features)

    def __repr__(self):
        return self.__str__()


class DiskFlag(enum.IntEnum):
    # This flag (which defaults to true) controls if disk types for
    #    which cylinder alignment is optional do cylinder alignment when a
    #    new partition gets added.
    #    This flag is available for msdos and sun disklabels (for sun labels
    #    it only controls the aligning of the end of the partition)
    CYLINDER_ALIGNMENT = 1
    # This flag controls whether the boot flag of a GPT PMBR is set
    GPT_PMBR_BOOT = 2

    @staticmethod
    def from_string(flag: str) -> 'DiskFlag':
        """Returns the DiskFlag from a string

        Args:
            flag (str): The flag to get

        Returns:
            DiskFlag: The flag

        Raises:
            ValueError: If the flag is not found
        """
        return DiskFlag[flag.upper()]

    def __str__(self) -> str:
        return 'DiskFlag.{}'.format(self.name)

    def __repr__(self) -> str:
        return self.__str__()


class Disk:
    """Represents a disk

    A disk is a collection of partitions.
    """

    # The partition list contains also emtpy partitions and metadata "partitions"
    _disk: typing.Any  # PedDisk*, can be NULL
    _destroyable: bool

    # Public methods
    def __init__(
        self,
        disk: typing.Optional[typing.Union['device.Device', 'cffi.FFI.CData']] = None,
    ) -> None:
        """Initializes a new disk

        Args:
            disk (typing.Optional[typing.Union[device.Device, cffi.FFI.CData]], optional): The disk to use. Defaults to None.
                if None, a NULL disk is created
                if a device.Device, a new disk is created for the device
                if a cffi.FFI.CData, the PedDisk* is wrapped

        Note:
            This is a wrapper around the ``ped_disk_new`` function for the device.Device argument type
        """
        if isinstance(disk, device.Device) and disk:
            self._disk = _parted.lib.ped_disk_new(disk.obj)
            self._destroyable = True
        else:
            self._disk = disk if disk else _parted.ffi.NULL
            self._destroyable = False

    def __del__(self) -> None:
        """Destroy the disk object

        Note:
            From the parted documentation:
        What this function does depends on the PedDiskType of disk, but you can generally assume that outstanding writes are flushed
        """
        if self._disk and self._destroyable:
            _parted.lib.ped_disk_destroy(self._disk)

    def __bool__(self) -> bool:
        return bool(self._disk)

    def __getitem__(self, num: int) -> 'Partition':
        return list(self.partitions_list('all'))[num]

    def __len__(self) -> int:
        return len(list(self.partitions_list('all')))

    def __eq__(self, other: typing.Any) -> bool:
        if isinstance(other, Disk):
            return str(self) == str(other)  # May be different locations, but same content
        return False

    @property
    def obj(self) -> 'cffi.FFI.CData':
        """Wrapped ``PedDisk*`` object"""
        return self._disk

    @property  # type: ignore  # mypy doesn't like the property decorator
    @ensure_obj_or_default(lambda: device.Device())
    def dev(self) -> 'device.Device':
        """The device of the disk"""
        return device.Device(self._disk.dev)

    @property  # type: ignore  # mypy doesn't like the property decorator
    @ensure_obj_or_default(lambda: DiskType())
    def type(self) -> DiskType:
        """The type of the disk"""
        return DiskType(self._disk.type)

    @property
    def partitions(self) -> typing.List[Partition]:
        """ALL partitions of the disk (valid an "virtual")"""
        return list(self.partitions_list('all'))

    @property
    def active_partitions(self) -> typing.List[Partition]:
        """ACTIVE partitions of the disk"""
        return list(self.partitions_list('active'))

    @property
    def free_partitions(self) -> typing.List[Partition]:
        """FREE partitions of the disk"""
        return list(self.partitions_list('free'))

    @property  # type: ignore  # mypy doesn't like the property decorator
    @ensure_obj_or_default(0)
    def last_partition_num(self) -> int:
        """The number of the last partition"""
        return _parted.lib.ped_disk_get_last_partition_num(self._disk)

    @property  # type: ignore  # mypy doesn't like the property decorator
    @ensure_obj_or_default(0)
    def max_primary_partition_count(self) -> int:
        """The maximum number of primary partitions"""
        return _parted.lib.ped_disk_get_max_primary_partition_count(self._disk)

    @property  # type: ignore  # mypy doesn't like the property decorator
    @ensure_obj_or_default(lambda: set())
    def flags(self) -> typing.Set[DiskFlag]:
        """The flags of the disk"""
        return {x for x in DiskFlag if self.get_flag(x)}

    @ensure_obj
    def get_partition(self, num: int) -> Partition:
        """Returns the partition with the given number

        Args:
            num (int): partition number

        Returns:
            Partition: partition with the given number

        Note:
            This is a wrapper around the ``ped_disk_get_partition`` function
        """
        return Partition(_parted.lib.ped_disk_get_partition(self._disk, num))

    @ensure_obj
    def get_extended_partition(self) -> Partition:
        """Returns the extended partition

        Returns:
            Partition: extended partition

        Raises:
            exceptions.InvalidPartitionError: if no extended partition exists

        Note:
            This is a wrapper around the ``ped_disk_extended_partition`` function
        """
        if DiskType.Feature.EXTENDED in self.type.features:
            return Partition(_parted.lib.ped_disk_extended_partition(self._disk))
        raise exceptions.InvalidPartitionError('No extended partition')

    @ensure_obj
    def get_partition_by_sector(self, sector: int) -> Partition:
        """Returns the partition containing the given sector

        Args:
            sector (int): sector

        Returns:
            Partition: partition containing the given sector
        """
        return Partition(_parted.lib.ped_disk_get_partition_by_sector(self._disk, sector))

    @ensure_obj
    def get_max_partition_geometry(
        self, partition: 'Partition', constraint: 'constraint.Constraint'
    ) -> 'geom.Geometry':
        """Returns the maximum geometry for the given partition

        Args:
            partition (Partition): partition
            constraint (constraint.Constraint): constraint

        Returns:
            geom.Geometry: maximum geometry for the given partition

        Note:
            This is a wrapper around the ``ped_disk_get_max_partition_geometry`` function
        """
        return make_destroyable(
            geom.Geometry(_parted.lib.ped_disk_get_max_partition_geometry(self._disk, partition.obj, constraint.obj))
        )

    @ensure_obj
    def set_partition_geometry(
        self, partition: 'Partition', const: 'constraint.Constraint', sector_start: int, sector_end: int
    ) -> None:
        """
        Sets a new geometry for a partition.

        Args:
            partition (Partition): partition to set the geometry for
            geom (geom.Geometry): new geometry
            constraint (constraint.Constraint): constraint to use

        Raises:
            exceptions.PartedException: if the operation failed
        """
        if not partition:  # pragma: no cover
            raise exceptions.PartedException('Invalid partition')
        if partition.disk != self:  # pragma: no cover
            raise exceptions.PartedException('Partition does not belong to this disk')
        if not const:  # pragma: no cover
            raise exceptions.PartedException('Invalid constraint')
        if (
            sector_start < 0
            or sector_end < 0
            or sector_end > self.dev.length
            or sector_start > self.dev.length
            or sector_start > sector_end
        ):
            raise exceptions.PartedException('Invalid sector range')
        if _parted.lib.ped_disk_set_partition_geom(self._disk, partition.obj, const.obj, sector_start, sector_end) == 0:
            raise exceptions.PartedException('Failed to set partition geometry')

    @ensure_obj
    def maximize_partition_geometry(self, partition: 'Partition', constraint: 'constraint.Constraint') -> None:
        """Maximizes the geometry of the given partition

        Args:
            partition (Partition): partition to maximize
            constraint (constraint.Constraint): constraint to use

        Raises:
            exceptions.PartedException: if the operation failed
        """
        if _parted.lib.ped_disk_maximize_partition(self._disk, partition.obj, constraint.obj) == 0:
            raise exceptions.PartedException('Failed to maximize partition')

    @ensure_obj
    def minimize_extended_partition(self) -> None:
        """Minimizes the extended partition

        Raises:
            exceptions.InvalidPartitionError: if no extended partition exists
            exceptions.PartedException: if the operation failed
        """
        if DiskType.Feature.EXTENDED not in self.type.features:
            raise exceptions.InvalidPartitionError('No extended partition')
        if _parted.lib.ped_disk_minimize_extended_partition(self._disk) == 0:
            raise exceptions.PartedException('Failed to minimize extended partition')

    @ensure_obj
    def set_flag(self, flag: DiskFlag, state: bool) -> None:
        """Sets the given flag to the given state

        Args:
            flag (DiskFlag): flag to set
            state (bool): state to set the flag to

        Raises:
            exceptions.PartedException: if the operation failed

        Note:
            This is a wrapper around the ``ped_disk_set_flag`` function. Unsupported flags will be ignored.
        """
        if self.is_flag_available(flag):
            if _parted.lib.ped_disk_set_flag(self._disk, flag.value, state) == 0:
                raise exceptions.PartedException('Invalid flag')
        # If not supported, just ignore it

    @ensure_obj
    def get_flag(self, flag: DiskFlag) -> bool:
        """Returns the state of the given flag

        Args:
            flag (DiskFlag): flag to get the state of

        Returns:
            bool: state of the given flag
        """
        if self.is_flag_available(flag):
            return _parted.lib.ped_disk_get_flag(self._disk, flag.value) != 0
        return False

    @ensure_obj
    def is_flag_available(self, flag: DiskFlag) -> bool:
        """Returns whether the given flag is available

        Args:
            flag (DiskFlag): flag to check

        Returns:
            bool: whether the given flag is available
        """
        return _parted.lib.ped_disk_is_flag_available(self._disk, flag.value) != 0

    def partitions_list(self, type: typing.Literal['all', 'active', 'free']) -> typing.Iterable[Partition]:
        """Gets the list of filtered partitions

        Args:
            type (str): type of partitions to get

        Yields:
            Partition: partition with the given type

        Note: This is a wrapper around the ``ped_disk_next_partition`` function. if Disk is not initialized, it will
            yield nothing.
        """
        if not self._disk:
            return

        # Clear old partitions cache
        part = _parted.lib.ped_disk_next_partition(self._disk, _parted.ffi.NULL)
        while part:
            p = Partition(part)
            if type == 'all':
                yield p
            elif type == 'active':
                if p.is_valid:
                    yield p
            elif type == 'free':
                if p.type == PartitionType.FREE:
                    yield p
            else:
                raise Exception('Invalid type')
            part = _parted.lib.ped_disk_next_partition(self._disk, part)

    @ensure_obj
    def check(
        self,
    ) -> bool:
        """Checks the disk for consistency and returns True if it is consistent.

        Returns:
            bool: whether the disk is consistent

        Note:
            This is a wrapper around the ``ped_disk_check`` function
        """
        return bool(_parted.lib.ped_disk_check(self._disk))

    @ensure_obj
    def duplicate(self) -> 'Disk':
        """Duplicates the disk

        Returns:
            Disk: duplicated disk
        """
        return make_destroyable(Disk(_parted.lib.ped_disk_duplicate(self._disk)))

    @ensure_obj
    def delete_partition(self, partition: 'Partition') -> None:
        """Removes the specified partition from the disk, and destroys it.

        The reference to the partition is no longer valid after this call

        Args:
            partition (Partition): partition to remove

        Raises:
            exceptions.InvalidPartitionError: if the partition is invalid
            exceptions.PartedException: if the operation failed
        """
        if not partition.is_valid:
            raise exceptions.InvalidPartitionError('Invalid partition: {}'.format(partition))

        if _parted.lib.ped_disk_delete_partition(self._disk, partition.obj) == 0:
            raise exceptions.PartedException('Failed to remove partition')
        else:
            partition._partition = _parted.ffi.NULL
            partition._destroyable = False

    @ensure_obj
    def delete_all_partitions(self) -> None:
        """Removes all partitions from the disk.

        Raises:
            exceptions.PartedException: if the operation failed

        Note:
            This is a wrapper around the ``ped_disk_delete_all`` function
        """
        if _parted.lib.ped_disk_delete_all(self._disk) == 0:
            raise exceptions.PartedException('Failed to remove all partitions')

    @ensure_obj
    def new_partition(
        self,
        part_type: PartitionType,
        fs_type: typing.Union[str, 'filesys.FileSystemType', 'filesys.FileSystemType.WNT'],
        start: int,
        end: int,
    ) -> 'Partition':
        """Creates a new partition

        Args:
            disk (Disk): The disk to use
            part_type (PartitionType): The type of the partition
            fs_type (str or FileSystemType): The file system type
            start (int): The start sector
            end (int): The end sector

        Returns:
            Partition: The new partition

        Raises:
            exceptions.InvalidDiskError if the disk is not valid for this operation
            exceptions.InvalidFileSystemType if the file system type is not valid

        Important:
            The created partition is not added to the disk. You have to call the ``add_to_disk`` method of the partition or
            the ``add_partition`` method of the disk to add it to the disk.

        Note:
            This is a wrapper around the ``ped_partition_new`` function
        """
        if isinstance(fs_type, (str, filesys.FileSystemType.WNT)):
            fs_type = filesys.FileSystemType(fs_type)

        part = make_destroyable(
            Partition(_parted.lib.ped_partition_new(self._disk, part_type.value, fs_type._filesystemtype, start, end))
        )

        # Ensures it gets destroyed when deleted
        return part

    @ensure_obj
    def add_partition(
        self,
        partition: 'Partition',
        constr: typing.Optional['constraint.Constraint'] = None,
    ) -> None:
        """Adds the given partition to the disk.

        Args:
            partition (Partition): partition to add
            constraint (constraint.Constraint): constraint to use

        Raises:
            exceptions.InvalidPartitionError: if the partition is invalid
            exceptions.PartedException: if the operation failed

        Note:
            This is a wrapper around the ``ped_disk_add_partition`` function
        """
        if not partition.is_valid:
            raise exceptions.InvalidPartitionError('Invalid partition: {}'.format(partition))

        if not constr:  # Create an EXACT constraint for this partition
            start_alignment = alignment.Alignment(partition.geometry.start, 0)
            end_alignment = alignment.Alignment(partition.geometry.end, 0)
            start_range = geom.Geometry(self.dev, partition.geometry.start, partition.geometry.start)
            end_range = geom.Geometry(self.dev, partition.geometry.end, partition.geometry.end)
            constr = constraint.Constraint.new(
                start_align=start_alignment,
                end_align=end_alignment,
                start_range=start_range,
                end_range=end_range,
                min_size_sector=partition.geometry.length,
                max_size_sector=partition.geometry.length,
            )

        if _parted.lib.ped_disk_add_partition(self._disk, partition._partition, constr._constraint) == 0:
            raise exceptions.PartedException('Failed to add partition')

        # Now partition is not destroyable anymore
        partition._destroyable = False

    @ensure_obj
    def create_partition(
        self,
        part_type: PartitionType,
        fs_type: typing.Union[str, 'filesys.FileSystemType', 'filesys.FileSystemType.WNT'],
        start: int,
        end: int,
        constraint: typing.Optional['constraint.Constraint'] = None,
    ) -> 'Partition':
        """Creates a new partition and adds it to the disk.

        Args:
            disk (Disk): The disk to use
            part_type (PartitionType): The type of the partition
            fs_type (str or FileSystemType): The file system type
            start (int): The start sector
            end (int): The end sector
            constraint (constraint.Constraint): constraint to use

        Returns:
            Partition: The new partition

        Raises:
            exceptions.InvalidDiskError if the disk is not valid for this operation
            exceptions.InvalidFileSystemType if the file system type is not valid
            exceptions.PartedException if the operation failed

        """
        part = self.new_partition(part_type, fs_type, start, end)
        self.add_partition(part, constraint)
        return part

    @ensure_obj
    def commit_to_dev(self) -> None:
        """
        Write the changes made to the in-memory description of a partition table to the device.
        As a protection, device must be opened in read-write mode to be able to commit changes.

        Warning: Ensure to invoke this method after you are made changes to the disk. The destruction of the disk object
            will write them on "most cases" as indicated by the parted documentation, but calling this method explicitly
            will ensure that the changes are written to the device.

        Returns:
            bool: whether the operation succeeded

        Note:
            This is a wrapper around the ``ped_disk_commit_to_dev`` function
        """
        self.dev.wants_access(for_writing=True)
        if _parted.lib.ped_disk_commit_to_dev(self._disk) == 0:
            raise exceptions.IOError('Failed to commit to device')

    @ensure_obj
    def commit_to_os(self) -> bool:
        """
        Tell the operating system kernel about the partition table layout of disk.

        This is rather loosely defined: for example, on old versions of Linux, it simply calls the BLKRRPART ioctl,
        which tells the kernel to reread the partition table. On newer versions (2.4.x), it will use the new blkpg
        interface to tell Linux where each partition starts/ends, etc. In this case, Linux does not need to have support
        for a specific type of partition table.

        Returns:
            bool: whether the operation succeeded

        Note:
            This is a wrapper around the ``ped_disk_commit_to_os`` function
        """
        return bool(_parted.lib.ped_disk_commit_to_os(self._disk))

    @ensure_obj
    def print(self) -> None:
        """Prints the partition table to stdout.

        Note:
            This is a wrapper around the ``ped_disk_print`` function
        """
        _parted.lib.ped_disk_print(self._disk)

    @ensure_obj
    def debug(self) -> str:
        """Prints the partition table to the given stream.

        Args:
            out_stream (typing.TextIO): stream to print to, defaults to stdout

        """
        out = ''
        # Disk information
        out += 'Disk: {}\n'.format(self.dev.path)
        out += 'Type: {}\n'.format(self.type)
        for i in self.partitions_list('all'):
            out += str(i) + '\n'
        return out

    def __str__(self) -> str:
        return 'Disk(path={}, type={}, last_p_n={}, flags={})'.format(
            self.dev.path, self.type, self.last_partition_num, self.flags
        )

    def __repr__(self) -> str:
        return self.__str__()
