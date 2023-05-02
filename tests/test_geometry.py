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
import io
import typing

from parted import _parted  # type: ignore
from parted import alignment, geom, exceptions, device

from tests.util import partedtest, create_gpt_disk_image_ctx


class TestPartedGeometry(partedtest.PartedTestCase):
    def test_geometry_null_works(self) -> None:
        for i in (None, _parted.ffi.NULL):
            geometry = geom.Geometry(i)
            self.assertEqual(geometry.obj, _parted.ffi.NULL)
            self.assertEqual(geometry.start, 0)
            geometry.start = 31
            self.assertEqual(geometry.start, 0)
            self.assertEqual(geometry.length, 0)
            geometry.length = 31
            self.assertEqual(geometry.length, 0)
            self.assertEqual(geometry.end, 0)
            geometry.end = 31
            self.assertEqual(geometry.end, 0)
            self.assertEqual(geometry.dev, device.Device())
            with self.assertRaises(exceptions.PartedException):
                self.assertNotIn(0, geometry)

    def test_geometry_new_and_constructor(self) -> None:
        with self.exception_context():
            dev = device.Device.get('non_existing_test_image.img')  # invalid device
            g1 = geom.Geometry(dev, 0, 100)
            self.assertEqual(g1.obj, _parted.ffi.NULL)

            self.assertEqual(self.total_exceptions, 1)  # One exception, creom creating device

            with create_gpt_disk_image_ctx() as path:
                dev = device.Device.get(path)
                g2 = geom.Geometry(dev, 0, 100)
                self.assertNotEqual(g2.obj, _parted.ffi.NULL)

                self.assertEqual(g2.dev, dev)
                self.assertEqual(g2.start, 0)
                self.assertEqual(g2.length, 100)
                self.assertEqual(g2.end, 99)

                g3 = geom.Geometry.new(dev, 0, 100)
                self.assertNotEqual(g3.obj, _parted.ffi.NULL)
                self.assertEqual(g2, g3)


    def test_geometry_create_and_destroy(self) -> None:
        with self.exception_context():
            with self.override_init_del_add_counter(geom.Geometry):
                lst: list[geom.Geometry] = []
                CHECKS = 100
                with create_gpt_disk_image_ctx() as path:
                    dev = device.Device.get(path)
                    for i in range(CHECKS):
                        lst.append(geom.Geometry.new(dev, 0, 100))
                
                    self.assertEqual(self.get_counter(geom.Geometry), CHECKS)
                    del lst
                    self.assertEqual(self.get_counter(geom.Geometry), 0)

                    # Now with new
                    lst = []
                    for i in range(CHECKS):
                        lst.append(geom.Geometry.new(dev, 0, 100))
                    
                    self.assertEqual(self.get_counter(geom.Geometry), CHECKS)
                    del lst
                    self.assertEqual(self.get_counter(geom.Geometry), 0)

                    # And now operations that creates new objects
                    # these are intersect and duplicate
                    for i in range(CHECKS):  # A few checks, to ensure no leaks..
                        g1 = geom.Geometry.new(dev, 0, 100)
                        g2 = geom.Geometry.new(dev, 50, 100)
                        g3 = g1.intersect(g2)
                        self.assertEqual(self.get_counter(geom.Geometry), 3)
                        del g3
                        self.assertEqual(self.get_counter(geom.Geometry), 2)
                        del g2
                        self.assertEqual(self.get_counter(geom.Geometry), 1)
                        del g1
                        self.assertEqual(self.get_counter(geom.Geometry), 0)
    
    def test_geometry_equality_and_operators(self) -> None:
        with create_gpt_disk_image_ctx() as path:
            dev = device.Device.get(path)
            g1 = geom.Geometry.new(dev, 2, 100)
            g1p = geom.Geometry.new(dev, 2, 100)
            g2 = geom.Geometry.new(dev, 0, 103)
            g3 = geom.Geometry.new(dev, 50, 101)
            g4 = geom.Geometry.new(dev, 102, 100)
            g5 = geom.Geometry()

            self.assertEqual(g1, g1p)
            self.assertNotEqual(g1, g3)
            self.assertNotEqual(g1, g4)
            self.assertNotEqual(g1, 0)
            self.assertNotEqual(g1, g5)

            self.assertIn(2, g1)
            self.assertNotIn(104, g1)
            self.assertNotIn(102, g1)
            self.assertNotIn(-1, g1)
            # Str or floart is not in            
            self.assertNotIn('h', g1)
            self.assertNotIn(0.0, g1)

            self.assertIn(g1, g2)

            # Asserts intersection is correct
            self.assertEqual(g1.intersect(g2), g1)
            self.assertEqual(g1^g2, g1)

            self.assertTrue(g1.overlap(g3))
            self.assertFalse(g4.overlap(g1))

            self.assertEqual(g1.map(g3, 0), -1)  # 0 if out of g3, so -1
            self.assertEqual(g1.map(g3, 48), 0)  # g1 start + 48 = 0 g3
            self.assertEqual(g1.map(g3, 49), 1)  # g1 start + 49 = 1 g3
            self.assertEqual(g1.map(g3, 50), 2)  # g31 start + 50 = 2 g3

            g1.set(10, 32)
            self.assertEqual(g1.start, 10)
            self.assertEqual(g1.length, 32)

            self.assertRaises(exceptions.NotOpenedError, g1.sync)
            self.assertRaises(exceptions.PartedException, g1.sync_fast)

            dev.open()
            g1.sync()
            g1.sync_fast()


    def test_geometry_io(self) -> None:
        with create_gpt_disk_image_ctx() as path:
            dev = device.Device.get(path)
            dev.open()
            g1 = geom.Geometry.new(dev, 0, 384)
            g2 = geom.Geometry.new(dev, 1024, 2048)

            # Will write 3 sectors
            buffer = self.random_bytes(dev.sector_size*2+1)
            g1.write(buffer, 0)
            g2.write(buffer, 32)
            self.assertEqual(g1.read(0, 3)[:dev.sector_size*2+1], buffer)
            self.assertEqual(g2.read(32, 3)[:dev.sector_size*2+1], buffer)

            self.assertEqual(g1.check(0), 0)
            self.assertEqual(g2.check(32), 0)

    def test_geometry_str_repr(self) -> None:
        with create_gpt_disk_image_ctx() as path:
            dev = device.Device.get(path)
            g1 = geom.Geometry.new(dev, 0, 384)
            
            self.assertIsInstance(str(g1), str)
            self.assertIsInstance(repr(g1), str)
            self.assertEqual(str(g1), repr(g1))
