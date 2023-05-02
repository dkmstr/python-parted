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
This module contains Filesystem related classes and functions

:author: Adolfo Gómez, dkmaster at dkmon dot com
"""

from os import stat
import typing
import enum
import logging

from parted.exceptions import PartedException

from . import _parted  # type: ignore
from . import geom

from .util import make_destroyable

if typing.TYPE_CHECKING:
    import cffi
    from . import timer

logger = logging.getLogger(__name__)


class FileSystemType:
    """This class represents a FileSystem
    """

    _filesystemtype: typing.Any = None

    # Well know filesystems, some of them, all supported by parted
    class WNT(enum.Enum):
        """Well known filesystems identifiers in parted
        
        This class contains the well known filesystems identifiers in parted.
        """
        zfs = 'zfs'
        udf = 'udf'
        btrfs = 'btrfs'
        nilfs2 = 'nilfs2'
        ext2 = 'ext2'
        ext3 = 'ext3'
        ext4 = 'ext4'
        fat16 = 'fat16'
        fat32 = 'fat32'
        hfs = 'hfs'
        hfsplus = 'hfs+'
        hfsx = 'hfsx'
        jfs = 'jfs'
        swsusp = 'swsusp'
        linux_swap = 'linux-swap'
        linux_swap_v0 = 'linux-swap(v0)'
        linux_swap_v1 = 'linux-swap(v1)'
        ntfs = 'ntfs'
        reiserfs = 'reiserfs'
        freebsd_ufs = 'freebsd-ufs'
        hp_ufs = 'hp-ufs'
        sun_ufs = 'sun-ufs'
        xfs = 'xfs'
        apfs1 = 'apfs1'
        apfs2 = 'apfs2'
        asfs = 'asfs'
        amufs0 = 'amufs0'
        amufs1 = 'amufs1'
        amufs2 = 'amufs2'
        amufs3 = 'amufs3'
        amufs4 = 'amufs4'
        amufs5 = 'amufs5'
        affs0 = 'affs0'
        affs1 = 'affs1'
        affs2 = 'affs2'
        affs3 = 'affs3'
        affs4 = 'affs4'
        affs5 = 'affs5'
        affs6 = 'affs6'

        @staticmethod
        def from_string(name: str) -> 'FileSystemType.WNT':
            """Returns a well known filesystem type from its name

            Args:
                name (str): Name of the filesystem type

            Returns:
                FileSystemType.WNT: The filesystem type

            Raises:
                ValueError: If the filesystem type is not known

            """
            return FileSystemType.WNT.__members__[name]

        def __str__(self):
            return self.value

    def __init__(self, filesystemtype: typing.Union[WNT, str, 'cffi.FFI.CData', None] = None) -> None:
        """Creates a new FileSystemType object

        Args:
            filesystemtype (typing.Union[WNF, str, cffi.FFI.CData], optional): The filesystem type to create. Defaults to None.
            If None, a "nil" filesystem type is created, which is not valid, but can be used to iterate over all filesystem types
            or to compare with other filesystem types.
        """
        if isinstance(filesystemtype, (str, FileSystemType.WNT)):
            fst = str(filesystemtype)
            self._filesystemtype = _parted.lib.ped_file_system_type_get(fst.encode())
        else:
            self._filesystemtype = filesystemtype if filesystemtype else _parted.ffi.NULL

    def __bool__(self) -> bool:
        return bool(self._filesystemtype)

    def __eq__(self, other: typing.Any) -> bool:
        """Compares against another FileSystemType, string or WNF

        Args:
            other (typing.Any): The other object to compare against

        Returns:
            bool: True if both are related to same Filesystem, False otherwise
        """
        if isinstance(other, FileSystemType):
            return self._filesystemtype == other._filesystemtype
        elif isinstance(other, FileSystemType.WNT):
            return self.name == other.value
        elif isinstance(other, str):
            return self.name == other
        else:
            return False

    @property
    def obj(self) -> 'cffi.FFI.CData':
        """Wrapped ``PedFileSystemType*`` object"""
        return self._filesystemtype

    @property
    def name(self) -> str:
        """Name of the filesystem (i.e. ext4, fat32, etc)"""
        if not self._filesystemtype:
            return ''
        return _parted.ffi.string(self._filesystemtype.name).decode()

    def next(self) -> 'FileSystemType':
        """Returns the next filesystem type

        Returns:
            FileSystemType: The next filesystem type
        """
        fs = self._filesystemtype if self._filesystemtype else _parted.ffi.NULL
        return FileSystemType(_parted.lib.ped_file_system_type_get_next(fs))

    @staticmethod
    def enumerate() -> typing.Iterator['FileSystemType']:
        """Enumerates all filesystem types

        Yields:
            FileSystemType: Available valid filesystem types
        """
        fs = _parted.ffi.NULL
        while True:
            fs = _parted.lib.ped_file_system_type_get_next(fs)
            if not fs:
                break
            yield FileSystemType(fs)

    @staticmethod
    def from_string(name: str) -> 'FileSystemType':
        """Returns a filesystem type from its name
            
            Args:
                name (str): Name of the filesystem type
    
            Returns:
                FileSystemType: The filesystem type
            """
        return FileSystemType(name)

    @staticmethod
    def none() -> 'FileSystemType':
        """Returns the "nil" filesystem type

        Returns:
            FileSystemType: The "nil" filesystem type
        """
        return FileSystemType()

    def __str__(self) -> str:
        return self.name


class FileSystem:
    """This class represents a FileSystem"""

    _filesystem: typing.Any

    def __init__(self, filesystem: typing.Optional['cffi.FFI.CData'] = None):
        """Creates a new FileSystem object

        Args:
            filesystem (cffi.FFI.CData, optional): The filesystem to create. Defaults to None.
            If None, a "nil" filesystem is created, which is not valid, but can be used to iterate over all filesystems
            or to compare with other filesystems.
        """
        self._filesystem = filesystem if filesystem else _parted.ffi.NULL

    def __bool__(self) -> bool:
        return bool(self._filesystem)

    @property
    def obj(self) -> 'cffi.FFI.CData':
        """Wrapped ``PedFileSystem*`` object"""
        return self._filesystem

    @property
    def geometry(self) -> 'geom.Geometry':
        """Geometry of the filesystem"""
        return geom.Geometry(self._filesystem.geom)

    @property
    def type(self) -> 'FileSystemType':
        """Type of the filesystem"""
        return FileSystemType(self._filesystem.type)

    @property
    def checked(self) -> bool:
        """Whether the filesystem has been checked"""
        return bool(self._filesystem.checked)

    @staticmethod
    def probe(gometry: 'geom.Geometry') -> 'FileSystemType':
        """Probes the file system on the given geometry.
        
        Args:
            geometry (geom.Geometry): The geometry to probe

        Returns:
            FileSystemType: The filesystem type. If no filesystem is found, returns "nil" FileSystemType
        """
        if not gometry:
            raise PartedException('Invalid geometry')
        return FileSystemType(_parted.lib.ped_file_system_probe(gometry.obj))

    @staticmethod
    def probe_specific(
        gometry: 'geom.Geometry', fstype: typing.Union['FileSystemType.WNT', 'FileSystemType']
    ) -> 'geom.Geometry':
        """Probes the file system on the given geometry.

        Args:
            geometry (geom.Geometry): The geometry to probe
            fstype (typing.Union[FileSystemType.WNT, FileSystemType]): The filesystem type to probe

        Returns:
            geom.Geometry: The geometry of the filesystem. If no filesystem is found, returns "nil" Geometry
        """
        if isinstance(fstype, FileSystemType.WNT):
            fstype = FileSystemType(fstype)

        return make_destroyable(geom.Geometry(_parted.lib.ped_file_system_probe_specific(fstype.obj, gometry.obj)))
