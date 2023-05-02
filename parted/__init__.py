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
"""Parted module.

This module presents a pythonic interface to the parted library.
cffi is used to bind to the parted library. 

Example:
    >>> from parted import device, disk, constraint
    >>> dev = device.Device('/dev/sda')
    >>> dsk = dev.disk
    >>> # print information about the partition table
    >>> print(disk.debug())
    >>> with dev.open() as d:
    ...     first = dev.read(0)
    ...     last = dev.read(-1)
    ...     print(first, last)
    >>> # clobber partition table
    >>> dev.clobber()
    >>> # create a new partition table (disk)
    >>> dsk = dev.new_table(disk.DiskType.WNT.GPT)
    >>> # create a new partition on table
    >>> part = disk.Partition.new(dsk, disk.PartitionType.NORMAL, filesys.FileSystemType.WNT.ext4, 2048, 4095)
    >>> # add the partition to the table
    >>> dsk.add_partition(part, constraint.Constraint.any())



:author: Adolfo Gómez, dkmaster at dkmon dot com
"""
__version__ = '0.1.0'
__author__ = 'Adolfo Gómez'
__email__ = 'dkmaster at dkmon dot com'
__license__ = 'BSD-3-Clause'
