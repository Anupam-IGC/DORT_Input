"""
model.py
========

Central model object for the DORT preparation API.

This module combines:

    mesh.py       -> Mesh / MeshAxis
    materials.py  -> Material / MaterialRegistry
    regions.py    -> Region / RegionRegistry

Its main responsibility is to build the final R-Z material filling map.

The array convention used throughout is:

    shape = (nz, nr)

so axis 0 is Z and axis 1 is R.

Example
-------
from model import DORTModel

model = DORTModel("example")

model.add_material("Sodium")
model.add_material("Core")
model.add_material("SS316")
model.add_material("Air")

model.mesh.r.add_segment(0.0, 200.0, step=10.0)
model.mesh.z.add_segment(-100.0, 100.0, step=10.0)

model.set_background("Sodium")

model.add_region(
    "core",
    material="Core",
    r=(0.0, 100.0),
    z=(-50.0, 50.0),
    priority=20,
)

model.add_region(
    "radial_shield",
    material="SS316",
    r=(100.0, 140.0),
    z=(-50.0, 50.0),
    priority=30,
)

model.add_region(
    "penetration",
    material="Air",
    r=(80.0, 120.0),
    z=(-10.0, 10.0),
    priority=50,
)

model.build()

print(model.material_id_map)
print(model.material_name_map)
print(model.region_map)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

import numpy as np

from mesh import Mesh
from materials import Material, MaterialRegistry
from regions import Region, RegionRegistry


@dataclass(frozen=True)
class BuildSummary:
    """
    Small immutable summary returned after a successful build.
    """

    model_name: str
    shape: tuple[int, int]
    n_cells: int
    n_materials: int
    n_regions: int
    background_material: str | None
    warnings: tuple[str, ...] = ()

    def __repr__(self) -> str:
        return (
            f"BuildSummary(model={self.model_name!r}, "
            f"shape={self.shape}, "
            f"cells={self.n_cells}, "
            f"materials={self.n_materials}, "
            f"regions={self.n_regions}, "
            f"background={self.background_material!r}, "
            f"warnings={len(self.warnings)})"
        )


class DORTModel:
    """
    Central user-facing model object.

    Parameters
    ----------
    name
        Human-readable model name.

    Notes
    -----
    ``DORTModel`` deliberately does not yet know how to write DORT input
    syntax. It only constructs and validates a material-filled R-Z mesh.
    A separate writer module will later translate these maps to DORT format.
    """

    def __init__(self, name: str = "DORT_model") -> None:
        clean_name = str(name).strip()

        if not clean_name:
            raise ValueError("Model name cannot be empty.")

        self.name = clean_name

        self.mesh = Mesh()
        self.materials = MaterialRegistry()
        self.regions = RegionRegistry()

        self._background_material: str | None = None

        self._material_id_map: np.ndarray | None = None
        self._material_name_map: np.ndarray | None = None
        self._region_map: np.ndarray | None = None
        self._priority_map: np.ndarray | None = None

        self._warnings: list[str] = []

    # ------------------------------------------------------------------
    # Material convenience API
    # ------------------------------------------------------------------

    def add_material(
        self,
        name: str,
        *,
        dort_id: int | None = None,
        description: str = "",
    ) -> Material:
        """
        Add a material to the model and return it.
        """
        return self.materials.add(
            name,
            dort_id=dort_id,
            description=description,
        )

    # ------------------------------------------------------------------
    # Region convenience API
    # ------------------------------------------------------------------

    def add_region(
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
        Add a rectangular R-Z region and return it.
        """
        return self.regions.add(
            name,
            material=material,
            r=r,
            z=z,
            priority=priority,
            enabled=enabled,
            description=description,
        )

    # ------------------------------------------------------------------
    # Background material
    # ------------------------------------------------------------------

    @property
    def background_material(self) -> str | None:
        """Name of the current background material."""
        return self._background_material

    def set_background(self, material: str) -> None:
        """
        Set the material used to initially fill the entire mesh.

        The material must already be registered.
        """
        material = str(material).strip()

        if material not in self.materials:
            raise KeyError(
                f"Cannot set background material to {material!r}: "
                "it is not registered."
            )

        self._background_material = material

    def clear_background(self) -> None:
        """
        Remove the background material.

        With no background, every cell must later be filled by an explicit
        region or ``build()`` will fail unless ``allow_unfilled=True``.
        """
        self._background_material = None

    # ------------------------------------------------------------------
    # Built-map properties
    # ------------------------------------------------------------------

    @property
    def is_built(self) -> bool:
        """Whether build() has produced current result arrays."""
        return self._material_id_map is not None

    def _require_built(self) -> None:
        if not self.is_built:
            raise RuntimeError(
                "The model has not been built yet. Call model.build() first."
            )

    @property
    def material_id_map(self) -> np.ndarray:
        """
        Final DORT material-ID array of shape ``(nz, nr)``.
        """
        self._require_built()
        return self._material_id_map.copy()

    @property
    def material_name_map(self) -> np.ndarray:
        """
        Final material-name array of shape ``(nz, nr)``.
        """
        self._require_built()
        return self._material_name_map.copy()

    @property
    def region_map(self) -> np.ndarray:
        """
        Name of the region that last assigned each cell.

        Background-filled cells contain ``"background"``.
        Unfilled cells contain an empty string.
        """
        self._require_built()
        return self._region_map.copy()

    @property
    def priority_map(self) -> np.ndarray:
        """
        Priority responsible for the final assignment of each cell.

        Background cells contain a very small sentinel integer.
        Unfilled cells also retain that sentinel.
        """
        self._require_built()
        return self._priority_map.copy()

    @property
    def warnings(self) -> tuple[str, ...]:
        """Warnings generated by the most recent validation/build."""
        return tuple(self._warnings)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(
        self,
        *,
        strict_region_bounds: bool = False,
    ) -> tuple[str, ...]:
        """
        Validate model consistency.

        Parameters
        ----------
        strict_region_bounds
            If False, a region extending partly outside the mesh produces a
            warning. If True, it raises ValueError.

        Returns
        -------
        tuple[str, ...]
            Warning messages.

        Raises
        ------
        ValueError / KeyError
            For invalid mesh, undefined materials, or invalid region use.
        """
        self._warnings = []

        self.mesh.validate()
        self.materials.validate()

        if self._background_material is not None:
            if self._background_material not in self.materials:
                raise KeyError(
                    f"Background material {self._background_material!r} "
                    "is not registered."
                )

        for region in self.regions:
            if not region.enabled:
                continue

            if region.material not in self.materials:
                raise KeyError(
                    f"Region {region.name!r} refers to undefined material "
                    f"{region.material!r}."
                )

            if not region.intersects_mesh(self.mesh):
                raise ValueError(
                    f"Region {region.name!r} does not intersect the mesh."
                )

            if not region.is_within_mesh(self.mesh):
                message = (
                    f"Region {region.name!r} extends outside the mesh domain. "
                    "Only cells whose centres fall inside the region and mesh "
                    "can be assigned."
                )

                if strict_region_bounds:
                    raise ValueError(message)

                self._warnings.append(message)

            if region.n_cells(self.mesh) == 0:
                self._warnings.append(
                    f"Region {region.name!r} intersects the mesh geometrically "
                    "but selects no mesh-cell centres."
                )

        return tuple(self._warnings)

    # ------------------------------------------------------------------
    # Equal-priority overlap checking
    # ------------------------------------------------------------------

    def _check_equal_priority_overlaps(self) -> None:
        """
        Reject cell overlaps between enabled regions of equal priority.

        Different-priority overlaps are intentional and are resolved by the
        normal low-to-high priority painting process.
        """
        enabled_regions = [
            region for region in self.regions if region.enabled
        ]

        by_priority: dict[int, list[Region]] = {}

        for region in enabled_regions:
            by_priority.setdefault(region.priority, []).append(region)

        for priority, group in by_priority.items():
            if len(group) < 2:
                continue

            masks = {
                region.name: region.mask(self.mesh)
                for region in group
            }

            for i, region_a in enumerate(group[:-1]):
                mask_a = masks[region_a.name]

                for region_b in group[i + 1:]:
                    overlap = mask_a & masks[region_b.name]
                    n_overlap = int(np.count_nonzero(overlap))

                    if n_overlap > 0:
                        raise ValueError(
                            f"Equal-priority overlap detected: regions "
                            f"{region_a.name!r} and {region_b.name!r} both "
                            f"have priority {priority} and overlap in "
                            f"{n_overlap} mesh cell(s). Assign different "
                            "priorities or modify the geometry."
                        )

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(
        self,
        *,
        allow_unfilled: bool = False,
        strict_region_bounds: bool = False,
    ) -> BuildSummary:
        """
        Build the final material and region maps.

        Algorithm
        ---------
        1. Validate mesh/material/region consistency.
        2. Fill the complete mesh with the background material, if defined.
        3. Sort enabled regions from low to high priority.
        4. Paint each region over the existing map.
        5. Reject equal-priority overlaps.
        6. Check for remaining unfilled cells.

        Parameters
        ----------
        allow_unfilled
            If False, any remaining cell without a material causes an error.
            If True, unfilled cells retain material ID 0 and empty names.
        strict_region_bounds
            Passed to ``validate()``.

        Returns
        -------
        BuildSummary
            Summary of the successful build.
        """
        self.validate(
            strict_region_bounds=strict_region_bounds
        )

        self._check_equal_priority_overlaps()

        shape = self.mesh.shape

        material_id_map = np.zeros(shape, dtype=int)
        material_name_map = np.full(shape, "", dtype=object)
        region_map = np.full(shape, "", dtype=object)

        # Sentinel lower than any ordinary user-supplied priority.
        priority_sentinel = np.iinfo(np.int64).min
        priority_map = np.full(
            shape,
            priority_sentinel,
            dtype=np.int64,
        )

        # --------------------------------------------------------------
        # Background fill
        # --------------------------------------------------------------
        if self._background_material is not None:
            background = self.materials[self._background_material]

            material_id_map[:, :] = background.dort_id
            material_name_map[:, :] = background.name
            region_map[:, :] = "background"

        # --------------------------------------------------------------
        # Region painting: low priority -> high priority
        # --------------------------------------------------------------
        for region in self.regions.sorted_by_priority():
            mask = region.mask(self.mesh)

            if not np.any(mask):
                continue

            material = self.materials[region.material]

            material_id_map[mask] = material.dort_id
            material_name_map[mask] = material.name
            region_map[mask] = region.name
            priority_map[mask] = region.priority

        # --------------------------------------------------------------
        # Final unfilled-cell check
        # --------------------------------------------------------------
        unfilled = material_id_map == 0
        n_unfilled = int(np.count_nonzero(unfilled))

        if n_unfilled > 0 and not allow_unfilled:
            raise ValueError(
                f"Model contains {n_unfilled} unfilled mesh cell(s). "
                "Define a background material, add regions that cover the "
                "remaining cells, or call build(allow_unfilled=True)."
            )

        # Save only after all checks succeed.
        self._material_id_map = material_id_map
        self._material_name_map = material_name_map
        self._region_map = region_map
        self._priority_map = priority_map

        return BuildSummary(
            model_name=self.name,
            shape=shape,
            n_cells=self.mesh.n_cells,
            n_materials=len(self.materials),
            n_regions=sum(
                1 for region in self.regions if region.enabled
            ),
            background_material=self._background_material,
            warnings=tuple(self._warnings),
        )

    # ------------------------------------------------------------------
    # Utility methods
    # ------------------------------------------------------------------

    def cell_assignment(
        self,
        z_index: int,
        r_index: int,
    ) -> dict[str, object]:
        """
        Return the final assignment of one mesh cell.

        This is a debugging helper and will be useful when inspecting a
        suspicious point in the material map.
        """
        self._require_built()

        nz, nr = self.mesh.shape

        if not (0 <= z_index < nz):
            raise IndexError(
                f"z_index={z_index} outside valid range 0..{nz - 1}."
            )

        if not (0 <= r_index < nr):
            raise IndexError(
                f"r_index={r_index} outside valid range 0..{nr - 1}."
            )

        return {
            "z_index": z_index,
            "r_index": r_index,
            "z_center": float(self.mesh.z.centers[z_index]),
            "r_center": float(self.mesh.r.centers[r_index]),
            "material_id": int(
                self._material_id_map[z_index, r_index]
            ),
            "material": self._material_name_map[
                z_index, r_index
            ],
            "region": self._region_map[z_index, r_index],
            "priority": int(
                self._priority_map[z_index, r_index]
            ),
        }

    def material_cell_counts(self) -> dict[str, int]:
        """
        Return number of cells assigned to each material.
        """
        self._require_built()

        result: dict[str, int] = {}

        for material in self.materials:
            result[material.name] = int(
                np.count_nonzero(
                    self._material_id_map == material.dort_id
                )
            )

        if np.any(self._material_id_map == 0):
            result["<unfilled>"] = int(
                np.count_nonzero(self._material_id_map == 0)
            )

        return result

    def region_cell_counts(self) -> dict[str, int]:
        """
        Return number of final cells owned by each region/background.

        Note that a lower-priority region may originally cover more cells than
        it owns in the final map because higher-priority regions can overwrite
        parts of it.
        """
        self._require_built()

        unique, counts = np.unique(
            self._region_map,
            return_counts=True,
        )

        result: dict[str, int] = {}

        for name, count in zip(unique, counts, strict=True):
            label = name if name else "<unfilled>"
            result[str(label)] = int(count)

        return result

    def __repr__(self) -> str:
        status = "built" if self.is_built else "not built"

        return (
            f"DORTModel(name={self.name!r}, "
            f"materials={len(self.materials)}, "
            f"regions={len(self.regions)}, "
            f"mesh_shape={self.mesh.shape}, "
            f"background={self._background_material!r}, "
            f"status={status!r})"
        )


