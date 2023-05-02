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
