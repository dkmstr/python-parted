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
Parted exceptions

This module contains all the exceptions that can be raised by python-parted

:author: Adolfo Gómez, dkmaster at dkmon dot com

Note:
            This exceptions are not reised by parted directly, but by the python
            wrapper. 
"""
import typing

class PartedException(Exception):
    """Base exception for parted module

    Args:
        message (str): Message to show
    """
    pass

class InvalidObjectError(PartedException):
    """Underlying object (wrapped Ped*) is not valid

    Args:
        message (str): Message to show
    """
    pass

class InvalidDeviceError(PartedException):
    """Device is not valid
    """
    pass

class InvalidDiskError(PartedException):
    """Disk is not valid
    """
    pass

class InvalidDiskTypeError(PartedException):
    """Disk type is not valid
    """
    pass

class InvalidPartitionError(PartedException):
    """Partition is not valid
    """
    pass

class InvalidFileSystemError(PartedException):
    """File system is not valid
    """
    pass

class CheckError(PartedException):
    """Check failed

    Args:
        errors (list): List of errors
    
    """
    def __init__(self, errors: typing.List[str]) -> None:
        super().__init__(*errors)

    def errors(self) -> typing.List[str]:
        """Returns the list of errors

        Returns:
            typing.List[str]: List of errors
        """
        return typing.cast(typing.List[str], self.args)

class NotOpenedError(PartedException):
    """Device is closed and an operation is requested
    """
    pass

class IOError(PartedException):
    """
    Exception raised when an IO error occurs
    """
    pass

class ReadOnlyError(IOError):
    """
    Exception raised when a write error occurs
    """
    pass
