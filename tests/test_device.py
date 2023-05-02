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
from curses import nonl
import os

from parted import _parted, constraint  # type: ignore
from parted import device, exceptions, disk, geom, filesys

from tests.util import partedtest, create_empty_disk_image_ctx, create_gpt_disk_image_ctx


class TestPartedDevice(partedtest.PartedTestCase):
    def test_device_null(self) -> None:
        # Free all devices
        device.Device.free_all()
        for i in (None, _parted.ffi.NULL, ''):
            dev = device.Device(i)
            self.assertEqual(dev.obj, _parted.ffi.NULL)

        dev = device.Device()

        self.assertFalse(bool(dev))
        self.assertEqual(dev.obj, _parted.ffi.NULL)
        self.assertEqual(dev.model, 'Unknown')
        self.assertEqual(dev.path, '')
        self.assertEqual(dev.type, 0)
        self.assertEqual(dev.sector_size, 0)
        self.assertEqual(dev.phys_sector_size, 0)
        self.assertEqual(dev.length, 0)
        self.assertEqual(dev.size, 0)
        self.assertEqual(dev.open_count, 0)
        self.assertTrue(dev.read_only)
        self.assertFalse(dev.external_mode)
        self.assertFalse(dev.dirty)
        self.assertFalse(dev.boot_dirty)
        geom = dev.hw_geom
        self.assertEqual((geom.cylinders, geom.heads, geom.sectors), (0, 0, 0))
        geom = dev.bios_geom
        self.assertEqual((geom.cylinders, geom.heads, geom.sectors), (0, 0, 0))

        self.assertEqual(dev.host, 0)
        self.assertEqual(dev.did, 0)
        self.assertFalse(dev.is_busy)
        self.assertFalse(bool(dev.next()))

        self.assertRaises(exceptions.InvalidObjectError, dev.open)
        self.assertRaises(exceptions.InvalidObjectError, dev.close)
        self.assertRaises(exceptions.InvalidObjectError, dev.read, 0, 0)
        self.assertRaises(exceptions.InvalidObjectError, dev.write, 0, 0)
        self.assertRaises(exceptions.InvalidObjectError, dev.sync)
        self.assertRaises(exceptions.InvalidObjectError, dev.sync_fast)
        self.assertRaises(exceptions.InvalidObjectError, dev.begin_external_access, False)
        self.assertRaises(exceptions.InvalidObjectError, dev.end_external_access)

    def test_device_not_null(self) -> None:
        device.Device.free_all()
        with create_empty_disk_image_ctx(partedtest.PartedTestCase.MiB) as disk_path:
            dev = device.Device.get(disk_path)

            # Wil not raise any exception
            dev.open()

            self.assertTrue(bool(dev))
            self.assertNotEqual(dev.obj, _parted.ffi.NULL)
            self.assertNotEqual(dev.model, 'Unknown')
            self.assertNotEqual(dev.path, '')
            self.assertNotEqual(dev.type, 0)
            self.assertNotEqual(dev.sector_size, 0)
            self.assertNotEqual(dev.phys_sector_size, 0)
            self.assertNotEqual(dev.length, 0)
            self.assertNotEqual(dev.size, 0)
            self.assertEqual(dev.open_count, 1)
            self.assertFalse(dev.read_only)
            self.assertFalse(dev.external_mode)
            self.assertFalse(dev.dirty)
            self.assertFalse(dev.boot_dirty)
            geom = dev.hw_geom
            self.assertNotEqual((geom.cylinders, geom.heads, geom.sectors), (0, 0, 0))
            geom = dev.bios_geom
            self.assertNotEqual((geom.cylinders, geom.heads, geom.sectors), (0, 0, 0))

            self.assertIsInstance(dev.host, int)
            self.assertIsInstance(dev.did, int)

            self.assertFalse(dev.is_busy)

            dev.close()
            self.assertRaises(exceptions.NotOpenedError, dev.read, 0, 1)
            dev.open()
            dev.read(0, 1)
            dev.close()
            self.assertRaises(exceptions.NotOpenedError, dev.write, b'', 0, 1)
            dev.open()
            dev.write(b'', 0, 1)
            dev.close()

            self.assertFalse(bool(dev.next()))

    def test_device_file(self) -> None:
        with create_empty_disk_image_ctx(partedtest.PartedTestCase.MiB) as disk_path:
            dev = device.Device.get(disk_path)
            self.assertTrue(bool(dev))
            self.assertEqual(dev.path, disk_path)
            self.assertEqual(dev.type, device.DeviceType.FILE)
            self.assertEqual(dev.sector_size, 512)
            self.assertEqual(dev.phys_sector_size, 512)
            self.assertEqual(dev.length, 2048)
            self.assertEqual(dev.bios_geom.total_sectors, 2048)
            self.assertEqual(dev.hw_geom.total_sectors, 2048)
            self.assertEqual(dev.size, partedtest.PartedTestCase.MiB)

    def test_device_clean(self) -> None:
        with create_empty_disk_image_ctx() as file:
            dev = device.Device(file)
            dsk = disk.Disk(dev)

            self.assertEqual(dsk.partitions, [])  # No partitions

            # Disk not initialized, try to access a method that needs it will raise exceptions.InvalidObjectError
            self.assertRaises(exceptions.InvalidObjectError, dsk.get_partition, 1)
            self.assertRaises(exceptions.InvalidObjectError, dsk.commit_to_dev)
            self.assertRaises(exceptions.InvalidObjectError, dsk.commit_to_os)
            self.assertRaises(exceptions.InvalidObjectError, dsk.create_partition, None, None, None, None, None)

            # device not opened, and partition table is initialized, try to access a method that needs it will raise exceptions.NotOpenedError
            dsk = dev.new_table('msdos')
            self.assertRaises(exceptions.NotOpenedError, dsk.commit_to_dev)
            with dev.open():
                # device opened
                dev.clobber()
                dev.new_table('msdos')
            
                self.assertEqual(len(dsk.active_partitions), 0)  # No partitions
                self.assertEqual(len(dsk.free_partitions), 1)  # One free space
                self.assertEqual(dsk.type, 'msdos')  # Has msdos type


    def test_open_close_device(self) -> None:
        # Open /dev/null will fail, and will raise a "parted exception"
        # wo will do close() on it, and will raise a "parted exception"

        with self.exception_context():
            dev = device.Device.get('/dev/null')
            self.assertEqual(self.total_exceptions, 2)

            self.assertRaises(exceptions.PartedException, dev.open)
            self.assertRaises(exceptions.PartedException, dev.close)
            self.assertEqual(self.total_exceptions, 2)
            del dev

        with create_empty_disk_image_ctx() as disk_path:
            dev = device.Device.get(disk_path)
            self.assertTrue(bool(dev))
            dev.open()  # This should not raise
            self.assertEqual(dev.open_count, 1)
            dev.open()  # This should not raise, and should not increment open_count
            self.assertEqual(dev.open_count, 2)
            dev.close()  # This should not raise
            self.assertEqual(dev.open_count, 1)
            dev.close()  # This should not raise, but should not do anything
            self.assertEqual(dev.open_count, 0)

    def test_device_read_write(self) -> None:
        # Use an empty test disk of 32 MiB
        with create_empty_disk_image_ctx(partedtest.PartedTestCase.MiB * 32) as disk_path:
            dev = device.Device.get(disk_path)
            self.assertTrue(bool(dev))
            dev.open()
            self.assertEqual(dev.open_count, 1)
            # Reads 0 bytes from sector 0
            self.assertEqual(dev.read(0, 0), b'')

            sector_size = dev.sector_size
            # Reads 1 sector from sector 0, all zeros
            self.assertEqual(dev.read(0, 1), b'\x00' * sector_size)
            # Writes 1 sector from sector 0, all 0xFF
            dev.write(b'\xff' * sector_size, 0, 1)
            # Read back, should be all 0xFF
            self.assertEqual(dev.read(0, 1), b'\xff' * sector_size)

            # Now write all disk with i&0xFF
            for i in range(dev.length):
                buffer = bytes([i & 0xFF]) * sector_size
                dev.write(buffer, i, 1)

            # Read back and test it has same written data
            for i in range(dev.length):
                buffer = bytes([i & 0xFF]) * sector_size
                self.assertEqual(dev.read(i, 1), buffer)

            with self.exception_context():
                # Try to read 1 sector from sector -1, should NOT raise
                dev.read(-1, 1)
                # Try to read beyond the end of the disk, should raise
                self.assertRaises(exceptions.IOError, dev.read, dev.length, 1)
                # Try to read sectors beyond the end of the disk, should raise
                self.assertRaises(exceptions.IOError, dev.read, dev.length - 1, 2)

                # Try to write 1 sector from sector -1, should work
                dev.write(b'\x00' * sector_size, -1, 1)

            self.assertEqual(self.total_exceptions, 2)
            # Writing to a file beyond the end of the disk should extend the file
            # Note that "length" will not be updated until device is "reopened"
            dev.write(b'\x00' * sector_size, dev.length, 1)

            # Should work, device is opened
            dev.sync()
            dev.sync_fast()

            # Close device
            dev.close()

            # Should raise an exception
            self.assertRaises(exceptions.NotOpenedError, dev.sync)
            self.assertRaises(exceptions.NotOpenedError, dev.sync_fast)

            self.assertEqual(dev.open_count, 0)

            # Reopen device
            dev.open()

            self.assertEqual(dev.open_count, 1)

    def test_device_clobber(self) -> None:
        with create_empty_disk_image_ctx(partedtest.PartedTestCase.MiB * 32) as disk_path:
            dev = device.Device(disk_path)
            self.assertTrue(bool(dev))

            with dev.open():
                self.assertEqual(dev.open_count, 1)
                # Write 1 sector from sector 0, all 0xFF
                dev.write(b'\xff' * dev.sector_size, 0, 2)
                # Read back, should be all 0xFF
                self.assertEqual(dev.read(0, 1), b'\xff' * dev.sector_size)

                dev.clobber()

                # Read back, should be all 0x00
                self.assertEqual(dev.read(0, 1), b'\x00' * dev.sector_size)
            
            # Invoking clovver with a closed device should raise an exception
            self.assertRaises(exceptions.NotOpenedError, dev.clobber)
            # Also with a read-only opened device
            with dev.open('r'):
                self.assertRaises(exceptions.ReadOnlyError, dev.clobber)

    def test_device_table(self) -> None:
        with create_gpt_disk_image_ctx() as disk_path:
            dev = device.Device(disk_path)
            self.assertTrue(bool(dev))

            with dev.open():
                self.assertEqual(dev.open_count, 1)
                self.assertEqual(dev.probe(), disk.DiskType.WNT.GPT)

                # read the partition table data from disk
                data = dev.read(0, 33)

                # create a new partition table, but don't write it to disk
                dsk = dev.new_table(disk.DiskType.WNT.GPT)

                # Nothing should have changed
                self.assertEqual(dev.read(0, 33), data)

                # Create a new partition on dsk
                part = dsk.new_partition(disk.PartitionType.NORMAL, filesys.FileSystemType.WNT.ext4, 2048, 4095)
                dsk.add_partition(part, constraint.Constraint.any(dev))

                # And create a new partition with NO filesystem
                part2 = dsk.new_partition(disk.PartitionType.NORMAL, filesys.FileSystemType.none(), 4096, 6143)
                dsk.add_partition(part2, constraint.Constraint.any(dev))

                # Nothing should have changed
                self.assertEqual(dev.read(0, 33), data)

                # Now sync to disk, and read back the data
                dsk.commit_to_dev()

                # Now the data should be different
                self.assertNotEqual(dev.read(0, 33), data)

                # The partition number 1 shouls be ecual to part
                self.assertEqual(dsk.get_partition(1), part)
                self.assertEqual(dsk.get_partition(2), part2)
                

                # Now create a new partition and add it to the table with "create_partition"
                # Has to be committed to disk
                part3 = dsk.create_partition(disk.PartitionType.NORMAL, filesys.FileSystemType.WNT.fat32, 6144, 8191)
                dsk.commit_to_dev()

                self.assertEqual(dsk.get_partition(3), part3)

    def test_probe_all(self) -> None:
        if os.geteuid() != 0:
            self.skipTest('Test requires root privileges')

        device.Device.probe_all()

        for i in device.Device.enumerate():
            print(i)
            self.assertTrue(bool(i))
            self.assertTrue(i.path)
            self.assertTrue(i.model)
            self.assertTrue(i.sector_size)
            self.assertTrue(i.phys_sector_size)
            self.assertTrue(i.length)
            self.assertTrue(i.size)
            self.assertTrue(i.hw_geom)
            self.assertTrue(i.bios_geom)

    def test_device_str_and_eq(self) -> None:
        with create_empty_disk_image_ctx(partedtest.PartedTestCase.MiB) as disk_path:
            dev = device.Device.get(disk_path)
            self.assertTrue(bool(dev))
            self.assertEqual(dev, dev)
            self.assertNotEqual(dev, None)
            self.assertNotEqual(dev, 0)
            self.assertIsInstance(str(dev), str)
            self.assertEqual(str(dev), repr(dev))

            # Device type and CHSGeometry
            dt = device.DeviceType.NVME
            chs = device.CHSGeometry(1, 2, 3)

            self.assertIsInstance(str(dt), str)
            self.assertEqual(str(dt), repr(dt))
            self.assertIsInstance(str(chs), str)
            self.assertEqual(str(chs), repr(chs))
