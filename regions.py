"""
regions.py
==========

Geometric region definitions for the DORT preparation API.

A Region describes a physical rectangular area in R-Z space using readable
material names. It does not assign DORT IDs itself. Its main responsibility is
to generate a Boolean mask over a Mesh.

The convention used throughout the API is

    mask.shape == (nz, nr)

so axis 0 corresponds to Z and axis 1 corresponds to R.

Example
-------
from mesh import Mesh
from regions import Region

mesh = Mesh()
mesh.r.add_segment(0.0, 200.0, step=10.0)
mesh.z.add_segment(-100.0, 100.0, step=10.0)

core = Region(
    name="core",
    material="Core",
    r=(0.0, 100.0),
    z=(-50.0, 50.0),
    priority=20,
)

mask = core.mask(mesh)

print(mask.shape)
print(mask.sum())
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

import numpy as np

from mesh import Mesh


@dataclass(frozen=True)
class Region:
    """
    Rectangular region in cylindrical R-Z geometry.

    Parameters
    ----------
    name
        Unique human-readable region name.
    material
        Name of the material assigned to the region.
    r
        Radial bounds ``(r_min, r_max)``.
    z
        Axial bounds ``(z_min, z_max)``.
    priority
        Integer priority used later when several regions overlap.
        Higher-priority regions will normally overwrite lower-priority ones.
    enabled
        Disabled regions remain defined but produce an empty mask.
    description
        Optional explanatory text.

    Notes
    -----
    Region membership is based on mesh-cell centres:

        r_min <= r_center < r_max
        z_min <= z_center < z_max

    The upper bound is exclusive. This avoids double-counting cells when two
    adjacent regions share a boundary.
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
        return self.r[0]

    @property
    def r_max(self) -> float:
        return self.r[1]

    @property
    def z_min(self) -> float:
        return self.z[0]

    @property
    def z_max(self) -> float:
        return self.z[1]

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        """
        Return ``(r_min, r_max, z_min, z_max)``.
        """
        return self.r_min, self.r_max, self.z_min, self.z_max

    def mask(self, mesh: Mesh) -> np.ndarray:
        """
        Return a Boolean mask identifying cells belonging to this region.

        Parameters
        ----------
        mesh
            Valid R-Z mesh.

        Returns
        -------
        numpy.ndarray
            Boolean array of shape ``(nz, nr)``.
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
        """Return the number of mesh cells selected by the region."""
        return int(np.count_nonzero(self.mask(mesh)))

    def intersects_mesh(self, mesh: Mesh) -> bool:
        """
        Return True if the geometric region overlaps the mesh domain.

        This tests geometric bounds, not cell-centre selection.
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
        """Return True if the entire region lies inside the mesh domain."""
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
        """
        Return True if two geometric regions have a non-zero-area overlap.

        Merely touching at a shared boundary does not count as overlap.
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
    """
    Ordered collection of uniquely named regions.

    The registry stores regions in insertion order. Final priority processing
    will be performed later by the DORTModel/build module.
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
        """
        Create, register, and return a Region.
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
        """Return a region by name."""
        try:
            return self._regions[name]
        except KeyError as exc:
            raise KeyError(
                f"Region {name!r} is not registered."
            ) from exc

    def remove(self, name: str) -> Region:
        """Remove and return a region."""
        try:
            return self._regions.pop(name)
        except KeyError as exc:
            raise KeyError(
                f"Region {name!r} is not registered."
            ) from exc

    @property
    def names(self) -> tuple[str, ...]:
        """Region names in insertion order."""
        return tuple(self._regions.keys())

    @property
    def regions(self) -> tuple[Region, ...]:
        """Region objects in insertion order."""
        return tuple(self._regions.values())

    def sorted_by_priority(self) -> tuple[Region, ...]:
        """
        Return enabled regions ordered from low to high priority.

        Python's stable sort preserves insertion order among regions having
        equal priority. Equal-priority overlaps will be checked explicitly by
        the model builder rather than silently relying on this order.
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
        """Remove all regions."""
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
