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
import os
import tempfile
import typing
import random
import contextlib

def rnd_extra() -> str:
    '''
    Returns a random string for extra
    '''
    return str(-random.randint(0, 100000000))

def create_empty_disk_image(extra: str = '', size: int = 1<<30) -> str:
    '''
    creates a temporary disk for testing purposes with the given size (defaults to 1 GiB)
    '''
    # some random chars so disk image is unique for every test
    rnd = ''.join(random.choices('0123456789abcdef', k=4))
    filename = os.path.join(tempfile.gettempdir(), f'parted_test_disk_{size//1024//1024}_{rnd}{extra}.img')
    # if exists, remove it
    if os.path.exists(filename):
        os.remove(filename)
    with open(filename, 'wb') as f:
        f.seek(size-1)
        f.write(b'\0')
    return filename

def create_msdos_disk_image(extra: str = '') -> str:
    '''
    creates a temporary disk with msdos partition table por testing purposes
    '''
    from . import msdosdsk
    # some random chars so disk image is unique for every test
    rnd = ''.join(random.choices('0123456789abcdef', k=4))
    filename = os.path.join(tempfile.gettempdir(), f'parted_test_disk_msdos_{rnd}{extra}.img')
    # if exists, remove it
    if os.path.exists(filename):
        os.remove(filename)
    with open(filename, 'wb') as f:
        f.write(msdosdsk.disk())
    return filename

def create_gpt_disk_image(extra: str = '') -> str:
    '''
    creates a temporary disk with gpt partition table por testing purposes
    '''
    from . import gptdsk
    # some random chars so disk image is unique for every test
    rnd = ''.join(random.choices('0123456789abcdef', k=4))
    filename = os.path.join(tempfile.gettempdir(), f'parted_test_disk_gpt_{rnd}{extra}.img')
    # if exists, remove it
    if os.path.exists(filename):
        os.remove(filename)
    with open(filename, 'wb') as f:
        f.write(gptdsk.disk())
    return filename

@contextlib.contextmanager
def create_empty_disk_image_ctx(size: int = 1<<20, delete_after: bool = True) -> typing.Iterator[str]:
    '''
    creates a temporary disk for testing purposes with the given size (defaults to 1 GiB)
    '''
    filename = create_empty_disk_image(size=size, extra=rnd_extra() if delete_after is False else '')
    try:
        yield filename
    finally:
        if delete_after:
            os.unlink(filename)
    
@contextlib.contextmanager
def create_msdos_disk_image_ctx(delete_after: bool = True) -> typing.Iterator[str]:
    '''
    creates a temporary disk with msdos partition table por testing purposes
    The disk has this structure:

        Boot Start   End Sectors Size Id Type
            2048    4095    2048   1M 83 Linux
            4096    8191    4096   2M 83 Linux
            8192   45055   36864  18M  5 Extended
            10240  16383    6144   3M  7 HPFS/NTFS/exFAT
            18432  26623    8192   4M 83 Linux

    Parted report these as this:
        Partition: -1 METADATA  Geometry(start=0, end=1, length=2)
        Partition: -1 FREESPACE  Geometry(start=2, end=2047, length=2046)
        Partition: 1 NORMAL  Geometry(start=2048, end=4095, length=2048)
        Partition: 2 NORMAL ext4 Geometry(start=4096, end=8191, length=4096)
        Partition: 3 EXTENDED  Geometry(start=8192, end=45055, length=36864)
        Partition: -1 LOGICAL_METADATA  Geometry(start=8192, end=8193, length=2)
        Partition: -1 LOGICAL_FREE  Geometry(start=8194, end=10199, length=2006)
        Partition: -1 LOGICAL_METADATA  Geometry(start=10200, end=10239, length=40)
        Partition: 5 LOGICAL ntfs Geometry(start=10240, end=16383, length=6144)
        Partition: -1 LOGICAL_FREE  Geometry(start=16384, end=18359, length=1976)
        Partition: -1 LOGICAL_METADATA  Geometry(start=18360, end=18431, length=72)
        Partition: 6 LOGICAL ext2 Geometry(start=18432, end=26623, length=8192)
        Partition: -1 LOGICAL_FREE  Geometry(start=26624, end=45055, length=18432)
        Partition: -1 FREESPACE  Geometry(start=45056, end=65279, length=20224)
        Partition: -1 METADATA  Geometry(start=65280, end=65535, length=256)
    '''
    filename = create_msdos_disk_image(extra=rnd_extra() if delete_after is False else '')
    try:
        yield filename
    finally:
        if delete_after:
            os.unlink(filename)

@contextlib.contextmanager
def create_gpt_disk_image_ctx(delete_after: bool = True) -> typing.Iterator[str]:
    '''
    creates a temporary disk with gpt partition table por testing purposes

    The disk has this structure:
        Start   End Sectors Size Type
         2048  4095    2048   1M Linux filesystem
         8192 14335    6144   3M Linux filesystem
        22528 32767   10240   5M Microsoft basic data

    Parted report these as this:
        Partition: -1 METADATA  Geometry(start=0, end=33, length=34)
        Partition: -1 FREESPACE  Geometry(start=34, end=2047, length=2014)
        Partition: 1 NORMAL  Geometry(start=2048, end=4095, length=2048)
        Partition: -1 FREESPACE  Geometry(start=4096, end=8191, length=4096)
        Partition: 2 NORMAL ext4 Geometry(start=8192, end=14335, length=6144)
        Partition: -1 FREESPACE  Geometry(start=14336, end=22527, length=8192)
        Partition: 3 NORMAL ntfs Geometry(start=22528, end=32767, length=10240)
        Partition: -1 FREESPACE  Geometry(start=32768, end=65502, length=32735)
        Partition: -1 METADATA  Geometry(start=65503, end=65535, length=33)

    '''
    filename = create_gpt_disk_image(extra=rnd_extra() if delete_after is False else '')
    try:
        yield filename
    finally:
        if delete_after:
            os.unlink(filename)
