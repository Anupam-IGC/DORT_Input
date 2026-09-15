"""Geometric region definitions for DORT R-Z input preparation.

A region describes a rectangular physical area in cylindrical R-Z space using
a readable material name. Region objects generate Boolean masks over a
:class:`mesh.Mesh`; material-ID assignment is performed later by
:class:`model.DORTModel`.

All masks use shape ``(nz, nr)``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

import numpy as np

from mesh import Mesh


@dataclass(frozen=True)
class Region:
    """Represent a rectangular region in cylindrical R-Z geometry.
    
    Parameters
    ----------
    name : str
        Unique region name.
    material : str
        Name of the material assigned to the region.
    r : tuple of float
        Radial bounds ``(r_min, r_max)``.
    z : tuple of float
        Axial bounds ``(z_min, z_max)``.
    priority : int, optional
        Overwrite priority. Higher-priority regions overwrite lower-priority
        regions during model construction.
    enabled : bool, optional
        If ``False``, the region remains registered but selects no cells.
    description : str, optional
        Free-text description.
    
    Raises
    ------
    TypeError
        If ``priority`` is not an integer or ``enabled`` is not Boolean.
    ValueError
        If names/bounds are invalid, radial lower bound is negative, or a maximum
        bound is not greater than its corresponding minimum.
    
    Notes
    -----
    Cell membership is centre-based and half-open:
    
    ``r_min <= r_center < r_max`` and
    ``z_min <= z_center < z_max``.
    
    The exclusive upper bound prevents double assignment at shared boundaries.
    """

    name: str
    material: str
    r: tuple[float, float]
    z: tuple[float, float]
    priority: int = 0
    enabled: bool = True
    description: str = ""

    def __post_init__(self) -> None:
        name = str(self.name).strip()
        material = str(self.material).strip()
        description = str(self.description).strip()

        if not name:
            raise ValueError("Region name cannot be empty.")

        if not material:
            raise ValueError(
                f"Region {name!r}: material name cannot be empty."
            )

        if len(self.r) != 2:
            raise ValueError(
                f"Region {name!r}: r must contain exactly two values."
            )

        if len(self.z) != 2:
            raise ValueError(
                f"Region {name!r}: z must contain exactly two values."
            )

        r_min, r_max = map(float, self.r)
        z_min, z_max = map(float, self.z)

        if not np.all(np.isfinite([r_min, r_max, z_min, z_max])):
            raise ValueError(
                f"Region {name!r}: all bounds must be finite."
            )

        if r_min < 0.0:
            raise ValueError(
                f"Region {name!r}: radial lower bound cannot be negative."
            )

        if r_max <= r_min:
            raise ValueError(
                f"Region {name!r}: r_max must be greater than r_min."
            )

        if z_max <= z_min:
            raise ValueError(
                f"Region {name!r}: z_max must be greater than z_min."
            )

        if isinstance(self.priority, bool) or not isinstance(self.priority, int):
            raise TypeError(
                f"Region {name!r}: priority must be an integer."
            )

        if not isinstance(self.enabled, bool):
            raise TypeError(
                f"Region {name!r}: enabled must be True or False."
            )

        object.__setattr__(self, "name", name)
        object.__setattr__(self, "material", material)
        object.__setattr__(self, "r", (r_min, r_max))
        object.__setattr__(self, "z", (z_min, z_max))
        object.__setattr__(self, "description", description)

    @property
    def r_min(self) -> float:
        """Return the lower radial bound.
        
        Returns
        -------
        float
            Minimum R coordinate.
        """
        return self.r[0]

    @property
    def r_max(self) -> float:
        """Return the upper radial bound.
        
        Returns
        -------
        float
            Maximum R coordinate.
        """
        return self.r[1]

    @property
    def z_min(self) -> float:
        """Return the lower axial bound.
        
        Returns
        -------
        float
            Minimum Z coordinate.
        """
        return self.z[0]

    @property
    def z_max(self) -> float:
        """Return the upper axial bound.
        
        Returns
        -------
        float
            Maximum Z coordinate.
        """
        return self.z[1]

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        """Return all region bounds.
        
        Returns
        -------
        tuple of float
            ``(r_min, r_max, z_min, z_max)``.
        """
        return self.r_min, self.r_max, self.z_min, self.z_max

    def mask(self, mesh: Mesh) -> np.ndarray:
        """Return the mesh-cell mask selected by the region.
        
        Parameters
        ----------
        mesh : Mesh
            Valid R-Z mesh on which region membership is evaluated.
        
        Returns
        -------
        numpy.ndarray
            Boolean array with shape ``(nz, nr)``.
        
        Raises
        ------
        ValueError
            If the supplied mesh is invalid.
        
        Notes
        -----
        Membership is evaluated using mesh-cell centres rather than fractional
        geometric intersection.
        """
        mesh.validate()

        if not self.enabled:
            return np.zeros(mesh.shape, dtype=bool)

        r_centers = mesh.r.centers
        z_centers = mesh.z.centers

        r_mask = (
            (r_centers >= self.r_min)
            & (r_centers < self.r_max)
        )

        z_mask = (
            (z_centers >= self.z_min)
            & (z_centers < self.z_max)
        )

        # Outer product of the two 1-D masks.
        return z_mask[:, np.newaxis] & r_mask[np.newaxis, :]

    def n_cells(self, mesh: Mesh) -> int:
        """Return the number of mesh cells selected by the region.
        
        Parameters
        ----------
        mesh : Mesh
            Valid R-Z mesh.
        
        Returns
        -------
        int
            Number of ``True`` entries in :meth:`mask`.
        """
        return int(np.count_nonzero(self.mask(mesh)))

    def intersects_mesh(self, mesh: Mesh) -> bool:
        """Test whether the geometric region intersects the mesh domain.
        
        Parameters
        ----------
        mesh : Mesh
            Valid R-Z mesh.
        
        Returns
        -------
        bool
            ``True`` when the continuous region bounds overlap the mesh bounds.
        
        Notes
        -----
        This is a geometric-bounds test; it does not guarantee that any cell centre is
        selected.
        """
        mesh.validate()

        r_lo, r_hi = mesh.r.bounds
        z_lo, z_hi = mesh.z.bounds

        radial_overlap = (
            self.r_max > r_lo
            and self.r_min < r_hi
        )

        axial_overlap = (
            self.z_max > z_lo
            and self.z_min < z_hi
        )

        return radial_overlap and axial_overlap

    def is_within_mesh(self, mesh: Mesh) -> bool:
        """Test whether the full region lies inside the mesh domain.
        
        Parameters
        ----------
        mesh : Mesh
            Valid R-Z mesh.
        
        Returns
        -------
        bool
            ``True`` when all four region bounds lie within the corresponding mesh
            bounds.
        """
        mesh.validate()

        r_lo, r_hi = mesh.r.bounds
        z_lo, z_hi = mesh.z.bounds

        return (
            self.r_min >= r_lo
            and self.r_max <= r_hi
            and self.z_min >= z_lo
            and self.z_max <= z_hi
        )

    def overlaps(self, other: "Region") -> bool:
        """Test whether two regions have a non-zero-area geometric overlap.
        
        Parameters
        ----------
        other : Region
            Region to compare with this region.
        
        Returns
        -------
        bool
            ``True`` when radial and axial intervals overlap with non-zero extent.
        
        Notes
        -----
        Regions that only touch at a common boundary are not considered overlapping.
        """
        radial_overlap = (
            self.r_min < other.r_max
            and self.r_max > other.r_min
        )

        axial_overlap = (
            self.z_min < other.z_max
            and self.z_max > other.z_min
        )

        return radial_overlap and axial_overlap

    def __repr__(self) -> str:
        return (
            f"Region(name={self.name!r}, material={self.material!r}, "
            f"r={self.r}, z={self.z}, priority={self.priority}, "
            f"enabled={self.enabled})"
        )


class RegionRegistry:
    """Store uniquely named regions in insertion order.
    
    Priority sorting is intentionally separate from insertion order. Equal-priority
    cell overlaps are rejected later by :class:`model.DORTModel`.
    """

    def __init__(self) -> None:
        self._regions: dict[str, Region] = {}

    def add(
        self,
        name: str,
        *,
        material: str,
        r: tuple[float, float],
        z: tuple[float, float],
        priority: int = 0,
        enabled: bool = True,
        description: str = "",
    ) -> Region:
        """Create and register a rectangular region.
        
        Parameters
        ----------
        name : str
            Unique region name.
        material : str
            Registered material name to be assigned later by the model.
        r : tuple of float
            Radial bounds ``(r_min, r_max)``.
        z : tuple of float
            Axial bounds ``(z_min, z_max)``.
        priority : int, optional
            Overwrite priority.
        enabled : bool, optional
            Whether the region participates in model building.
        description : str, optional
            Free-text description.
        
        Returns
        -------
        Region
            Newly registered immutable region.
        
        Raises
        ------
        ValueError
            If ``name`` is already registered or if the Region definition is invalid.
        TypeError
            If Region type constraints are violated.
        """
        clean_name = str(name).strip()

        if clean_name in self._regions:
            raise ValueError(
                f"Region {clean_name!r} already exists."
            )

        region = Region(
            name=clean_name,
            material=material,
            r=r,
            z=z,
            priority=priority,
            enabled=enabled,
            description=description,
        )

        self._regions[region.name] = region
        return region

    def get(self, name: str) -> Region:
        """Return a region by name.
        
        Parameters
        ----------
        name : str
            Registered region name.
        
        Returns
        -------
        Region
            Matching region.
        
        Raises
        ------
        KeyError
            If no such region is registered.
        """
        try:
            return self._regions[name]
        except KeyError as exc:
            raise KeyError(
                f"Region {name!r} is not registered."
            ) from exc

    def remove(self, name: str) -> Region:
        """Remove a region by name.
        
        Parameters
        ----------
        name : str
            Registered region name.
        
        Returns
        -------
        Region
            Removed region.
        
        Raises
        ------
        KeyError
            If no such region is registered.
        """
        try:
            return self._regions.pop(name)
        except KeyError as exc:
            raise KeyError(
                f"Region {name!r} is not registered."
            ) from exc

    @property
    def names(self) -> tuple[str, ...]:
        """Return region names in insertion order.
        
        Returns
        -------
        tuple of str
            Registered names.
        """
        return tuple(self._regions.keys())

    @property
    def regions(self) -> tuple[Region, ...]:
        """Return region objects in insertion order.
        
        Returns
        -------
        tuple of Region
            Registered regions.
        """
        return tuple(self._regions.values())

    def sorted_by_priority(self) -> tuple[Region, ...]:
        """Return enabled regions ordered from low to high priority.
        
        Returns
        -------
        tuple of Region
            Stable priority-sorted sequence.
        
        Notes
        -----
        Python's stable sort preserves insertion order among equal-priority regions,
        but the model builder explicitly rejects equal-priority overlaps instead of
        using that order to resolve them.
        """
        return tuple(
            sorted(
                (
                    region
                    for region in self._regions.values()
                    if region.enabled
                ),
                key=lambda region: region.priority,
            )
        )

    def clear(self) -> None:
        """Remove all registered regions.
        
        Returns
        -------
        None
        """
        self._regions.clear()

    def __contains__(self, name: str) -> bool:
        return name in self._regions

    def __getitem__(self, name: str) -> Region:
        return self.get(name)

    def __iter__(self) -> Iterator[Region]:
        return iter(self._regions.values())

    def __len__(self) -> int:
        return len(self._regions)

    def __repr__(self) -> str:
        content = ", ".join(
            f"{region.name}:{region.material}@{region.priority}"
            for region in self._regions.values()
        )

        return f"RegionRegistry({{{content}}})"


if __name__ == "__main__":
    # Small demonstration / smoke test.
    mesh = Mesh()

    mesh.r.add_segment(0.0, 200.0, step=10.0)
    mesh.z.add_segment(-100.0, 100.0, step=10.0)

    regions = RegionRegistry()

    core = regions.add(
        "core",
        material="Core",
        r=(0.0, 100.0),
        z=(-50.0, 50.0),
        priority=20,
    )

    shield = regions.add(
        "radial_shield",
        material="SS316",
        r=(100.0, 140.0),
        z=(-50.0, 50.0),
        priority=30,
    )

    penetration = regions.add(
        "penetration",
        material="Air",
        r=(80.0, 120.0),
        z=(-10.0, 10.0),
        priority=50,
    )

    print(regions)
    print()
    print("Core mask shape :", core.mask(mesh).shape)
    print("Core cell count :", core.n_cells(mesh))
    print("Shield cells    :", shield.n_cells(mesh))
    print("Penetration     :", penetration.n_cells(mesh))
    print()
    print("Core inside mesh:", core.is_within_mesh(mesh))
    print("Core/shield geometric overlap:", core.overlaps(shield))
    print("Core/penetration overlap     :", core.overlaps(penetration))
    print()
    print("Priority order:")
    for region in regions.sorted_by_priority():
        print(
            f"  {region.priority:3d}  "
            f"{region.name:16s} -> {region.material}"
        )
