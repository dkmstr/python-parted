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
This module contains the Constraint class, which is used to specify
the constraints on a Partition.

:author: Adolfo Gómez, dkmaster at dkmon dot com
"""
import logging
import enum
import typing

from . import _parted  # type: ignore
from . import alignment, device, exceptions, geom
from .util import ensure_obj, make_destroyable

if typing.TYPE_CHECKING:
    import cffi

logger = logging.getLogger(__name__)

class Constraint:
    """Wrapper for PedConstraint object

    This class represents a constraint on a partition.  A constraint
    is a set of rules that a partition must follow.  
    A constraint is composes of:
    - start_align: the alignment of the start of the partition
    - end_align: the alignment of the end of the partition
    - start_range: the range of the start of the partition
    - end_range: the range of the end of the partition
    - min_size: the minimum size of the partition
    - max_size: the maximum size of the partition

    From parted documentation::

        Constraints are used to communicate restrictions on operations Constraints
        are restrictions on the location and alignment of the start and end of a
        partition, and the minimum and maximum size.
        
        Constraints are closed under intersection (for the proof see the source
        code).  For background information see the Chinese Remainder Theorem.
        
        This interface consists of construction constraints, finding the intersection
        of constraints, and finding solutions to constraints.
        
        The constraint solver allows you to specify constraints on where a partition
        or file system (or any PedGeometry) may be placed/resized/etc. For example,
        you might want to make sure that a file system is at least 10 Gb, or that it
        starts at the beginning of new cylinder.
        
    """
    _constraint: typing.Any = None
    _destroyable: bool = True

    def __init__(
        self,
        constraint: typing.Optional['cffi.FFI.CData'] = None,
    ) -> None:
        """Creates a new constraint object

        Args:
            constraint (cffi.FFI.CData, optional): Underlying PedConstraint object. Defaults to None.
        """
        self._destroyable = False
        self._constraint = constraint if constraint else _parted.ffi.NULL

    def __del__(self) -> None:
        # Note: "init" method of library is not supported (nor needed in fact)
        # so we can safely destroy the constraint if destroyable
        if self._destroyable and self._constraint:
            _parted.lib.ped_constraint_destroy(self._constraint)

    def __bool__(self) -> bool:
        """Returns True if the constraint is valid, False otherwise

        Returns:
            bool: True if the constraint is valid, False otherwise
        """
        return bool(self._constraint)

    @property
    def obj(self) -> 'cffi.FFI.CData':
        """Wrapped ``PedConstraint*`` object"""
        return self._constraint

    @property
    def start_align(self) -> 'alignment.Alignment':
        """Returns the alignment of the start of the region.

        Returns:
            alignment.Alignment: The alignment of the start of the region.
        """
        if not self._constraint:
            return alignment.Alignment.none()
        return alignment.Alignment(self._constraint.start_align)

    @property
    def end_align(self) -> 'alignment.Alignment':
        """Returns the alignment of the end of the region.

        Returns:
            alignment.Alignment: The alignment of the end of the region.
        """
        if not self._constraint:
            return alignment.Alignment.none()
        return alignment.Alignment(self._constraint.end_align)

    @property
    def start_range(self) -> 'geom.Geometry':
        """Returns the start range of the constraint.

        Returns:
            geom.Geometry: The start range of the constraint.
        """
        if not self._constraint:
            return geom.Geometry(_parted.ffi.NULL)
        return geom.Geometry(self._constraint.start_range)

    @property
    def end_range(self) -> 'geom.Geometry':
        """Returns the end range of the constraint.

        Returns:
            geom.Geometry: The end range of the constraint.
        """
        if not self._constraint:
            return geom.Geometry(_parted.ffi.NULL)
        return geom.Geometry(self._constraint.end_range)

    @property
    def min_size(self) -> int:
        """Minimum size of the partition in bytes
        
        Returns:
            int: minimum size of the partition in bytes
        """
        if not self._constraint:
            return 0
        return self._constraint.min_size

    @property
    def max_size(self) -> int:
        """The max size of the constraint

        Returns:
            int: The max size of the constraint
        """
        if not self._constraint:
            return 0
        return self._constraint.max_size

    @ensure_obj
    def duplicate(self) -> 'Constraint':
        """Returns a new constraint that is a duplicate of this constraint.

        Returns:
            Constraint: A new constraint that is a duplicate of this constraint.

        Raises:
            exceptions.InvalidObjectError: if self is not a valid constraint
        """
        return make_destroyable(Constraint(_parted.lib.ped_constraint_duplicate(self._constraint)))

    @ensure_obj
    def intersect(self, constraint: 'Constraint') -> 'Constraint':
        """Returns a new constraint that is the intersection of this constraint and the given constraint.

        The intersection of two constraints is the largest constraint that is contained by both of them.
        This is calculated:
        - intersection of start_alignments. If no intersection, returns empty constraint
        - intersection of end_alignments. If no intersection, returns empty constraint
        - intersection of start_ranges. If no intersection, returns empty constraint
        - intersection of end_ranges. If no intersection, returns empty constraint
        - max of min_sizes
        - min of max_sizes

        Args:
            constraint (Constraint): The constraint to intersect with this constraint.

        Returns:
            Constraint: The intersection of this constraint and the given constraint.

        Raises:
            exceptions.InvalidObjectError: if self is not a valid constraint
        """
        return make_destroyable(Constraint(_parted.lib.ped_constraint_intersect(self._constraint, constraint.obj)))

    @ensure_obj
    def is_solution(self, geom: 'geom.Geometry') -> bool:
        """Check whether geom satisfies the given constraint.
        Will satisfied it if:
        - geom.start is aligned to start_align
        - geom.end is aligned to end_align
        - geom.start is in start_range
        - geom.end is in end_range
        - geom.length is in the range [min_size, max_size]
        
        Args:
            geom (geom.Geometry): The geometry to check

        Returns:
            bool: True if geom satisfies the given constraint, False otherwise

        Raises:
            exceptions.InvalidObjectError: if self is not a valid constraint
        """
        return bool(_parted.lib.ped_constraint_is_solution(self._constraint, geom.obj))

    @ensure_obj
    def solve_max(self) -> 'geom.Geometry':
        """Find the largest region that satisfies a constraint.

        Returns:
            geom.Geometry: The largest region that satisfies the constraint.

        Raises:
            exceptions.InvalidObjectError: if self is not a valid constraint
        """
        return geom.Geometry(_parted.lib.ped_constraint_solve_max(self._constraint))

    @ensure_obj
    def solve_nearest(self, geometry: 'geom.Geometry') -> 'geom.Geometry':
        """Return the nearest region to geometry that satisfy a constraint.

        This is the region that, if geometry is moved to it, geometry will be as close as possible to the
        original geometry, and still satisfy the constraint.

        Args:
            geometry (geom.Geometry): The geometry to solve

        Returns:
            geom.Geometry: The nearest geometry that satisfies the constraint

        Raises:
            exceptions.InvalidObjectError: if self is not a valid constraint

        """
        return geom.Geometry(_parted.lib.ped_constraint_solve_nearest(self._constraint, geometry.obj))

    @staticmethod
    def any(dev: 'device.Device') -> 'Constraint':
        """Return a constraint that any region on the given device will satisfy.
            - start_align = aligment.Alignment.any()
            - end_align = aligment.Alignment.any()
            - start_range = geom.Geometry(0, dev.length)
            - end_range = geom.Geometry(0, dev.length)
            - min_size = 1
            - max_size = dev.length

        Args:
            dev (device.Device): The device to create the constraint for

        Returns:
            Constraint: A constraint that any region on the given device will satisfy.

        """
        if not dev:
            return Constraint()
        return make_destroyable(Constraint(_parted.lib.ped_constraint_any(dev.obj)))

    @staticmethod
    def exact(geom: 'geom.Geometry') -> 'Constraint':
        """Return a constraint that only the given region will satisfy.
            - start_align = alignment.Alignment(geom.start, 0)
            - end_align = alignment.Alignment(geom.end, 0)
            - start_range = geom.Geometry(geom.start, 1)
            - end_range = geom.Geometry(geom.end, 1)

        Args:
            geom (geom.Geometry): The geometry to constrain to.

        Returns:
            Constraint: A constraint that only the given region will satisfy.
        """
        return make_destroyable(Constraint(_parted.lib.ped_constraint_exact(geom.obj)))

    @staticmethod
    def align(dev: 'device.Device', align: int) -> 'Constraint':
        """Return a constraint that will enforce an alignment on the start and end of a region.
            - start_align = alignment.Alignment(boundary, 0)
            - end_align = alignment.Alignment(boundary, 0)
            - start_range = geom.Geometry(0, dev.length)
            - end_range = geom.Geometry(0, dev.length)

        Args:
            dev (device.Device): The device to create the constraint for
            alignment (int): The alignment boundary in Kbytes. will be rounded up to the nearest multiple of dev.sector_size

        Returns:
            Constraint: A constraint that will enforce an alignment on the start and end of a region.

        Examples:
            >>> import parted
            >>> dev = parted.getDevice('/dev/sda')
            >>> constraint = parted.Constraint.bound(dev, 1<<10)  # 1 MiB
            
        """
        # Ensure boundary is multiple of dev.sector_size, and convert to sectors
        align = (align * 1024 + dev.sector_size - 1) // dev.sector_size
        return Constraint.new(
            start_align=alignment.Alignment(0, align),
            end_align=alignment.Alignment(-1, align),
            start_range=geom.Geometry(dev, 0, dev.length),
            end_range=geom.Geometry(dev, 0, dev.length),
            min_size_sector = align,
            max_size_sector = dev.length
        )

    @staticmethod
    def new(
        start_align: 'alignment.Alignment',
        end_align: 'alignment.Alignment',
        start_range: 'geom.Geometry',
        end_range: 'geom.Geometry',
        min_size_sector: int,
        max_size_sector: int,
    ) -> 'Constraint':
        """Create a new constraint.

        Args:
            start_align (alignment.Alignment): The alignment of the start of the region.
            end_align (alignment.Alignment): The alignment of the end of the region.
            start_range (geom.Geometry): The range of the start of the region.
            end_range (geom.Geometry): The range of the end of the region.
            min_size (int): The minimum size of the region.
            max_size (int): The maximum size of the region.

        Returns:
            Constraint: A newly created contraint object.
        """
        # Sanity checks
        if min_size_sector <= 0:
            raise exceptions.PartedException('Invalid min_size (must be > 0)')

        if max_size_sector <= 0:
            raise exceptions.PartedException('Invalid max_size (must be > 0)')

        return make_destroyable(
            Constraint(
                _parted.lib.ped_constraint_new(
                    start_align.obj,
                    end_align.obj,
                    start_range.obj,
                    end_range.obj,
                    min_size_sector,
                    max_size_sector,
                )
            )
        )

    @staticmethod
    def new_from_min(min: 'geom.Geometry') -> 'Constraint':
        """Return a constraint that requires a region to entirely contain min.

        Args:
            min (geom.Geometry): The geometry to constrain to.

        Returns:
            Constraint: A constraint that requires a region to entirely contain min.
        """
        return make_destroyable(Constraint(_parted.lib.ped_constraint_new_from_min(min.obj)))

    @staticmethod
    def new_from_min_max(min: 'geom.Geometry', max: 'geom.Geometry') -> 'Constraint':
        """Return a constraint that requires a region to be entirely contained inside max, and to entirely contain min.

        Args:
            min (geom.Geometry): The minimum geometry to constrain to.
            max (geom.Geometry): The maximum geometry to constrain to.

        Returns:
            Constraint: The constraint.

        """
        # if min is not inside max, raise exceptions.PartedException
        if not min in max:
            raise exceptions.PartedException("min is not inside max, min: {}, max: {}".format(min, max))
        return make_destroyable(
            Constraint(
                _parted.lib.ped_constraint_new_from_min_max(min.obj, max.obj),
            )
        )

    @staticmethod
    def new_from_max(max: 'geom.Geometry') -> 'Constraint':
        """Return a constraint that requires a region to be entirely contained inside max.

        Args:
            max (geom.Geometry): The geometry to constrain to.

        Returns:
            Constraint: The new created constraint.
        """
        return make_destroyable(Constraint(_parted.lib.ped_constraint_new_from_max(max.obj)))

    def __str__(self) -> str:
        return 'Constraint({}, {}, {}, {}, {}, {})'.format(
            self.start_align, self.end_align, self.start_range, self.end_range, self.min_size, self.max_size
        )

    def __repr__(self) -> str:
        return self.__str__()
