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
                
