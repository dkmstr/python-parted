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
import logging

from parted import _parted  # type: ignore
from parted import disk, filesys, device, geom, alignment, constraint, exceptions

from tests.util import partedtest, create_msdos_disk_image_ctx, create_gpt_disk_image_ctx

logger = logging.getLogger(__name__)


class TestPartedPartition(partedtest.PartedTestCase):
    def test_partition_null(self) -> None:
        for i in (None, _parted.ffi.NULL):
            part = disk.Partition(i)
            self.assertEqual(part.obj, _parted.ffi.NULL)
            self.assertEqual(part.disk, disk.Disk())
            self.assertEqual(part.num, -9999)
            self.assertEqual(part.type, disk.PartitionType.FREE)
            self.assertEqual(part.fs_type, filesys.FileSystemType())
            self.assertEqual(part.path, '')
            self.assertSetEqual(part.flags, set())
            self.assertEqual(part.name, '')
            # Set name, will do nothing
            part.name = 'test'
            self.assertEqual(part.name, '')
            self.assertFalse(part.busy)
            self.assertFalse(part.active)

            with self.assertRaises(exceptions.PartedException):
                part.set_geometry(constraint.Constraint.any(device.Device()), 1, 1024)

    def test_partition_not_null_msdos(self) -> None:
        with self.exception_context():
            with create_msdos_disk_image_ctx() as path:
                dev = device.Device.get(path)
                dsk = dev.read_table()
                part = dsk.get_partition(2)  # Partition 2 is ext4, primary, active
                self.assertNotEqual(part.obj, _parted.ffi.NULL)
                self.assertEqual(part.disk, dsk)
                self.assertEqual(part.num, 2)
                self.assertEqual(part.type, disk.PartitionType.NORMAL)
                self.assertEqual(part.fs_type, filesys.FileSystemType('ext4'))
                self.assertEqual(part.path, path + '2')
                self.assertEqual(part.geometry.start, 4096)
                self.assertEqual(part.geometry.end, 8191)
                self.assertEqual(part.geometry.length, 4096)
                self.assertEqual(part.geometry.dev, dev)
                self.assertSetEqual(part.flags, set())
                self.assertEqual(part.name, '')
                # sets name, will do nothing
                part.name = 'test'
                self.assertEqual(part.name, '')
                self.assertEqual(part.busy, False)
                self.assertEqual(part.active, True)
                self.assertEqual(part.extended_list, [])
                self.assertEqual(part.extended_list_active, [])
                self.assertEqual(part.extended_list_free, [])

                part.set_flag(disk.PartitionFlag.LBA, True)
                self.assertSetEqual(part.flags, {disk.PartitionFlag.LBA})
                part.set_flag(disk.PartitionFlag.BOOT, True)
                self.assertSetEqual(part.flags, {disk.PartitionFlag.LBA, disk.PartitionFlag.BOOT})
                part.set_flag(disk.PartitionFlag.LBA, False)
                self.assertSetEqual(part.flags, {disk.PartitionFlag.BOOT})
                part.set_flag(disk.PartitionFlag.BOOT, False)
                self.assertSetEqual(part.flags, set())

                part.set_geometry(constraint.Constraint.any(dev), 1, 1024)
                self.assertEqual(part.geometry.start, 2)
                self.assertEqual(part.geometry.end, 1019)

                part.maximize(constraint.Constraint.any(dev))
                self.assertEqual(part.geometry.start, 2)
                self.assertEqual(part.geometry.end, 2039)

                with self.assertRaises(exceptions.PartedException):
                    dsk.partitions[0].maximize(constraint.Constraint.any(dev))
                self.assertEqual(self.total_exceptions, 0)

    def test_partition_not_null_gpt(self) -> None:
        with self.exception_context():
            with create_gpt_disk_image_ctx() as path:
                dev = device.Device.get(path)
                dsk = dev.read_table()
                logger.info('Disk: %s', dsk)
                part = dsk.get_partition(2)  # Partition 2 is ext4, primary, active
                self.assertNotEqual(part.obj, _parted.ffi.NULL)
                self.assertEqual(part.disk, dsk)
                self.assertEqual(part.num, 2)
                self.assertEqual(part.type, disk.PartitionType.NORMAL)
                self.assertEqual(part.fs_type, filesys.FileSystemType('ext4'))
                self.assertEqual(part.path, path + '2')
                self.assertEqual(part.geometry.start, 8192)
                self.assertEqual(part.geometry.end, 14335)
                self.assertEqual(part.geometry.length, 6144)
                self.assertEqual(part.geometry.dev, dev)
                self.assertSetEqual(part.flags, set())
                self.assertEqual(part.name, '')
                # sets name, will do it
                part.name = 'test'
                self.assertEqual(part.name, 'test')
                self.assertEqual(part.busy, False)
                self.assertEqual(part.active, True)
                self.assertEqual(part.extended_list, [])
                self.assertEqual(part.extended_list_active, [])
                self.assertEqual(part.extended_list_free, [])

                part.set_flag(disk.PartitionFlag.HIDDEN, True)
                self.assertSetEqual(part.flags, {disk.PartitionFlag.HIDDEN})
                part.set_flag(
                    disk.PartitionFlag.BOOT, True
                )  # also sets ESP (EFI System Partition) flag, because it's a bootable partition on GPT
                self.assertSetEqual(
                    part.flags, {disk.PartitionFlag.HIDDEN, disk.PartitionFlag.BOOT, disk.PartitionFlag.ESP}
                )
                self.assertIn(disk.PartitionFlag.HIDDEN, part.flags)
                self.assertIn(disk.PartitionFlag.BOOT, part.flags)

                part.set_flag(disk.PartitionFlag.HIDDEN, False)
                self.assertIn(disk.PartitionFlag.BOOT, part.flags)
                part.set_flag(disk.PartitionFlag.BOOT, False)
                self.assertSetEqual(part.flags, set())

                dev.open()
                part.set_geometry(constraint.Constraint.any(dev), 1, 1024)
                # GPT Partition table is:
                # LBA 0: Protective MBR
                # LBA 1: GPT Header
                # LBA 2-33: GPT Partition Entries
                #   * every entry is 128 bytes, contains 32 bytes of GUID, 16 bytes of name, 8 bytes of flags, 72 bytes of padding
                # So, firts partition starts at LBA 34
                # ...
                # LBA -33: GPT Partition Entries
                # LBA -32 to -2: GPT Header
                # LBA -1: Secondary GPT Header

                self.assertEqual(part.geometry.start, 34)
                self.assertEqual(part.geometry.end, 1024)

                part.maximize(constraint.Constraint.any(dev))
                self.assertEqual(part.geometry.start, 34)
                self.assertEqual(part.geometry.end, 2047)

                with self.assertRaises(exceptions.PartedException):
                    dsk.partitions[0].maximize(constraint.Constraint.any(dev))
                self.assertEqual(self.total_exceptions, 0)

    def test_partition_flags(self) -> None:
        for i in disk.PartitionFlag:
            self.assertIsInstance(i, disk.PartitionFlag)
            self.assertIsInstance(str(i), str)
            self.assertIsInstance(repr(i), str)
            self.assertEqual(repr(i), str(i))

    def test_partition_type(self) -> None:
        for i in disk.PartitionType:
            self.assertIsInstance(i, disk.PartitionType)
            self.assertIsInstance(str(i), str)
            self.assertIsInstance(repr(i), str)
            self.assertEqual(repr(i), str(i))

    def test_new_destroy(self) -> None:
        with self.exception_context():
            with create_msdos_disk_image_ctx() as path:
                with self.override_init_del_add_counter(disk.Partition):
                    dev = device.Device.get(path)
                    dsk = dev.read_table()
                    CHECKS = 100
                    for i in range(100):  # A few tests to ensure no leaks
                        part = dsk.new_partition(disk.PartitionType.NORMAL, 'ext4', 0, 100)
                        self.assertIsInstance(part, disk.Partition)
                        self.assertNotEqual(part, 1)
                        self.assertEqual(part.type, disk.PartitionType.NORMAL)
                        self.assertEqual(part.geometry.start, 0)
                        self.assertEqual(part.geometry.end, 100)
                        self.assertEqual(part.geometry.length, 101)
                        self.assertEqual(self.get_counter(disk.Partition), 1)
                        del part
                        self.assertEqual(self.get_counter(disk.Partition), 0)
                        self.assertEqual(self.total_exceptions, 0)

                    lst: list[disk.Partition] = []
                    for i in range(100):
                        lst.append(dsk.new_partition(disk.PartitionType.NORMAL, 'ext4', 0, 100))

                    self.assertEqual(self.get_counter(disk.Partition), 100)
                    del lst
                    self.assertEqual(self.get_counter(disk.Partition), 0)

    def test_partition_changes_written(self) -> None:
        with self.exception_context():
            with create_msdos_disk_image_ctx() as path:
                dev = device.Device.get(path)
                dsk = dev.read_table()
                # Get data from device, to ensure not changes are written to disk
                with dev.open():
                    orig_data = dev.read(0, 1)  # Read first sector

                    part = dsk.get_partition(1)
                    part.delete()

                    self.assertEqual(self.total_exceptions, 0)

                    # Check that no changes were written to disk
                    not_modified = dev.read(0, 1)
                    self.assertEqual(orig_data, not_modified)

                    # Write changes to disk
                    dsk.commit_to_dev()

                    self.assertEqual(self.total_exceptions, 0)

                    # Check that changes were written to disk
                    modified = dev.read(0, 1)
                    self.assertNotEqual(orig_data, modified)

                    partitions = dsk.partitions[:]

                    # Create a new partition
                    part = dsk.new_partition(disk.PartitionType.NORMAL, 'ext4', 0, 100)
                    const = constraint.Constraint.new(
                        alignment.Alignment(0, dev.hw_geom.sectors),
                        alignment.Alignment(0, dev.hw_geom.sectors),
                        geom.Geometry(dev, 0, 100),
                        geom.Geometry(dev, 0, 100 + dev.hw_geom.sectors*2),
                        100,
                        256,
                    )

                    # Changes should not have been written to disk
                    not_modified = dev.read(0, 1)
                    self.assertEqual(modified, not_modified)

                    # Write changes to disk
                    dsk.commit_to_dev()

                    # Not added to disk yet, no changes
                    not_modified = dev.read(0, 1)
                    self.assertEqual(modified, not_modified)

                    modified_partitions = dsk.partitions[:]
                    # Not added to diskm no changes
                    self.assertEqual(partitions, modified_partitions)

                    # Add partition to disk
                    part.add_to_disk(const)

                    # Partition list has changed
                    modified_partitions = dsk.partitions[:]
                    self.assertNotEqual(partitions, modified_partitions)

                    # Disk has not been written to
                    not_modified = dev.read(0, 1)
                    self.assertEqual(modified, not_modified)

                    # Write changes to disk
                    dsk.commit_to_dev()

                    # Check that changes were written to disk
                    modified = dev.read(0, 1)
                    self.assertNotEqual(modified, not_modified)

                    self.assertEqual(self.total_exceptions, 0)

    def test_partition_str_repr(self) -> None:
        with self.exception_context():
            with create_msdos_disk_image_ctx() as path:
                dev = device.Device.get(path)
                dsk = dev.read_table()
                part = dsk.get_partition(1)
                self.assertIsInstance(str(part), str)
                self.assertEqual(repr(part), str(part))
