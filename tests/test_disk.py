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
from parted import disk, exceptions, excpt, device, constraint, geom, timer

from tests.util import partedtest, create_empty_disk_image_ctx, create_gpt_disk_image_ctx, create_msdos_disk_image_ctx

logger = logging.getLogger(__name__)


class TestPartedDisk(partedtest.PartedTestCase):
    def test_disk_type(self) -> None:
        dt = disk.DiskType.from_name(disk.DiskType.WNT.GPT)
        self.assertEqual(dt.name, disk.DiskType.WNT.GPT)
        self.assertEqual(dt, disk.DiskType.WNT.GPT)
        self.assertIn(dt, (disk.DiskType.WNT.GPT, disk.DiskType.WNT.MSDOS))
        self.assertNotIn(dt, (disk.DiskType.WNT.MSDOS, disk.DiskType.WNT.BSD))
        self.assertEqual(dt.features, disk.DiskType.Feature.NAME)
        dg = disk.DiskType.from_name(disk.DiskType.WNT.MSDOS)
        self.assertEqual(dg.name, disk.DiskType.WNT.MSDOS)
        self.assertEqual(dg, disk.DiskType.WNT.MSDOS)
        self.assertIn(dg, (disk.DiskType.WNT.GPT, disk.DiskType.WNT.MSDOS, disk.DiskType.WNT.BSD))
        self.assertNotIn(dg, (disk.DiskType.WNT.GPT, disk.DiskType.WNT.BSD))
        self.assertEqual(dg.features, disk.DiskType.Feature.EXTENDED)

        # Enumerate all types
        for dt in disk.DiskType.enumerate():
            logger.info('Disk type: %s', dt)
            self.assertIsInstance(dt, disk.DiskType)
            self.assertIsInstance(dt.name, str)
            self.assertIsInstance(dt.features, disk.DiskType.Feature)

        self.assertEqual(next(iter(disk.DiskType.enumerate())), disk.DiskType.first_type())

        # Test creation and equality
        for dt in (
            disk.DiskType('msdos'),
            disk.DiskType(disk.DiskType.WNT.MSDOS),
            disk.DiskType.from_name('msdos'),
            disk.DiskType.from_name(disk.DiskType.WNT.MSDOS),
        ):
            self.assertEqual(dt, disk.DiskType.WNT.MSDOS)
            self.assertEqual(dt, 'msdos')
            self.assertNotEqual(dt, disk.DiskType('gpt'))
            self.assertNotEqual(dt, 0)
            self.assertTrue(dt.next_type())

        # str y repr de disk.DiskType.WNT
        self.assertIsInstance(str(disk.DiskType.WNT.MSDOS), str)
        self.assertIsInstance(repr(disk.DiskType.WNT.MSDOS), str)
        self.assertEqual(str(disk.DiskType.WNT.MSDOS), repr(disk.DiskType.WNT.MSDOS))

        # str y repr de disk.DiskType
        self.assertIsInstance(str(disk.DiskType('msdos')), str)
        self.assertIsInstance(repr(disk.DiskType('msdos')), str)
        self.assertEqual(str(disk.DiskType('msdos')), repr(disk.DiskType('msdos')))

    def test_disk_null(self) -> None:
        for i in (None, _parted.ffi.NULL):
            dsk = disk.Disk(i)
            self.assertEqual(dsk.obj, _parted.ffi.NULL)

    def test_disk_as_array(self) -> None:
        with self.exception_context():
            with create_msdos_disk_image_ctx() as path:
                dsk = disk.Disk(device.Device.get(path))

                self.assertEqual(len(dsk), len(dsk.partitions))

                for i in range(len(dsk)):
                    self.assertIsInstance(dsk[i], disk.Partition)
                    self.assertEqual(dsk[i], dsk.partitions[i])

    def test_disk_empty(self) -> None:
        with create_empty_disk_image_ctx() as path:
            dev = device.Device.get(path)
            dskType = dev.probe()
            self.assertEqual(dskType.name, '')  # Empty name means unknown

            with self.exception_context():
                dsk = dev.read_table()
                # No partition table available
                self.assertFalse(dsk)
                self.assertFalse(dsk.dev)
                self.assertFalse(dsk.type)
                self.assertEqual(dsk.partitions, [])
                self.assertEqual(dsk.last_partition_num, 0)
                self.assertEqual(dsk.max_primary_partition_count, 0)
                with self.assertRaises(exceptions.PartedException):
                    dsk.check()

        self.assertEqual(self.total_exceptions, 1)  # Disk.read will raise an exception

    def test_disk_msdos(self) -> None:
        with self.exception_context():
            with create_msdos_disk_image_ctx() as path:
                dev = device.Device.get(path)
                dskType = dev.probe()
                self.assertEqual(dskType.name, 'msdos')

                dsk = dev.read_table()
                self.assertTrue(dsk)
                self.assertNotEqual(dsk, False)
                self.assertEqual(dsk.last_partition_num, 6)
                self.assertEqual(len(dsk.partitions), 15)
                self.assertEqual(len(dsk.active_partitions), 5)
                self.assertEqual(len(dsk.free_partitions), 2)
                self.assertEqual(dsk.max_primary_partition_count, 4)  # msdos can have 4 primary partitions
                for i in dsk.partitions:
                    self.assertEqual(i.disk, dsk)
                    self.assertTrue(i)
                    s = str(i)
                    logger.info(s)

                self.assertEqual(self.total_exceptions, 0)

                # 8 partitions inside extended partition
                self.assertEqual(len(dsk.get_extended_partition().extended_list), 8)
                self.assertEqual(len(dsk.get_extended_partition().extended_list_free), 3)
                self.assertEqual(len(dsk.get_extended_partition().extended_list_active), 2)

                for n in range(5):
                    self.assertEqual(dsk.active_partitions[n].active, True)
                    self.assertEqual(dsk.active_partitions[n], dsk.get_partition(dsk.active_partitions[n].num))

                const = constraint.Constraint.any(dev)
                self.assertEqual(geom.Geometry.new(dev, 2, 4078), dsk.active_partitions[0].max_geometry(const))
                self.assertEqual(geom.Geometry.new(dev, 4590, 3570), dsk.active_partitions[1].max_geometry(const))
                self.assertEqual(geom.Geometry.new(dev, 8670, 56610), dsk.active_partitions[2].max_geometry(const))
                self.assertEqual(geom.Geometry.new(dev, 8670, 9690), dsk.active_partitions[3].max_geometry(const))
                self.assertEqual(geom.Geometry.new(dev, 16832, 28048), dsk.active_partitions[4].max_geometry(const))

                self.assertEqual(
                    dsk.get_partition_by_sector(dsk.active_partitions[0].geometry.start + 10), dsk.active_partitions[0]
                )
                self.assertEqual(
                    dsk.get_partition_by_sector(dsk.active_partitions[4].geometry.start + 10), dsk.active_partitions[4]
                )

                # Resize first active partition to a size larger than disk
                logger.info('Testing %s', dsk[0].geometry)
                # Note:
                dsk.active_partitions[0].delete()
                # Second partition now is first
                # this will not fail, but will resize the partition to the maximum possible size with the given constraint
                # asnd constraint allows the change of start and end sectors to any value
                dsk.active_partitions[0].set_geometry(const, 1, dev.length)
                self.assertEqual(dsk.active_partitions[0].geometry, geom.Geometry.new(dev, 2, 8158))

                part = dsk.active_partitions[0]
                for start, end in ((-1, dev.length), (2, 1), (part.geometry.start, dev.length + 1)):
                    with self.assertRaises(exceptions.PartedException, msg='start: %s, end: %s' % (start, end)):
                        part.set_geometry(const, start, end)

                dsk.minimize_extended_partition()
                self.assertEqual(len(dsk.get_extended_partition().extended_list), 7)
                # Before resizing, geometry was Geometry(start=8192, end=45055, length=36864)
                self.assertEqual(dsk.get_extended_partition().geometry, geom.Geometry(dev, 10200, 16830))

                dsk.set_flag(disk.DiskFlag.CYLINDER_ALIGNMENT, False)

                self.assertEqual(dsk.check(), True)

    def test_disk_gpt(self) -> None:
        with self.exception_context():
            with create_gpt_disk_image_ctx() as path:
                dev = device.Device.get(path)
                dskType = dev.probe()
                self.assertEqual(dskType.name, disk.DiskType.WNT.GPT)

                dsk = dev.read_table()
                self.assertTrue(dsk)
                self.assertEqual(dsk.last_partition_num, 3)
                self.assertEqual(len(dsk.partitions), 9)
                self.assertEqual(len(dsk.active_partitions), 3)
                self.assertEqual(len(dsk.free_partitions), 4)
                self.assertEqual(dsk.max_primary_partition_count, 128)  # gtp can have 128 primary partitions
                for i in dsk.partitions:
                    s = str(i)
                    logger.info(i)

                self.assertEqual(self.total_exceptions, 0)

                #
                dsk.active_partitions[0].name = 'bema'

                self.assertEqual(dsk.partitions[2].name, 'bema')

                for n in range(3):
                    self.assertEqual(dsk.active_partitions[n].active, True)
                    self.assertEqual(dsk.active_partitions[n], dsk.get_partition(dsk.active_partitions[n].num))

                const = constraint.Constraint.any(dev)
                logger.info('Testing %s with max geometry with constraint %s', dsk.active_partitions[0], const)
                self.assertEqual(geom.Geometry.new(dev, 34, 8158), dsk.active_partitions[0].max_geometry(const))
                logger.info('Testing %s with max geometry with constraint %s', dsk.active_partitions[1], const)
                self.assertEqual(geom.Geometry.new(dev, 4096, 18432), dsk.active_partitions[1].max_geometry(const))
                logger.info('Testing %s with max geometry with constraint %s', dsk.active_partitions[2], const)
                self.assertEqual(geom.Geometry.new(dev, 14336, 51167), dsk.active_partitions[2].max_geometry(const))

                self.assertRaises(exceptions.PartedException, dsk.get_extended_partition)

                # The rest of the tests are covered with msdos disk

    def test_copy_disk(self) -> None:
        with self.exception_context():
            with create_msdos_disk_image_ctx() as path:
                dev = device.Device.get(path)
                dev.open()
                dsk = dev.read_table()  # Same as disk.Disk(dev)
                # Copy sectors from start_geom to end_geom, direction of copy is determined
                # by the sign of the difference between origin and destination start sectors
                # se we do not overwrite the data we are copying
                call_count = 0

                def timerCallback(t: 'timer.Timer') -> None:
                    nonlocal call_count
                    call_count += 1

                tmr = timer.Timer.new(timerCallback)

                # Get a copy of destination region before to check later
                # that the copy was done correctly
                start_geom = geom.Geometry.new(dev, 0, 128)
                saved = dev.read(start_geom.start, start_geom.length)
                dev.copy(start_geom, 256, tmr, sectors_block=19)
                self.assertEqual(dev.read(256, 128), saved)
                self.assertNotEqual(call_count, 0)
                # Now overlapping copy
                call_count = 0
                saved = dev.read(start_geom.start, start_geom.length)
                dev.copy(start_geom, 64, tmr, sectors_block=23)
                self.assertEqual(dev.read(64, 128), saved)
                self.assertNotEqual(call_count, 0)
                # Now copy to the same place
                call_count = 0
                saved = dev.read(start_geom.start, start_geom.length)
                dev.copy(start_geom, 0, tmr, sectors_block=29)
                self.assertEqual(dev.read(0, 128), saved)
                self.assertEqual(call_count, 0)  # No copy was done

                # Nos backward copy
                call_count = 0
                start_geom = geom.Geometry.new(dev, 256, 128)
                saved = dev.read(start_geom.start, start_geom.length)
                dev.copy(start_geom, start_geom.start - 64, tmr, sectors_block=31)
                self.assertEqual(dev.read(start_geom.start - 64, 128), saved)

                # Write changes to disk
                dsk.commit_to_dev()

    def test_disk_str(self) -> None:
        dsk = disk.Disk()
        self.assertIsInstance(str(dsk), str)
        self.assertEqual(str(dsk), repr(dsk))

        with create_gpt_disk_image_ctx() as path:
            dev = device.Device.get(path)

            dsk = dev.read_table()
            self.assertTrue(dsk)

            self.assertIsInstance(str(dsk), str)
            self.assertEqual(str(dsk), repr(dsk))
