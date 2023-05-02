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
import logging

from parted import _parted  # type: ignore
from parted import filesys, exceptions, device, geom

from tests.util import partedtest, create_msdos_disk_image_ctx

logger = logging.getLogger(__name__)


class TestPartedFilesys(partedtest.PartedTestCase):
    def test_null_works(self) -> None:
        for i in (None, _parted.ffi.NULL):
            const = filesys.FileSystem(i)
            self.assertEqual(const.obj, _parted.ffi.NULL)

    def test_well_known_filesystem_types(self) -> None:
        for i in filesys.FileSystemType.WNT:
            const = filesys.FileSystemType(i)
            logger.info('Checking %s (%s)', i, const)
            self.assertNotEqual(const.obj, _parted.ffi.NULL, 'FileSystemType for %s is NULL' % (i,))

    def test_enumerate_filesystem_types(self) -> None:
        for i in filesys.FileSystemType.enumerate():
            logger.info('Found %s', i)
            self.assertNotEqual(i.obj, _parted.ffi.NULL, 'FileSystemType for %s is NULL' % (i,))

    def test_probe_filesystem(self) -> None:
        with self.exception_context():
            # Any partition will do the trick
            with create_msdos_disk_image_ctx() as path:
                # get partition number 2, ext4 type
                dev = device.Device(path)
                dsk = dev.read_table()
                for part_num, part_type in ((2, filesys.FileSystemType.WNT.ext4), (5, filesys.FileSystemType.WNT.ntfs)):
                    specific = filesys.FileSystemType(part_type)
                    part = dsk.get_partition(part_num)

                    self.assertEqual(part.fs_type, filesys.FileSystemType(part_type))

                    # Probe filesystem in partition 2
                    fs_type = filesys.FileSystem.probe(part.geometry)
                    self.assertEqual(fs_type, filesys.FileSystemType(part_type))

                    # Probe specific filesystem in partition 2, various ways
                    g = filesys.FileSystem.probe_specific(geom.Geometry.new(dev, 0, dev.length), specific)
                    self.assertEqual(g, geom.Geometry.new(dev, 0, 0), 'Geometry for %s is not the same' % (specific,))

                    g = filesys.FileSystem.probe_specific(part.geometry, part_type)
                    self.assertIn(g, part.geometry)  # Ensures that the geometry is inside the partition

                # With a non existing partition
                with self.assertRaises(exceptions.PartedException):
                    for i in range(dsk.last_partition_num+1, dsk.last_partition_num+128, 2):
                        filesys.FileSystem.probe(dsk.get_partition(i).geometry)
                        # This will not be reached, as the exception will be raised
                        # ensure that the loop is not infinite
                        raise Exception('Should not be reached')
                
