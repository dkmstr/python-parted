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
from hashlib import new
from parted import _parted  # type: ignore
from parted import constraint, alignment, geom, device, exceptions, disk

from tests.util import partedtest, create_empty_disk_image_ctx


class TestPartedConstraint(partedtest.PartedTestCase):
    def test_constraint_null(self) -> None:
        for i in (None, _parted.ffi.NULL):
            const = constraint.Constraint(i)
            self.assertEqual(const.obj, _parted.ffi.NULL)

        const = constraint.Constraint(_parted.ffi.NULL)
        self.assertEqual(const.obj, _parted.ffi.NULL)
        self.assertEqual(const.start_align, alignment.Alignment.none())
        self.assertEqual(const.end_align, alignment.Alignment.none())
        self.assertEqual(const.start_range, geom.Geometry(None))
        self.assertEqual(const.end_range, geom.Geometry(None))
        self.assertEqual(const.min_size, 0)
        self.assertEqual(const.max_size, 0)

    def test_constaint_any_exact(self) -> None:
        with create_empty_disk_image_ctx(partedtest.PartedTestCase.MiB) as disk_path:
            dev = device.Device.get(disk_path)

            full_geom = geom.Geometry.new(dev, 0, dev.length)
            const = constraint.Constraint.any(dev)
            self.assertNotEqual(const.obj, _parted.ffi.NULL)
            self.assertEqual(const.start_align, alignment.Alignment.any())
            self.assertEqual(const.end_align, alignment.Alignment.any())
            self.assertEqual(const.start_range, full_geom)
            self.assertEqual(const.end_range, full_geom)
            self.assertEqual(const.min_size, 1)
            self.assertEqual(const.max_size, dev.length)

            geometry = geom.Geometry.new(dev, 0, dev.length // 2)
            const = constraint.Constraint.exact(geometry)

            self.assertNotEqual(const.obj, _parted.ffi.NULL)
            # offset 0, grain size = 0 (that is, only sector 0 matches)
            self.assertEqual(const.start_align, alignment.Alignment.none())
            # offset end-1, grain size = 0 (that is, only sector end-1 matches)
            self.assertEqual(const.end_align, alignment.Alignment.new(offset=dev.length // 2 - 1, grain_size=0))
            self.assertEqual(const.start_range, geom.Geometry.new(dev, geometry.start, 1))
            self.assertEqual(const.end_range, geom.Geometry.new(dev, geometry.end, 1))

    def test_constraint_new(self) -> None:
        with create_empty_disk_image_ctx(partedtest.PartedTestCase.MiB) as disk_path:
            dev = device.Device.get(disk_path)

            start_align = alignment.Alignment.none()
            end_align = alignment.Alignment.any()
            start_range = geom.Geometry.new(dev, 0, 10)
            end_range = geom.Geometry.new(dev, 0, 20)

            const = constraint.Constraint.new(start_align, end_align, start_range, end_range, 1, dev.length)
            self.assertTrue(const)
            self.assertNotEqual(const.obj, _parted.ffi.NULL)
            self.assertEqual(const.start_align, start_align)
            self.assertEqual(const.end_align, end_align)
            self.assertEqual(const.start_range, start_range)
            self.assertEqual(const.end_range, end_range)
            self.assertEqual(const.min_size, 1)
            self.assertEqual(const.max_size, dev.length)

            const = constraint.Constraint.any(dev)

            self.assertTrue(const)
            self.assertNotEqual(const.obj, _parted.ffi.NULL)
            self.assertEqual(const.start_align, alignment.Alignment.any())
            self.assertEqual(const.end_align, alignment.Alignment.any())
            self.assertEqual(const.start_range, geom.Geometry.new(dev, 0, dev.length))
            self.assertEqual(const.end_range, geom.Geometry.new(dev, 0, dev.length))
            self.assertEqual(const.min_size, 1)
            self.assertEqual(const.max_size, dev.length)

            # New from min
            const = constraint.Constraint.new_from_min(geom.Geometry.new(dev, 0, 10))
            self.assertTrue(const)
            self.assertNotEqual(const.obj, _parted.ffi.NULL)
            self.assertEqual(const.start_align, alignment.Alignment.any())
            self.assertEqual(const.end_align, alignment.Alignment.any())
            self.assertEqual(const.start_range, geom.Geometry.new(dev, 0, 1))
            self.assertEqual(const.end_range, geom.Geometry.new(dev, 9, dev.length - 9))

            # New from min_max
            # if min is outside of max, raises an exception
            with self.assertRaises(exceptions.PartedException):
                constraint.Constraint.new_from_min_max(
                    geom.Geometry.new(dev, 0, 10), geom.Geometry.new(dev, 1, dev.length // 2 - 5)
                )

            const = constraint.Constraint.new_from_min_max(
                geom.Geometry.new(dev, 4, 10), geom.Geometry.new(dev, 4, dev.length // 2 - 5)
            )
            self.assertTrue(const)
            self.assertNotEqual(const.obj, _parted.ffi.NULL)
            self.assertEqual(const.start_align, alignment.Alignment.any())
            self.assertEqual(const.end_align, alignment.Alignment.any())
            self.assertEqual(const.start_range, geom.Geometry.new(dev, 4, 1))
            self.assertEqual(const.end_range, geom.Geometry.new(dev, 9 + 4, dev.length // 2 - 14))

            # New from max
            max = geom.Geometry.new(dev, 0, 10)
            const = constraint.Constraint.new_from_max(max)
            self.assertTrue(const)
            self.assertNotEqual(const.obj, _parted.ffi.NULL)
            self.assertEqual(const.start_align, alignment.Alignment.any())
            self.assertEqual(const.end_align, alignment.Alignment.any())
            self.assertEqual(const.start_range, max)
            self.assertEqual(const.end_range, max)

    def test_constraint_duplicate(self) -> None:
        with create_empty_disk_image_ctx(partedtest.PartedTestCase.MiB) as disk_path:
            dev = device.Device.get(disk_path)
            const = constraint.Constraint.any(dev)
            const2 = const.duplicate()

            self.assertNotEqual(const.obj, _parted.ffi.NULL)
            self.assertNotEqual(const2.obj, _parted.ffi.NULL)
            self.assertEqual(const.start_align, const2.start_align)
            self.assertEqual(const.end_align, const2.end_align)
            self.assertEqual(const.start_range, const2.start_range)
            self.assertEqual(const.end_range, const2.end_range)
            self.assertEqual(const.min_size, const2.min_size)
            self.assertEqual(const.max_size, const2.max_size)

    def test_constaint_align(self) -> None:
        with create_empty_disk_image_ctx(partedtest.PartedTestCase.MiB*32) as disk_path:
            for algn_size in range(1, 4):
                dev = device.Device.get(disk_path)

                al = 1<<(8+algn_size)

                algn = constraint.Constraint.align(dev, al)  # to MiB

                # Create a partition table
                # First, initialize the partition table
                dev.open()
                dev.clobber()
                dsk = dev.new_table('msdos')
                part = dsk.create_partition(disk.PartitionType.NORMAL, 'ext4', 0, 1000, constraint=algn)
                self.assertTrue(part)
                self.assertEqual(part.geometry.length//al, part.geometry.length/al)
                self.assertEqual(part.geometry.start//al, part.geometry.start/al)
                self.assertEqual((part.geometry.end+1)//al, (part.geometry.end+1)/al)               

            # Data has not been written to disk yet

    def test_constraint_destroy(self) -> None:
        with self.override_init_del_add_counter(constraint.Constraint):
            with create_empty_disk_image_ctx(partedtest.PartedTestCase.MiB) as disk_path:
                consts = [
                    constraint.Constraint.new(
                        alignment.Alignment.none(),
                        alignment.Alignment.any(),
                        geom.Geometry.new(device.Device.get(disk_path), 0, 10),
                        geom.Geometry.new(device.Device.get(disk_path), 0, 20),
                        1,
                        100,
                    )
                    for i in range(128)
                ]

                self.assertEqual(self.get_counter(constraint.Constraint), 128)

                for i in range(128):  # remove e few times
                    dev = device.Device.get(disk_path)
                    const = constraint.Constraint.any(dev)
                    del const

                self.assertEqual(self.get_counter(constraint.Constraint), 128)

                del consts  # remove all

                self.assertEqual(self.get_counter(constraint.Constraint), 0)

    def test_constraint_operations(self) -> None:
        with create_empty_disk_image_ctx(partedtest.PartedTestCase.MiB) as disk_path:
            dev = device.Device.get(disk_path)

            const = constraint.Constraint.any(dev)
            # Create a constraint with basic data
            const2 = constraint.Constraint.new(
                alignment.Alignment.any(),
                alignment.Alignment.new(0, 2),
                geom.Geometry.new(dev, 0, 10),
                geom.Geometry.new(dev, 0, 20),
                1,
                100,
            )

            # Test intersect
            const3 = const.intersect(const2)
            self.assertEqual(const3.start_align, const2.start_align)
            self.assertEqual(const3.end_align, const2.end_align)
            self.assertEqual(const3.start_range, const2.start_range)
            self.assertEqual(const3.end_range, const2.end_range)
            self.assertEqual(const3.min_size, const2.min_size)
            self.assertEqual(const3.max_size, const2.max_size)

            # Check solution
            geom1 = geom.Geometry.new(dev, 2, 5)
            # goem starts fulfills the start_align, and is inside the start_range
            # geom ends fulfills the end_align, and is inside the end_range
            # geom size is between min_size and max_size
            # so geom1 is a solution
            self.assertTrue(const2.is_solution(geom1))
            geom1.length = 10  # geom1 is too big, end outside the end_range
            self.assertFalse(const2.is_solution(geom1))
            geom1.end = 10
            self.assertTrue(const2.is_solution(geom1))
            geom1.start = 10  # start if out of start_range
            self.assertFalse(const2.is_solution(geom1))
            geom1.start = 9
            self.assertTrue(const2.is_solution(geom1))

            # solves max & nearest
            geom1 = const2.solve_max()
            # start is with any alignment, between 0 and 9 (inclusive)
            # end is with alignment 0,2 (that is, any positive pair), between 0 and 19 (inclusive)
            # so the max geom is 0, 18, length 19
            self.assertEqual(geom1.start, 0)
            self.assertEqual(geom1.end, 18)
            self.assertEqual(geom1.length, 19)

            geom1 = const2.solve_nearest(geom.Geometry.new(dev, 0, 10))
            # start is with any alignment, between 0 and 9 (inclusive)
            # end is with alignment 0, 2 (that is, any positive pair), between 0 and 19 (inclusive)
            # so the nearest geom to (0, 10) is geom(0, 8)
            self.assertEqual(geom1.start, 0)
            self.assertEqual(geom1.end, 8)
            self.assertEqual(geom1.length, 9)

    def test_constraint_str(self) -> None:
        with create_empty_disk_image_ctx(partedtest.PartedTestCase.MiB) as disk_path:
            dev = device.Device.get(disk_path)

            const = constraint.Constraint.any(dev)
            self.assertIsInstance(str(const), str)
            self.assertEqual(str(const), repr(const))

            const = constraint.Constraint.new(
                alignment.Alignment.any(),
                alignment.Alignment.new(0, 2),
                geom.Geometry.new(dev, 0, 10),
                geom.Geometry.new(dev, 0, 20),
                1,
                100,
            )
            self.assertIsInstance(str(const), str)
            self.assertEqual(str(const), repr(const))
