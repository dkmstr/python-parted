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
This module contains the Alignment class.

The alignment class is used to specify the alignment of a partition.
It's a wrapper for the PedAlignment struct. and related functions.

:author: Adolfo Gómez, dkmaster at dkmon dot com
"""
import typing

from . import _parted  # type: ignore

from .util import ensure_obj, make_destroyable, ensure_obj_or_default

from . import geom

if typing.TYPE_CHECKING:
    from . import geom
    import cffi


class Alignment:
    """Aligment wrapper

    This class wraps the PedAlignment object, and provides a more pythonic interface to itself.
    """

    _alignment: typing.Any
    _destroyable: bool

    def __init__(
        self, alignment_or_offset: typing.Union[int, 'cffi.FFI.CData', None], grain_size: int = 0
    ) -> None:
        """Creates an alignment object

        Args:
            alignment_or_offset (typing.Union[int, "cffi.FFI.CData"]): If an int, it's the offset, if a CData, it's the PedAlignment* object
            grain_size (int, optional): Grain size of the aligment. Defaults to 0. (Only used if offset is an int)

        Note:
            If alignment_or_offset is an int, it&#39;s the offset, a new parted PedAlignment will be created with that offset and grain_size
            If alignment_or_offset is a CData, it&#39;s the PedAlignment, and it will be used as is
        """
        if isinstance(alignment_or_offset, int) and alignment_or_offset is not False:
            self._alignment = _parted.lib.ped_alignment_new(alignment_or_offset, grain_size)
            self._destroyable = True
        else:
            self._alignment = alignment_or_offset if alignment_or_offset else _parted.ffi.NULL
            self._destroyable = False

    def __del__(self) -> None:
        """Destroys the alignment object

        Ensures that the alignment object is destroyed if it's destroyable
        """
        if self._destroyable and self._alignment:
            _parted.lib.ped_alignment_destroy(self._alignment)
            self._alignment = _parted.ffi.NULL

    def __bool__(self) -> bool:
        """Returns True if the alignment is valid, False otherwise"""
        return bool(self._alignment)

    def __eq__(self, other: typing.Any) -> bool:
        """Compares two alignments. Returns True if they are equal, False otherwise"""
        if isinstance(other, Alignment):
            return self.offset == other.offset and self.grain_size == other.grain_size
        return False

    @ensure_obj
    def __xor__(self, other: 'Alignment') -> 'Alignment':
        """
        Returns the alignment that is the result of the intersect operation between this alignment and the other one
        """
        return self.intersect(other)

    @property
    def obj(self) -> 'cffi.FFI.CData':
        """Wrapped ``PedAlignment*`` object"""
        return self._alignment

    @property  # type: ignore  # mypy does not likes decorated properties
    @ensure_obj_or_default(0)
    def offset(self) -> int:
        """Wrapped alignment offset

        Returns:
            int: The offset of the alignment
        """
        return self._alignment.offset

    @property  # type: ignore  # mypy does not likes decorated properties
    @ensure_obj_or_default(0)
    def grain_size(self) -> int:
        """Wrapped alignment grain size

        Returns:
            int: The grain size of the alignment
        """
        return self._alignment.grain_size

    @ensure_obj
    def init(self, offset: int, grain_size: int) -> None:
        """Initializes an already created alignment object

        Args:
            offset (int): The offset
            grain_size (int): The grain size

        Raises:
            exceptions.InvalidObjectError: If the wrapped alignment is not valid
        """
        _parted.lib.ped_alignment_init(self._alignment, offset, grain_size)

    @ensure_obj_or_default(lambda: Alignment(None))
    def duplicate(self) -> 'Alignment':
        """Generates a Duplicated self.

        This is an independent copy of the alignment, that can be manipulated without affecting the original one.

        Returns:
            Alignment: An Aligment with a duplicate of our managed PEDAlignment object
        """
        return make_destroyable(Alignment(_parted.lib.ped_alignment_duplicate(self._alignment)))

    @ensure_obj
    def intersect(self, other: 'Alignment') -> 'Alignment':
        """Intersect operation between self alignment and the other one.

        The intersect operation is the alignment that complies with both alignments.

        Args:
            other (Alignment): The other alignment

        Returns:
            Alignment: The resulting alignment

        Raises:
            exceptions.InvalidObjectError: If the wrapped alignment is not valid
        """
        return make_destroyable(
            Alignment(_parted.lib.ped_alignment_intersect(self._alignment, other._alignment))
        )

    @ensure_obj
    def align_up(self, geometry: 'geom.Geometry', sector: int) -> int:
        """Returns the closest sector to sector that lies inside geom that satisfies self aligment.

        Args:
            geometry (geom.Geometry): The geometry that contains the sector to align
            sector (int): The sector to align

        Returns:
            int: _description_

        Raises:
            exceptions.InvalidObjectError: If the wrapped alignment is not valid
        """
        return _parted.lib.ped_alignment_align_up(self._alignment, geometry.obj, sector)

    @ensure_obj
    def align_down(self, geometry: 'geom.Geometry', sector: int) -> int:
        """Returns the closest sector to sector that lies inside geom that satisfies the given alignment constraint align.

        Args:
            geometry (geom.Geometry): The geometry that contains the sector to align
            sector (int): the sector to align

        Returns:
            int: The aligned sector

        Raises:
            exceptions.InvalidObjectError: If the wrapped alignment is not valid
        """
        return _parted.lib.ped_alignment_align_down(self._alignment, geometry.obj, sector)

    @ensure_obj
    def align_nearest(self, geometry: 'geom.Geometry', sector: int) -> int:
        """Returns the sector that is closest to sector, satisfies the align constraint and lies inside geom.

        Args:
            geometry (geom.Geometry): The geometry that contains the sector to align
            sector (int): the sector to align

        Returns:
            int: The aligned sector

        Raises:
            exceptions.InvalidObjectError: If the wrapped alignment is not valid
        """
        return _parted.lib.ped_alignment_align_nearest(self._alignment, geometry.obj, sector)

    @ensure_obj
    def is_aligned(self, geometry: 'geom.Geometry', sector: int) -> bool:
        """
        This function returns True if sector satisfies the alignment constraint align and lies inside geom.

        Args:
            geometry (geom.Geometry): The geometry that contains the sector to check if it is aligned
            sector (int): the sector to check if it is aligned

        Returns:
            bool: _description_

        Raises:
            exceptions.InvalidObjectError: If the wrapped alignment is not valid
        """
        return bool(_parted.lib.ped_alignment_is_aligned(self._alignment, geometry.obj, sector))

    @staticmethod
    def new(offset: int, grain_size: int) -> 'Alignment':
        """
        Return an alignment object (used by PedConstraint), representing all PedSector's that are of the form offset + X * grain_size.

        Args:
            offset (int): The offset
            grain_size (int): The grain size

        Returns:
            Alignment: The alignment object
        """
        return make_destroyable(Alignment(_parted.lib.ped_alignment_new(offset, grain_size)))

    @staticmethod
    def any() -> 'Alignment':
        """
        Return an alignment object that represents all PedSector's. (that is, offset=0, grain_size=1)

        Returns:
            Alignment: _description_
        """
        return Alignment(_parted.lib.ped_alignment_any)

    @staticmethod
    def none() -> 'Alignment':
        """
        Return an alignment object that represents no PedSector's. (that is, offset=0, grain_size=0)

        Returns:
            Alignment: _description_
        """
        return Alignment(_parted.lib.ped_alignment_none)

    def __str__(self) -> str:
        """
        Returns a string representation of the alignment

        Returns:
            str: The string representation of the alignment
        """
        return f'Alignment(offset={self.offset}, grain_size={self.grain_size})'

    def __repr__(self) -> str:
        """
        Returns a string representation of the alignment

        Returns:
            str: The string representation of the alignment
        """
        return self.__str__()
