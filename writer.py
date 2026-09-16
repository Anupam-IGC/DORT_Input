"""DORT/FIDO serialization for R-Z geometry and local external mixtures.

The local DORT installation used by this project reads pre-mixed macroscopic
cross sections from an external file (normally ``mixf.cr``).  The supplied
``m_ia_oa.for`` program creates that file from microscopic ``igc-s3`` data.

For a P_L calculation, each physical mixture occupies L+1 consecutive records
in ``mixf.cr``.  The locally modified DORT uses the *negative* first record
number in array 9$::

    P5 mixture 1 -> tables  1..6 -> 9$ =  -1
    P5 mixture 2 -> tables  7..12 -> 9$ = -7
    P5 mixture 3 -> tables 13..18 -> 9$ = -13

The standard DORT in-core 10$/11$/12* mixing table is therefore not generated.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import numpy as np

from model import DORTModel


@dataclass(frozen=True)
class ZoneDefinition:
    """One generated DORT material zone."""

    zone_id: int
    owner: str
    material: str
    material_id: int
    material_number: int
    legendre_order: int
    cross_section_tables: tuple[int, ...]
    n_cells: int


@dataclass(frozen=True)
class ZoneData:
    zone_map: np.ndarray
    zones: tuple[ZoneDefinition, ...]

    @property
    def izm(self) -> int:
        return len(self.zones)


def _format_real(value: float, precision: int = 8) -> str:
    value = float(value)
    if not np.isfinite(value):
        raise ValueError("Cannot write non-finite value.")
    if value == 0.0:
        return "0.0"
    if 1.0e-4 <= abs(value) < 1.0e7:
        return f"{value:.{precision}g}"
    return f"{value:.{precision}E}"


def _wrap_fields(origin: str, fields: list[str], *, width: int = 72) -> str:
    if width < 20:
        raise ValueError("width must be at least 20.")

    lines: list[str] = []
    current = origin.rstrip()
    for field in fields:
        field = str(field).strip()
        if not field:
            continue
        candidate = f"{current} {field}" if current else field
        if len(candidate) <= width:
            current = candidate
        else:
            if current:
                lines.append(current.rstrip())
            current = "    " + field
    if current:
        lines.append(current.rstrip())
    return "\n".join(lines)


def _rle_row(row: np.ndarray, *, min_run: int = 2) -> list[str]:
    row = np.asarray(row, dtype=int)
    if row.ndim != 1:
        raise ValueError("row must be one-dimensional.")

    fields: list[str] = []
    i = 0
    while i < row.size:
        value = int(row[i])
        j = i + 1
        while j < row.size and int(row[j]) == value:
            j += 1
        count = j - i
        if count >= min_run:
            fields.append(f"{count}R {value}")
        else:
            fields.extend([str(value)] * count)
        i = j
    return fields


class DORTWriter:
    """Translate a built model to DORT/FIDO geometry/material arrays.

    Parameters
    ----------
    model
        Already-built :class:`model.DORTModel`.
    zone_policy
        ``"region"`` creates one zone per final geometric owner;
        ``"material"`` creates one zone per used material.
    material_numbers
        Optional explicit ``material name -> 9$ value`` mapping for advanced
        or legacy cases. Values may be positive or negative but may not be zero.
        When an external mixture is defined, its 9$ value is calculated
        automatically and should not be overridden.
    cross_section_unit
        Logical unit used by DORT ``NTSIG`` for ``mixf.cr``. The local sample
        deck uses unit 51.
    cross_section_filename
        Informational filename associated with ``cross_section_unit``.
    line_width
        Preferred FIDO free-field line width.
    """

    def __init__(
        self,
        model: DORTModel,
        *,
        zone_policy: str = "region",
        material_numbers: Mapping[str, int] | None = None,
        cross_section_unit: int = 51,
        cross_section_filename: str = "mixf.cr",
        line_width: int = 72,
    ) -> None:
        if not model.is_built:
            raise RuntimeError("Call model.build() before constructing DORTWriter.")
        if zone_policy not in {"region", "material"}:
            raise ValueError("zone_policy must be 'region' or 'material'.")
        if line_width < 20:
            raise ValueError("line_width must be at least 20.")
        if isinstance(cross_section_unit, bool) or not isinstance(cross_section_unit, int):
            raise TypeError("cross_section_unit must be an integer.")
        if cross_section_unit <= 0:
            raise ValueError("cross_section_unit must be positive.")

        model.materials.validate()
        model.mixtures.validate(material_names=model.materials.names)

        self.model = model
        self.zone_policy = zone_policy
        self.line_width = int(line_width)
        self.cross_section_unit = cross_section_unit
        self.cross_section_filename = str(cross_section_filename)
        self._material_numbers = dict(material_numbers or {})
        self._validate_material_numbers()
        self._validate_used_mixtures()
        self._zone_data = self._build_zone_data()

    @property
    def im(self) -> int:
        return self.model.mesh.r.n_cells

    @property
    def jm(self) -> int:
        return self.model.mesh.z.n_cells

    @property
    def izm(self) -> int:
        return self._zone_data.izm

    @property
    def isctm(self) -> int:
        return self.model.materials.legendre_order

    @property
    def external_mixtures_enabled(self) -> bool:
        return len(self.model.mixtures) > 0

    @property
    def zones(self) -> tuple[ZoneDefinition, ...]:
        return self._zone_data.zones

    @property
    def zone_map(self) -> np.ndarray:
        return self._zone_data.zone_map.copy()

    def create_source(self, *, background: float = 0.0):
        """Create a fixed-source builder tied to this writer's final mesh/zones.

        The returned :class:`source.FixedSource` can select source cells by
        material name, final region name, generated DORT zone number, or an
        explicit R-Z mesh interval.  Its energy spectrum may be loaded from a
        separate file and serialized as DORT cards 96** and 98**.
        """
        from source import FixedSource

        return FixedSource.from_writer(self, background=background)

    def create_run_control(
        self,
        mode: str,
        *,
        energy_groups: int,
        quadrature_directions: int,
        neutron_groups: int | None = None,
        **kwargs,
    ):
        """Create a high-level run-control profile for this writer.

        Parameters
        ----------
        mode
            ``"eigenvalue_first"``, ``"eigenvalue_rerun"`` or
            ``"fixed_source"``.
        energy_groups
            Number of energy groups (``IGM``).
        quadrature_directions
            Maximum number of angular directions (``MM``).
        neutron_groups
            Optional local-DORT ``NEUT`` tail value.
        **kwargs
            Human-readable run settings or advanced options accepted by
            :meth:`run_control.DORTRunControl.from_writer`.  Examples include
            ``maximum_outer_iterations=20``, ``left_boundary="reflected"``
            and ``flux_extrapolation="theta_weighted"``.

        Returns
        -------
        run_control.DORTRunControl
            Configured run-control object with 61$$/62$$/63** generation and
            93*..98* card validation.
        """
        from run_control import DORTRunControl

        return DORTRunControl.from_writer(
            self,
            mode=mode,
            energy_groups=energy_groups,
            quadrature_directions=quadrature_directions,
            neutron_groups=neutron_groups,
            **kwargs,
        )

    @property
    def required_file_units(self) -> dict[str, int]:
        """Known ``61$`` file-unit requirement for the local mixture workflow."""
        return {"NTSIG": self.cross_section_unit}

    @property
    def required_control_values(self) -> dict[str, int]:
        """Control values that can be inferred safely for DORT ``62$``.

        ``MIXL``, ``MTP`` and ``MTM`` are deliberately not inferred here.
        The local DORT modification reads the externally prepared ``mixf.cr``
        differently from the stock in-core mixing workflow.
        """
        return {
            "ISCTM": self.isctm,
            "IZM": self.izm,
            "IM": self.im,
            "JM": self.jm,
            "INGEOM": 1,
        }

    def _validate_material_numbers(self) -> None:
        for name, number in self._material_numbers.items():
            if name not in self.model.materials:
                raise KeyError(f"Unknown material in material_numbers: {name!r}.")
            if isinstance(number, bool) or not isinstance(number, int):
                raise TypeError(f"Material number for {name!r} must be an integer.")
            if number == 0:
                raise ValueError(f"Material number for {name!r} cannot be zero.")
            if name in self.model.mixtures:
                raise ValueError(
                    f"Material {name!r} already has an external mixture definition; "
                    "its negative 9$ value is calculated automatically."
                )

    def _used_material_names(self) -> tuple[str, ...]:
        material_map = self.model.material_name_map
        return tuple(
            material.name
            for material in self.model.materials
            if np.any(material_map == material.name)
        )

    def _validate_used_mixtures(self) -> None:
        if not self.external_mixtures_enabled:
            return
        missing = [
            name for name in self._used_material_names()
            if name not in self.model.mixtures and name not in self._material_numbers
        ]
        if missing:
            raise ValueError(
                "External mixture mode is active, but these used materials have no "
                f"mixture recipe or explicit material-number override: {missing}."
            )

    def material_number(self, material_name: str) -> int:
        """Return the value written to DORT ``9$`` for a physical material."""
        if material_name in self.model.mixtures:
            return self.model.mixtures.dort_material_number(material_name, self.isctm)
        if material_name in self._material_numbers:
            return int(self._material_numbers[material_name])
        # Fallback for simple non-mixture/legacy models.
        return int(self.model.materials[material_name].material_id)

    def material_table_numbers(self, material_name: str) -> tuple[int, ...]:
        if material_name in self.model.mixtures:
            return self.model.mixtures.table_numbers(material_name, self.isctm)
        return ()

    def material_layout(self) -> tuple[dict[str, object], ...]:
        rows: list[dict[str, object]] = []
        for material in self.model.materials:
            rows.append(
                {
                    "material_id": material.material_id,
                    "material": material.name,
                    "legendre_order": material.legendre_order,
                    "cross_section_tables": self.material_table_numbers(material.name),
                    "dort_9_value": self.material_number(material.name),
                }
            )
        return tuple(rows)

    def _zone_definition(
        self,
        *,
        zone_id: int,
        owner: str,
        material_name: str,
        n_cells: int,
    ) -> ZoneDefinition:
        material = self.model.materials[material_name]
        return ZoneDefinition(
            zone_id=zone_id,
            owner=owner,
            material=material_name,
            material_id=material.material_id,
            material_number=self.material_number(material_name),
            legendre_order=material.legendre_order,
            cross_section_tables=self.material_table_numbers(material_name),
            n_cells=n_cells,
        )

    def _build_zone_data(self) -> ZoneData:
        return self._build_material_zones() if self.zone_policy == "material" else self._build_region_zones()

    def _build_region_zones(self) -> ZoneData:
        owner_map = self.model.region_map
        material_map = self.model.material_name_map
        if np.any(owner_map == ""):
            raise ValueError("Cannot generate DORT input while unfilled cells exist.")

        owners: list[str] = []
        if np.any(owner_map == "background"):
            owners.append("background")
        for region in self.model.regions:
            if region.enabled and np.any(owner_map == region.name):
                owners.append(region.name)

        zone_map = np.zeros(owner_map.shape, dtype=int)
        zones: list[ZoneDefinition] = []
        for zone_id, owner in enumerate(owners, start=1):
            mask = owner_map == owner
            if owner == "background":
                material_name = self.model.background_material
                if material_name is None:
                    raise RuntimeError("Background cells exist without a background material.")
            else:
                material_name = self.model.regions[owner].material

            actual = np.unique(material_map[mask])
            if len(actual) != 1 or str(actual[0]) != material_name:
                raise ValueError(f"Inconsistent final material assignment for owner {owner!r}.")

            zone_map[mask] = zone_id
            zones.append(
                self._zone_definition(
                    zone_id=zone_id,
                    owner=owner,
                    material_name=material_name,
                    n_cells=int(np.count_nonzero(mask)),
                )
            )

        if np.any(zone_map == 0):
            raise RuntimeError("Some filled cells were not assigned a DORT zone.")
        return ZoneData(zone_map=zone_map, zones=tuple(zones))

    def _build_material_zones(self) -> ZoneData:
        material_map = self.model.material_name_map
        if np.any(material_map == ""):
            raise ValueError("Cannot generate DORT input while unfilled cells exist.")

        used = [m.name for m in self.model.materials if np.any(material_map == m.name)]
        zone_map = np.zeros(material_map.shape, dtype=int)
        zones: list[ZoneDefinition] = []
        for zone_id, material_name in enumerate(used, start=1):
            mask = material_map == material_name
            zone_map[mask] = zone_id
            zones.append(
                self._zone_definition(
                    zone_id=zone_id,
                    owner=f"material:{material_name}",
                    material_name=material_name,
                    n_cells=int(np.count_nonzero(mask)),
                )
            )

        if np.any(zone_map == 0):
            raise RuntimeError("Some cells were not assigned a DORT zone.")
        return ZoneData(zone_map=zone_map, zones=tuple(zones))

    def ijzn_stream(self) -> np.ndarray:
        stream = self._zone_data.zone_map.ravel(order="C")
        if stream.size != self.im * self.jm:
            raise RuntimeError("Internal 8$ length mismatch.")
        return stream.copy()

    def izmt_stream(self) -> np.ndarray:
        """Expanded local-DORT ``9$`` stream; negative values are supported."""
        stream = np.asarray([z.material_number for z in self.zones], dtype=int)
        if np.any(stream == 0):
            raise RuntimeError("DORT 9$ contains a zero material reference.")
        return stream

    def iznrg_identity_stream(self) -> np.ndarray:
        return np.arange(1, self.izm + 1, dtype=int)

    def iznrg_material_stream(self) -> np.ndarray:
        return np.asarray([z.material_id for z in self.zones], dtype=int)

    def array2(self) -> str:
        return _wrap_fields(
            "2**", [_format_real(v) for v in self.model.mesh.z.edges], width=self.line_width
        )

    def array4(self) -> str:
        return _wrap_fields(
            "4**", [_format_real(v) for v in self.model.mesh.r.edges], width=self.line_width
        )

    def array8(self) -> str:
        lines: list[str] = []
        j = 0
        group_index = 0
        while j < self.jm:
            row = self._zone_data.zone_map[j, :]
            fields = _rle_row(row)
            repeats = 0
            k = j + 1
            while k < self.jm and np.array_equal(self._zone_data.zone_map[k, :], row):
                repeats += 1
                k += 1
            if repeats:
                fields.append(f"{repeats}Q {self.im}")

            origin = "8$$" if group_index == 0 else "    "
            lines.extend(_wrap_fields(origin, fields, width=self.line_width).splitlines())
            group_index += 1
            j = k
        return "\n".join(lines)

    def array9(self) -> str:
        """Generate local-DORT ``9$$`` material references.

        External mixtures use negative references such as -1, -7 and -13 for
        P5 mixtures 1, 2 and 3.
        """
        return _wrap_fields(
            "9$$", [str(int(v)) for v in self.izmt_stream()], width=self.line_width
        )

    def array61(
        self,
        *,
        ntflx: int = 0,
        ntfog: int = 0,
        ntbsi: int = 0,
        ntdsi: int = 0,
        ntfci: int = 0,
        ntibi: int = 0,
        ntibo: int = 0,
        ntnpr: int = 0,
        ntdir: int = 0,
        ntdso: int = 0,
        ntscl: int = 0,
        ntznf: int = 0,
    ) -> str:
        """Generate DORT ``61$$`` with ``NTSIG`` tied to ``mixf.cr`` unit 51.

        ``NTSIG`` is the third entry and is taken from ``cross_section_unit``.
        Other logical units default to zero and can be supplied explicitly.
        """
        values = [
            ntflx,
            ntfog,
            self.cross_section_unit,
            ntbsi,
            ntdsi,
            ntfci,
            ntibi,
            ntibo,
            ntnpr,
            ntdir,
            ntdso,
            ntscl,
            ntznf,
        ]
        for value in values:
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError("All 61$ logical-unit values must be integers.")
            if value < 0:
                raise ValueError("61$ logical-unit values cannot be negative.")
        return _wrap_fields(
            "61$$", [str(value) for value in values] + ["E"], width=self.line_width
        )

    def array84_identity(self) -> str:
        return _wrap_fields(
            "84$$", [str(int(v)) for v in self.iznrg_identity_stream()], width=self.line_width
        )

    def array84_by_material(self) -> str:
        return _wrap_fields(
            "84$$", [str(int(v)) for v in self.iznrg_material_stream()], width=self.line_width
        )

    def mixture_cards_fragment(self) -> str:
        """Return zone-aware ``84$$`` and ``9$$`` cards for the built model.

        ``84$$`` groups edit regions by natural material/mixture ID, while
        ``9$$`` contains the local negative cross-section references.  Unlike
        the compact cards written by :meth:`MixtureRegistry.write_dort_mix_cards`,
        this method remains correct when ``zone_policy='region'`` creates more
        DORT zones than physical mixtures.
        """
        return f"{self.array84_by_material()}\n{self.array9()}"

    def write_mixture_cards(self, filename: str | Path) -> Path:
        """Write zone-aware ``84$$``/``9$$`` cards for the current writer."""
        path = Path(filename)
        path.write_text(self.mixture_cards_fragment() + "\n", encoding="ascii")
        return path

    def block4_geometry_material_fragment(
        self,
        *,
        include_mesh: bool = True,
        terminate_block: bool = False,
    ) -> str:
        """Return ``2*``, ``4*``, ``8$`` and ``9$`` for the local workflow.

        No 10$/11$/12* arrays are generated because cross-section mixing is
        performed externally before DORT execution.
        """
        parts: list[str] = []
        if include_mesh:
            parts += [self.array2(), "", self.array4(), ""]
        parts += [self.array8(), "", self.array9()]
        if terminate_block:
            parts += ["", "T"]
        return "\n".join(parts)

    def write_block4_fragment(
        self,
        filename: str | Path,
        *,
        include_mesh: bool = True,
        terminate_block: bool = False,
    ) -> Path:
        path = Path(filename)
        path.write_text(
            self.block4_geometry_material_fragment(
                include_mesh=include_mesh,
                terminate_block=terminate_block,
            ) + "\n",
            encoding="ascii",
        )
        return path

    def material_layout_text(self) -> str:
        lines = [
            "ID  Material                 P_L  mixf.cr tables      9$ value",
            "----------------------------------------------------------------",
        ]
        for row in self.material_layout():
            tables = row["cross_section_tables"]
            if tables:
                table_text = str(tables[0]) if len(tables) == 1 else f"{tables[0]}..{tables[-1]}"
            else:
                table_text = "--"
            lines.append(
                f"{int(row['material_id']):2d}  {str(row['material'])[:22]:22s} "
                f"P{int(row['legendre_order']):<2d} {table_text:17s} "
                f"{int(row['dort_9_value']):8d}"
            )
        return "\n".join(lines)

    def zone_table_text(self) -> str:
        lines = [
            "Zone  Owner                     Material              ID  9$ value   Cells",
            "----------------------------------------------------------------------------",
        ]
        for z in self.zones:
            lines.append(
                f"{z.zone_id:4d}  {z.owner[:25]:25s} {z.material[:20]:20s} "
                f"{z.material_id:3d} {z.material_number:9d} {z.n_cells:8d}"
            )
        return "\n".join(lines)

    def summary_text(self) -> str:
        lines = [
            f"DORT writer summary for: {self.model.name}",
            "",
            "Cross-section file link (61$):",
            f"  NTSIG = {self.cross_section_unit}",
            f"  file  = {self.cross_section_filename}",
            "",
            "62$ values inferred safely:",
            f"  ISCTM = {self.isctm}",
            f"  IZM   = {self.izm}",
            f"  IM    = {self.im}",
            f"  JM    = {self.jm}",
            "  INGEOM = 1  (R-Z)",
            "  MIXL/MTP/MTM: retain values required by the local modified-DORT template",
            "",
            "External mixture / material layout:",
            self.material_layout_text(),
            "",
            f"2* entries = {self.jm + 1}",
            f"4* entries = {self.im + 1}",
            f"8$ entries = {self.im * self.jm}",
            f"9$ entries = {self.izm}",
            "",
            self.zone_table_text(),
        ]
        return "\n".join(lines)


if __name__ == "__main__":
    model = DORTModel("writer_demo")
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
    model.build()

    writer = DORTWriter(model, cross_section_unit=51)
    print(writer.array61())
    print()
    print(writer.summary_text())
    print()
    print(writer.block4_geometry_material_fragment())
