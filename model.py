"""High-level R-Z model assembly for DORT input preparation.

The model combines mesh, material, and region definitions into validated
material/region maps.  DORT/FIDO serialization is handled by ``writer.py``.
The array convention is ``(nz, nr)``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from mesh import Mesh
from materials import Material, MaterialRegistry
from mixtures import Mixture, MixtureFileValidation, MixtureRegistry
from regions import Region, RegionRegistry


@dataclass(frozen=True)
class BuildSummary:
    model_name: str
    shape: tuple[int, int]
    n_cells: int
    n_materials: int
    n_regions: int
    background_material: str | None
    warnings: tuple[str, ...] = ()

    def __repr__(self) -> str:
        return (
            f"BuildSummary(model={self.model_name!r}, shape={self.shape}, "
            f"cells={self.n_cells}, materials={self.n_materials}, "
            f"regions={self.n_regions}, background={self.background_material!r}, "
            f"warnings={len(self.warnings)})"
        )


class DORTModel:
    """Central user-facing R-Z model object."""

    def __init__(self, name: str = "DORT_model") -> None:
        clean_name = str(name).strip()
        if not clean_name:
            raise ValueError("Model name cannot be empty.")

        self.name = clean_name
        self.mesh = Mesh()
        self.materials = MaterialRegistry()
        self.mixtures = MixtureRegistry()
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
        material_id: int | None = None,
        dort_id: int | None = None,
        legendre_order: int = 0,
        description: str = "",
    ) -> Material:
        """Register a material.

        Parameters
        ----------
        name
            Unique readable material name.
        material_id
            Optional natural-number ID. Normally omit this; IDs are assigned as
            1, 2, 3, ... in registration order.
        dort_id
            Legacy alias for ``material_id``.
        legendre_order
            Scattering expansion order L for P_L. DORT uses one global ISCTM,
            so every material in a valid model must use the same value.
        description
            Optional explanatory text.
        """
        return self.materials.add(
            name,
            material_id=material_id,
            dort_id=dort_id,
            legendre_order=legendre_order,
            description=description,
        )

    # ------------------------------------------------------------------
    # External mixture-preparation convenience API
    # ------------------------------------------------------------------

    def add_mixture(
        self,
        name: str,
        components,
        *,
        legendre_order: int | None = None,
        description: str = "",
    ) -> Mixture:
        """Register a physical material and its external mixing recipe.

        Parameters
        ----------
        name
            Final material name used by geometry regions.
        components
            Mapping ``{microscopic_MAT_number: atom_density}`` or an iterable
            of ``(MAT_number, atom_density)`` pairs. These are the identifiers
            used by the microscopic ``igc-s3`` library read by ``m_ia_oa.for``.
        legendre_order
            Common order L for P_L. The supplied external mixer supports
            L = 0..6. For later mixtures this may be omitted and the established
            common material order is inherited.
        description
            Optional explanatory text.

        Notes
        -----
        Mixtures and materials share the natural sequence 1, 2, 3, ... .
        For order L, mixture m occupies ``L+1`` records in ``mixf.cr`` beginning
        at ``1 + (m-1)*(L+1)``. The locally modified DORT input therefore uses
        the negative of this first record number in array 9$.
        """
        clean_name = str(name).strip()
        expected_mixture_id = len(self.mixtures) + 1

        if clean_name in self.materials:
            material = self.materials[clean_name]
            if material.material_id != expected_mixture_id:
                raise ValueError(
                    "Mixtures must be defined in the same natural-number order as "
                    "model materials. "
                    f"Next mixture ID is {expected_mixture_id}, but material "
                    f"{clean_name!r} has ID {material.material_id}."
                )
            if legendre_order is not None and material.legendre_order != legendre_order:
                raise ValueError(
                    f"Material {clean_name!r} already uses P{material.legendre_order}; "
                    f"cannot define its mixture as P{legendre_order}."
                )
        else:
            if legendre_order is None:
                legendre_order = self.materials.legendre_order if len(self.materials) else 0
            material = self.add_material(
                clean_name,
                legendre_order=legendre_order,
                description=description,
            )

        # The external mixer has a hard-coded maximum order of six.
        self.mixtures._validate_legendre_order(material.legendre_order)

        return self.mixtures.add(
            clean_name,
            components,
            mixture_id=material.material_id,
            description=description,
        )

    def define_mixture(
        self,
        material: str,
        components,
        *,
        description: str = "",
    ) -> Mixture:
        """Define an external mixture for an already registered material."""
        if material not in self.materials:
            raise KeyError(
                f"Cannot define mixture for {material!r}: material is not registered."
            )
        return self.add_mixture(
            material,
            components,
            legendre_order=self.materials[material].legendre_order,
            description=description,
        )

    def load_mixtures_from_excel(
        self,
        filename: str | Path,
        *,
        sheet_name: str = "Read",
        legendre_order: int = 5,
        clear_existing: bool = False,
    ) -> tuple[Mixture, ...]:
        """Load external mixture recipes from the standard workbook layout.

        The recommended workbook format follows the supplied ``mixture.py``:
        ``Nuclide`` in column A, ``MAT No.`` in column B, and one final mixture
        per subsequent column.  Nonblank mixture cells are atom densities.

        Mixture/material IDs follow the workbook column order exactly.
        """
        imported = MixtureRegistry.from_excel(filename, sheet_name=sheet_name)
        self.mixtures._validate_legendre_order(legendre_order)

        if len(self.materials) or len(self.mixtures):
            if not clear_existing:
                raise ValueError(
                    "The model already contains materials or mixtures. Load the "
                    "spreadsheet into a fresh model, or pass clear_existing=True "
                    "before defining geometry."
                )
            if len(self.regions) or self.background_material is not None:
                raise ValueError(
                    "Cannot clear materials after regions/background have been defined. "
                    "Load the mixture workbook before defining geometry."
                )
            self.materials.clear()
            self.mixtures.clear()

        for mixture in imported:
            self.add_mixture(
                mixture.name,
                mixture.components,
                legendre_order=legendre_order,
                description=f"Loaded from {Path(filename).name}:{sheet_name}",
            )
        return self.mixtures.mixtures

    def prepare_mixtures_from_excel(
        self,
        filename: str | Path,
        *,
        output_dir: str | Path = ".",
        sheet_name: str = "Read",
        legendre_order: int = 5,
        clear_existing: bool = False,
    ) -> dict[str, Path]:
        """Load a mixture workbook and write ``mix.inp`` plus mapping files."""
        self.load_mixtures_from_excel(
            filename,
            sheet_name=sheet_name,
            legendre_order=legendre_order,
            clear_existing=clear_existing,
        )
        return self.write_mixture_preparation_files(output_dir)

    def write_mixture_preparation_files(
        self,
        output_dir: str | Path,
    ) -> dict[str, Path]:
        """Write ``mix.inp``, ``Mixture_Names.txt`` and ``dort_mix_cards.txt``."""
        return self.mixtures.write_preparation_files(
            output_dir,
            self.materials.legendre_order,
        )

    def render_mixture_input(self) -> str:
        """Return the complete ``mix.inp`` text for ``m_ia_oa.for``."""
        return self.mixtures.render_mix_input(self.materials.legendre_order)

    def write_mixture_input(self, filename: str | Path) -> Path:
        """Write ``mix.inp`` for the external microscopic-to-macroscopic mixer."""
        return self.mixtures.write_mix_input(filename, self.materials.legendre_order)

    def validate_mixture_file(self, filename: str | Path) -> MixtureFileValidation:
        """Validate a generated ``mixf.cr`` against the registered mixtures."""
        return self.mixtures.validate_mix_file(filename, self.materials.legendre_order)

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
        return self._background_material

    def set_background(self, material: str) -> None:
        material = str(material).strip()
        if material not in self.materials:
            raise KeyError(
                f"Cannot set background material to {material!r}: it is not registered."
            )
        self._background_material = material

    def clear_background(self) -> None:
        self._background_material = None

    # ------------------------------------------------------------------
    # Built-map properties
    # ------------------------------------------------------------------

    @property
    def is_built(self) -> bool:
        return self._material_id_map is not None

    def _require_built(self) -> None:
        if not self.is_built:
            raise RuntimeError("The model has not been built yet. Call model.build() first.")

    @property
    def material_id_map(self) -> np.ndarray:
        self._require_built()
        return self._material_id_map.copy()

    @property
    def material_name_map(self) -> np.ndarray:
        self._require_built()
        return self._material_name_map.copy()

    @property
    def region_map(self) -> np.ndarray:
        self._require_built()
        return self._region_map.copy()

    @property
    def priority_map(self) -> np.ndarray:
        self._require_built()
        return self._priority_map.copy()

    @property
    def warnings(self) -> tuple[str, ...]:
        return tuple(self._warnings)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self, *, strict_region_bounds: bool = False) -> tuple[str, ...]:
        self._warnings = []

        self.mesh.validate()
        self.materials.validate()
        self.mixtures.validate(material_names=self.materials.names)

        if self._background_material is not None and self._background_material not in self.materials:
            raise KeyError(
                f"Background material {self._background_material!r} is not registered."
            )

        for region in self.regions:
            if not region.enabled:
                continue

            if region.material not in self.materials:
                raise KeyError(
                    f"Region {region.name!r} refers to undefined material {region.material!r}."
                )

            if not region.intersects_mesh(self.mesh):
                raise ValueError(f"Region {region.name!r} does not intersect the mesh.")

            if not region.is_within_mesh(self.mesh):
                message = (
                    f"Region {region.name!r} extends outside the mesh domain. "
                    "Only cells whose centres fall inside both the region and mesh are assigned."
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

    def _check_equal_priority_overlaps(self) -> None:
        enabled_regions = [region for region in self.regions if region.enabled]
        by_priority: dict[int, list[Region]] = {}

        for region in enabled_regions:
            by_priority.setdefault(region.priority, []).append(region)

        for priority, group in by_priority.items():
            if len(group) < 2:
                continue

            masks = {region.name: region.mask(self.mesh) for region in group}
            for i, region_a in enumerate(group[:-1]):
                for region_b in group[i + 1:]:
                    overlap = masks[region_a.name] & masks[region_b.name]
                    n_overlap = int(np.count_nonzero(overlap))
                    if n_overlap:
                        raise ValueError(
                            f"Equal-priority overlap detected: regions {region_a.name!r} "
                            f"and {region_b.name!r} both have priority {priority} and "
                            f"overlap in {n_overlap} mesh cell(s). Assign different "
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
        self.validate(strict_region_bounds=strict_region_bounds)
        self._check_equal_priority_overlaps()

        shape = self.mesh.shape
        material_id_map = np.zeros(shape, dtype=int)
        material_name_map = np.full(shape, "", dtype=object)
        region_map = np.full(shape, "", dtype=object)
        priority_sentinel = np.iinfo(np.int64).min
        priority_map = np.full(shape, priority_sentinel, dtype=np.int64)

        if self._background_material is not None:
            background = self.materials[self._background_material]
            material_id_map[:, :] = background.material_id
            material_name_map[:, :] = background.name
            region_map[:, :] = "background"

        for region in self.regions.sorted_by_priority():
            mask = region.mask(self.mesh)
            if not np.any(mask):
                continue

            material = self.materials[region.material]
            material_id_map[mask] = material.material_id
            material_name_map[mask] = material.name
            region_map[mask] = region.name
            priority_map[mask] = region.priority

        unfilled = material_id_map == 0
        n_unfilled = int(np.count_nonzero(unfilled))
        if n_unfilled and not allow_unfilled:
            raise ValueError(
                f"Model contains {n_unfilled} unfilled mesh cell(s). Define a background "
                "material, add regions covering the remaining cells, or call "
                "build(allow_unfilled=True)."
            )

        self._material_id_map = material_id_map
        self._material_name_map = material_name_map
        self._region_map = region_map
        self._priority_map = priority_map

        return BuildSummary(
            model_name=self.name,
            shape=shape,
            n_cells=self.mesh.n_cells,
            n_materials=len(self.materials),
            n_regions=sum(1 for region in self.regions if region.enabled),
            background_material=self._background_material,
            warnings=tuple(self._warnings),
        )

    # ------------------------------------------------------------------
    # Utility methods
    # ------------------------------------------------------------------

    def cell_assignment(self, z_index: int, r_index: int) -> dict[str, object]:
        self._require_built()
        nz, nr = self.mesh.shape
        if not (0 <= z_index < nz):
            raise IndexError(f"z_index={z_index} outside valid range 0..{nz - 1}.")
        if not (0 <= r_index < nr):
            raise IndexError(f"r_index={r_index} outside valid range 0..{nr - 1}.")

        material_id = int(self._material_id_map[z_index, r_index])
        material_name = self._material_name_map[z_index, r_index]
        result: dict[str, object] = {
            "z_index": z_index,
            "r_index": r_index,
            "z_center": float(self.mesh.z.centers[z_index]),
            "r_center": float(self.mesh.r.centers[r_index]),
            "material_id": material_id,
            "material": material_name,
            "region": self._region_map[z_index, r_index],
            "priority": int(self._priority_map[z_index, r_index]),
        }

        if material_id > 0:
            legendre_order = self.materials[material_name].legendre_order
            result["legendre_order"] = legendre_order
            if material_name in self.mixtures:
                result["mixf_first_table"] = self.mixtures.first_table_number(
                    material_name, legendre_order
                )
                result["dort_9_material_number"] = self.mixtures.dort_material_number(
                    material_name, legendre_order
                )

        return result

    def material_cell_counts(self) -> dict[str, int]:
        self._require_built()
        result: dict[str, int] = {}
        for material in self.materials:
            result[material.name] = int(
                np.count_nonzero(self._material_id_map == material.material_id)
            )
        if np.any(self._material_id_map == 0):
            result["<unfilled>"] = int(np.count_nonzero(self._material_id_map == 0))
        return result

    def region_cell_counts(self) -> dict[str, int]:
        self._require_built()
        unique, counts = np.unique(self._region_map, return_counts=True)
        result: dict[str, int] = {}
        for name, count in zip(unique, counts, strict=True):
            result[str(name if name else "<unfilled>")] = int(count)
        return result

    def __repr__(self) -> str:
        status = "built" if self.is_built else "not built"
        return (
            f"DORTModel(name={self.name!r}, materials={len(self.materials)}, "
            f"mixtures={len(self.mixtures)}, regions={len(self.regions)}, "
            f"mesh_shape={self.mesh.shape}, "
            f"background={self._background_material!r}, status={status!r})"
        )


if __name__ == "__main__":
    model = DORTModel("external_mixture_demo")
    model.add_mixture(
        "Mixture-1",
        {5125: 1.10597e-2, 5131: 8.27546e-3, 825: 2.90028e-2},
        legendre_order=5,
    )
    model.add_mixture("Mixture-2", {425: 1.1107e-1})
    model.add_mixture("Mixture-3", {725: 1.89693e-5, 825: 8.15551e-5})

    model.mesh.r.add_segment(0.0, 200.0, step=10.0)
    model.mesh.z.add_segment(-100.0, 100.0, step=10.0)
    model.set_background("Mixture-1")
    model.add_region(
        "inner", material="Mixture-2", r=(0.0, 100.0), z=(-50.0, 50.0), priority=20
    )
    model.add_region(
        "shield", material="Mixture-3", r=(100.0, 140.0), z=(-50.0, 50.0), priority=30
    )
    print(model.build())
    print()
    print(model.render_mixture_input())
