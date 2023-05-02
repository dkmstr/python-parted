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

from parted import _parted  # type: ignore
from parted import alignment, geom, exceptions, device

from tests.util import partedtest, create_empty_disk_image_ctx


class TestPartedAlignment(partedtest.PartedTestCase):
    def test_alignment_null(self) -> None:
        for i in (None, _parted.ffi.NULL, False):
            al = alignment.Alignment(i)
            self.assertEqual(al.obj, _parted.ffi.NULL)

        al = alignment.Alignment(_parted.ffi.NULL)
        self.assertEqual(al.grain_size, 0)
        self.assertEqual(al.offset, 0)

        # Ensure method raises errrors
        self.assertRaises(exceptions.InvalidObjectError, al.init, 0, 1)
        # duplicate of none gives none, so no error
        al.duplicate()
        self.assertRaises(exceptions.InvalidObjectError, al.intersect, al)
        self.assertRaises(
            exceptions.InvalidObjectError,
            al.align_up,
            geom.Geometry(_parted.ffi.NULL),
            0,
        )
        self.assertRaises(
            exceptions.InvalidObjectError,
            al.align_down,
            geom.Geometry(_parted.ffi.NULL),
            0,
        )
        self.assertRaises(
            exceptions.InvalidObjectError,
            al.align_nearest,
            geom.Geometry(_parted.ffi.NULL),
            0,
        )
        self.assertRaises(
            exceptions.InvalidObjectError,
            al.is_aligned,
            geom.Geometry(_parted.ffi.NULL),
            0,
        )

    def test_alignment(self) -> None:
        # Create an alignment, all sectors
        any = alignment.Alignment.new(0, 1)

        # ensures bool(any) is True
        self.assertTrue(any)

        self.assertEqual(any.offset, 0)
        self.assertEqual(any.grain_size, 1)
        self.assertEqual(any, alignment.Alignment.any())
        self.assertNotEqual(any, alignment.Alignment.none())

        none = alignment.Alignment.new(0, 0)
        self.assertEqual(none.offset, 0)
        self.assertEqual(none.grain_size, 0)
        self.assertEqual(none, alignment.Alignment.none())  # Alignment.none() is a reference to "NULL" alignment
        self.assertNotEqual(none, alignment.Alignment.any())

    def test_alignment_align_up(self) -> None:
        with create_empty_disk_image_ctx(partedtest.PartedTestCase.MiB) as disk_path:
            dev = device.Device.get(disk_path)
            # Create a geometry, half of the disk
            first_half_geom = geom.Geometry.new(dev, 0, dev.length // 2)
            second_half_geom = geom.Geometry.new(dev, dev.length // 2, dev.length // 2)

            # Create an alignment, all pair sectors
            pair = alignment.Alignment.new(0, 2)

            # Create an alignment, all odd sectors
            odd = alignment.Alignment.new(1, 2)

            # Create an alignment, all sectors
            any = alignment.Alignment.new(0, 1)

            # Now test some alignments
            self.assertEqual(any.align_up(first_half_geom, 0), 0)
            self.assertEqual(any.align_up(first_half_geom, 1), 1)

            # For second half, sector are "rounded up" to geom start
            self.assertEqual(any.align_up(second_half_geom, 0), dev.length // 2)
            self.assertEqual(any.align_up(second_half_geom, 1), dev.length // 2)

            self.assertEqual(pair.align_up(first_half_geom, 0), 0)
            self.assertEqual(pair.align_up(first_half_geom, 1), 2)

            # For second half, sector are "rounded up" to geom start
            self.assertEqual(pair.align_up(second_half_geom, 0), dev.length // 2)
            self.assertEqual(pair.align_up(second_half_geom, 1), dev.length // 2)

            self.assertEqual(odd.align_up(first_half_geom, 0), 1)
            self.assertEqual(odd.align_up(first_half_geom, 1), 1)

            # For second half, sector are "rounded up" to geom start
            self.assertEqual(odd.align_up(second_half_geom, 0), dev.length // 2 + 1)
            self.assertEqual(odd.align_up(second_half_geom, 1), dev.length // 2 + 1)

            self.assertEqual(odd.align_up(second_half_geom, dev.length // 2), dev.length // 2 + 1)
            self.assertEqual(odd.align_up(second_half_geom, dev.length // 2 + 1), dev.length // 2 + 1)
            self.assertEqual(odd.align_up(second_half_geom, dev.length // 2 + 2), dev.length // 2 + 3)

    def test_alignment_align_down(self) -> None:
        with create_empty_disk_image_ctx(partedtest.PartedTestCase.MiB) as disk_path:
            dev = device.Device.get(disk_path)
            # Create a geometry, half of the disk
            first_half_geom = geom.Geometry.new(dev, 0, dev.length // 2)
            second_half_geom = geom.Geometry.new(dev, dev.length // 2, dev.length // 2)

            # Create an alignment, all pair sectors
            pair = alignment.Alignment.new(0, 2)

            # Create an alignment, all odd sectors
            odd = alignment.Alignment.new(1, 2)

            # Create an alignment, all sectors
            any = alignment.Alignment.new(0, 1)

            # Now test some alignments
            self.assertEqual(any.align_down(first_half_geom, 0), 0)
            self.assertEqual(any.align_down(first_half_geom, 1), 1)

            # For second half, sector are "rounded down" to geom start
            self.assertEqual(any.align_down(second_half_geom, 0), dev.length // 2)
            self.assertEqual(any.align_down(second_half_geom, 1), dev.length // 2)

            self.assertEqual(pair.align_down(first_half_geom, 0), 0)
            self.assertEqual(pair.align_down(first_half_geom, 1), 0)

            # For second half, sector are "rounded down" to geom start
            self.assertEqual(pair.align_down(second_half_geom, 0), dev.length // 2)
            self.assertEqual(pair.align_down(second_half_geom, 1), dev.length // 2)

            self.assertEqual(odd.align_down(first_half_geom, 0), 1)
            self.assertEqual(odd.align_down(first_half_geom, 1), 1)

            # For second half, sector are "rounded down" to geom start
            self.assertEqual(odd.align_down(second_half_geom, 0), dev.length // 2 + 1)
            self.assertEqual(odd.align_down(second_half_geom, 1), dev.length // 2 + 1)
            self.assertEqual(odd.align_down(second_half_geom, 2), dev.length // 2 + 1)

    def test_alignment_align_nearest(self) -> None:
        with create_empty_disk_image_ctx(partedtest.PartedTestCase.MiB) as disk_path:
            dev = device.Device.get(disk_path)
            # Create a geometry, half of the disk
            first_half_geom = geom.Geometry.new(dev, 0, dev.length // 2)
            second_half_geom = geom.Geometry.new(dev, dev.length // 2, dev.length // 2)

            # Create an alignment, all pair sectors
            pair = alignment.Alignment.new(0, 2)

            # Create an alignment, all odd sectors
            odd = alignment.Alignment.new(1, 2)

            # Create an alignment, all sectors
            any = alignment.Alignment.new(0, 1)

            # Now test some alignments
            self.assertEqual(any.align_nearest(first_half_geom, 0), 0)
            self.assertEqual(any.align_nearest(first_half_geom, 1), 1)

            # For second half, sector are "rounded down" to geom start
            self.assertEqual(any.align_nearest(second_half_geom, 0), dev.length // 2)
            self.assertEqual(any.align_nearest(second_half_geom, 1), dev.length // 2)

            self.assertEqual(pair.align_nearest(first_half_geom, 0), 0)
            self.assertEqual(pair.align_nearest(first_half_geom, 1), 0)

            # For second half, sector are "rounded down" to geom start
            self.assertEqual(pair.align_nearest(second_half_geom, 0), dev.length // 2)
            self.assertEqual(pair.align_nearest(second_half_geom, 1), dev.length // 2)

            self.assertEqual(odd.align_nearest(first_half_geom, 0), 1)
            self.assertEqual(odd.align_nearest(first_half_geom, 1), 1)

            # For second half, sector are "rounded down" to geom start
            self.assertEqual(odd.align_nearest(second_half_geom, 0), dev.length // 2 + 1)
            self.assertEqual(odd.align_nearest(second_half_geom, 1), dev.length // 2 + 1)
            self.assertEqual(odd.align_nearest(second_half_geom, 2), dev.length // 2 + 1)

    def test_aligment_is_aligned(self) -> None:
        with create_empty_disk_image_ctx(partedtest.PartedTestCase.MiB) as disk_path:
            dev = device.Device.get(disk_path)
            # Create a geometry, half of the disk
            first_half_geom = geom.Geometry.new(dev, 0, dev.length // 2)
            second_half_geom = geom.Geometry.new(dev, dev.length // 2, dev.length // 2)

            # Create an alignment, all pair sectors
            pair = alignment.Alignment.new(0, 2)

            # Create an alignment, all odd sectors
            odd = alignment.Alignment.new(1, 2)

            # Create an alignment, all sectors
            any = alignment.Alignment.new(0, 1)

            # Now test some alignments
            self.assertTrue(any.is_aligned(first_half_geom, 0))
            self.assertTrue(any.is_aligned(first_half_geom, 1))

            self.assertTrue(any.is_aligned(second_half_geom, dev.length // 2))
            self.assertTrue(any.is_aligned(second_half_geom, dev.length // 2 + 1))

            self.assertTrue(pair.is_aligned(first_half_geom, 0))
            self.assertFalse(pair.is_aligned(first_half_geom, 1))

            # For second half, sector are "rounded down" to geom start
            self.assertTrue(pair.is_aligned(second_half_geom, dev.length // 2))
            self.assertFalse(pair.is_aligned(second_half_geom, dev.length // 2 + 1))

            self.assertFalse(odd.is_aligned(second_half_geom, 0))
            self.assertFalse(odd.is_aligned(second_half_geom, 1))

            # For second half, sector are "rounded down" to geom start
            self.assertFalse(odd.is_aligned(second_half_geom, dev.length // 2))
            self.assertTrue(odd.is_aligned(second_half_geom, dev.length // 2 + 1))
            self.assertFalse(odd.is_aligned(second_half_geom, dev.length // 2 + 2))

    def test_aligment_intersect(self) -> None:
        any = alignment.Alignment.any()
        pair = alignment.Alignment.new(0, 2)
        odd = alignment.Alignment.new(1, 2)
        none = alignment.Alignment.none()

        self.assertEqual(any.intersect(any), any)
        self.assertEqual(any.intersect(pair), pair)
        self.assertEqual(any.intersect(odd), odd)

        self.assertEqual(pair.intersect(any), pair)
        self.assertEqual(pair.intersect(pair), pair)
        self.assertEqual(pair.intersect(odd), none)

        self.assertEqual(odd.intersect(any), odd)
        self.assertEqual(odd.intersect(pair), none)
        self.assertEqual(odd.intersect(odd), odd)

        # Use ^ to test the __xor__ method
        self.assertEqual(any ^ any, any)
        self.assertEqual(any ^ pair, pair)
        self.assertEqual(any ^ odd, odd)

        self.assertEqual(pair ^ any, pair)
        self.assertEqual(pair ^ pair, pair)
        self.assertEqual(pair ^ odd, none)

        self.assertEqual(odd ^ any, odd)
        self.assertEqual(odd ^ pair, none)
        self.assertEqual(odd ^ odd, odd)

    def test_alignment_comparison(self) -> None:
        any = alignment.Alignment.any()
        pair = alignment.Alignment.new(0, 2)
        odd = alignment.Alignment.new(1, 2)
        none = alignment.Alignment.none()

        self.assertEqual(any, any)
        self.assertNotEqual(any, pair)
        self.assertNotEqual(any, odd)

        self.assertNotEqual(pair, any)
        self.assertEqual(pair, pair)
        self.assertNotEqual(pair, odd)

        self.assertNotEqual(odd, any)
        self.assertNotEqual(odd, pair)
        self.assertEqual(odd, odd)

        self.assertNotEqual(none, any)
        self.assertNotEqual(none, pair)
        self.assertNotEqual(none, odd)
        self.assertEqual(none, none)

        self.assertNotEqual(any, 1)

    def test_aligment_duplication(self) -> None:
        any = alignment.Alignment.any()
        pair = alignment.Alignment.new(0, 2)
        odd = alignment.Alignment.new(1, 2)
        none = alignment.Alignment.none()

        self.assertEqual(any.duplicate(), any)
        self.assertEqual(pair.duplicate(), pair)
        self.assertEqual(odd.duplicate(), odd)
        self.assertEqual(none.duplicate(), none)

    def test_aligment_init(self) -> None:
        align = alignment.Alignment.new(0, 4)

        self.assertEqual(align.offset, 0)
        self.assertEqual(align.grain_size, 4)

        align.init(1, 2)
        self.assertEqual(align.offset, 1)
        self.assertEqual(align.grain_size, 2)

    def test_aligment_str(self) -> None:
        any = alignment.Alignment.any()
        pair = alignment.Alignment.new(0, 2)
        odd = alignment.Alignment.new(1, 2)
        none = alignment.Alignment.none()

        self.assertIsInstance(str(any), str)
        self.assertIsInstance(str(pair), str)
        self.assertIsInstance(str(odd), str)
        self.assertIsInstance(str(none), str)

        self.assertEqual(str(any), repr(any))
        self.assertEqual(str(pair), repr(pair))
        self.assertEqual(str(odd), repr(odd))
        self.assertEqual(str(none), repr(none))
    
        