if __name__ == "__main__":
    # --------------------------------------------------------------
    # Demonstration / smoke test
    # --------------------------------------------------------------
    model = DORTModel("example_RZ_model")

    model.add_material(
        "Sodium",
        description="Background coolant",
    )
    model.add_material("Core")
    model.add_material("SS316")
    model.add_material("Air")

    model.mesh.r.add_segment(
        0.0,
        200.0,
        step=10.0,
    )
    model.mesh.z.add_segment(
        -100.0,
        100.0,
        step=10.0,
    )

    model.set_background("Sodium")

    model.add_region(
        "core",
        material="Core",
        r=(0.0, 100.0),
        z=(-50.0, 50.0),
        priority=20,
    )

    model.add_region(
        "radial_shield",
        material="SS316",
        r=(100.0, 140.0),
        z=(-50.0, 50.0),
        priority=30,
    )

    model.add_region(
        "penetration",
        material="Air",
        r=(80.0, 120.0),
        z=(-10.0, 10.0),
        priority=50,
    )

    summary = model.build()

    print(model)
    print(summary)
    print()

    print("Material cell counts:")
    for name, count in model.material_cell_counts().items():
        print(f"  {name:12s}: {count}")

    print()
    print("Final region ownership:")
    for name, count in model.region_cell_counts().items():
        print(f"  {name:16s}: {count}")

    print()
    print("Example cell:")
    print(model.cell_assignment(z_index=10, r_index=9))
