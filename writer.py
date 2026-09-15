"""DORT/FIDO serialization for geometry and material filling.

The writer translates a built :class:`model.DORTModel` into ordinary R-Z
geometry/material input arrays. The present writer covers ``2*``, ``4*``,
``8$``, ``9$`` and an optional identity ``84$`` helper.

Directional quadrature is documented as a separate processing stage because
DORT stores it in ``81*`` (weights), ``82*`` (R-direction cosine), and ``83*``
(Z-direction cosine).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import numpy as np

from model import DORTModel


@dataclass(frozen=True)
class ZoneDefinition:
    """Describe one generated DORT material zone.
    
    Parameters
    ----------
    zone_id : int
        One-based DORT zone number.
    owner : str
        Geometric owner label or material-derived owner label.
    material : str
        Material name used by the zone.
    material_number : int
        Material number written to DORT ``9$``.
    n_cells : int
        Number of fine-space cells assigned to the zone.
    """
    zone_id: int
    owner: str
    material: str
    material_number: int
    n_cells: int


@dataclass(frozen=True)
class ZoneData:
    """Store the generated zone map and zone definitions.
    
    Parameters
    ----------
    zone_map : numpy.ndarray
        Integer zone map with shape ``(JM, IM)``.
    zones : tuple of ZoneDefinition
        Zone definitions in DORT zone-number order.
    """
    zone_map: np.ndarray
    zones: tuple[ZoneDefinition, ...]

    @property
    def izm(self) -> int:
        """Return the number of generated material zones.
        
        Returns
        -------
        int
            ``IZM``.
        """
        return len(self.zones)


def _format_real(value: float, precision: int = 8) -> str:
    """Format one finite floating-point value for FIDO free-field input.
    
    Parameters
    ----------
    value : float
        Value to format.
    precision : int, optional
        Significant-digit target.
    
    Returns
    -------
    str
        FIDO-compatible numeric token.
    
    Raises
    ------
    ValueError
        If ``value`` is not finite.
    """
    value = float(value)
    if not np.isfinite(value):
        raise ValueError("Cannot write non-finite mesh coordinate.")
    if value == 0.0:
        return "0.0"
    if 1.0e-4 <= abs(value) < 1.0e7:
        return f"{value:.{precision}g}"
    return f"{value:.{precision}E}"


def _wrap_fields(origin: str, fields: list[str], *, width: int = 72) -> str:
    """Wrap FIDO free-field tokens without splitting operator clauses.
    
    Parameters
    ----------
    origin : str
        Array-origin token such as ``"2**"`` or ``"9$$"``.
    fields : list of str
        Tokens to append.
    width : int, optional
        Preferred maximum line width.
    
    Returns
    -------
    str
        Wrapped multi-line text.
    
    Raises
    ------
    ValueError
        If ``width`` is too small for practical free-field formatting.
    """
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
    """Encode one integer row using FIDO ``R`` repetition syntax.
    
    Parameters
    ----------
    row : numpy.ndarray
        One-dimensional integer row.
    min_run : int, optional
        Minimum repeated-run length to compress.
    
    Returns
    -------
    list of str
        Encoded tokens.
    
    Raises
    ------
    ValueError
        If ``row`` is not one-dimensional.
    """
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
    """Translate a built model to DORT/FIDO R-Z geometry/material arrays.
    
    Parameters
    ----------
    model : DORTModel
        Already-built model.
    zone_policy : {'region', 'material'}, optional
        ``'region'`` creates a separate zone for every final geometric owner;
        ``'material'`` creates one zone for every material actually used.
    material_numbers : mapping of str to int, optional
        Override mapping from material name to the material number written in
        ``9$``. This supports external GIP/cross-section identifiers that differ
        from the project's positive internal IDs.
    line_width : int, optional
        Preferred free-field line width. The default of 72 follows traditional
        FIDO practice.
    
    Raises
    ------
    RuntimeError
        If the model has not been built.
    ValueError
        If ``zone_policy`` or ``line_width`` is invalid.
    KeyError
        If ``material_numbers`` contains an unknown material.
    TypeError
        If an external material number is not an integer.
    """

    def __init__(
        self,
        model: DORTModel,
        *,
        zone_policy: str = "region",
        material_numbers: Mapping[str, int] | None = None,
        line_width: int = 72,
    ) -> None:
        if not model.is_built:
            raise RuntimeError("Call model.build() before constructing DORTWriter.")
        if zone_policy not in {"region", "material"}:
            raise ValueError("zone_policy must be 'region' or 'material'.")
        if line_width < 20:
            raise ValueError("line_width must be at least 20.")

        self.model = model
        self.zone_policy = zone_policy
        self.line_width = int(line_width)
        self._material_numbers = dict(material_numbers or {})
        self._validate_material_numbers()
        self._zone_data = self._build_zone_data()

    @property
    def im(self) -> int:
        """Return the number of radial fine-mesh intervals.
        
        Returns
        -------
        int
            DORT ``IM``.
        """
        return self.model.mesh.r.n_cells

    @property
    def jm(self) -> int:
        """Return the number of axial fine-mesh intervals.
        
        Returns
        -------
        int
            DORT ``JM``.
        """
        return self.model.mesh.z.n_cells

    @property
    def izm(self) -> int:
        """Return the number of generated material zones.
        
        Returns
        -------
        int
            DORT ``IZM``.
        """
        return self._zone_data.izm

    @property
    def zones(self) -> tuple[ZoneDefinition, ...]:
        """Return generated zone definitions.
        
        Returns
        -------
        tuple of ZoneDefinition
            Zones in zone-number order.
        """
        return self._zone_data.zones

    @property
    def zone_map(self) -> np.ndarray:
        """Return the generated fine-space zone map.
        
        Returns
        -------
        numpy.ndarray
            Integer array with shape ``(JM, IM)``.
        """
        return self._zone_data.zone_map.copy()

    @property
    def required_control_values(self) -> dict[str, int]:
        """Return geometry-related control values that must agree with DORT ``62$``.
        
        Returns
        -------
        dict of str to int
            Mapping containing ``IZM``, ``IM``, ``JM``, and ``INGEOM=1``.
        """
        return {"IZM": self.izm, "IM": self.im, "JM": self.jm, "INGEOM": 1}

    def _validate_material_numbers(self) -> None:
        """Validate external material-number overrides.
        
        Returns
        -------
        None
        
        Raises
        ------
        KeyError
            If an override refers to an unknown material.
        TypeError
            If an override is not an integer.
        ValueError
            If an override is zero.
        """
        for name, number in self._material_numbers.items():
            if name not in self.model.materials:
                raise KeyError(f"Unknown material in material_numbers: {name!r}.")
            if isinstance(number, bool) or not isinstance(number, int):
                raise TypeError(f"Material number for {name!r} must be an integer.")
            if number == 0:
                raise ValueError(f"Material number for {name!r} cannot be zero.")

    def material_number(self, material_name: str) -> int:
        """Return the DORT material number for a material name.
        
        Parameters
        ----------
        material_name : str
            Registered material name.
        
        Returns
        -------
        int
            Override value when supplied, otherwise the material's internal ID.
        
        Raises
        ------
        KeyError
            If the material is not registered.
        """
        if material_name in self._material_numbers:
            return int(self._material_numbers[material_name])
        return int(self.model.materials[material_name].dort_id)

    def _build_zone_data(self) -> ZoneData:
        """Construct zone data according to the configured zone policy.
        
        Returns
        -------
        ZoneData
            Generated zone map and definitions.
        """
        if self.zone_policy == "material":
            return self._build_material_zones()
        return self._build_region_zones()

    def _build_region_zones(self) -> ZoneData:
        """Construct one DORT zone per final geometric owner.
        
        Returns
        -------
        ZoneData
            Region-based zone data.
        
        Raises
        ------
        ValueError
            If unfilled cells or inconsistent material assignments are detected.
        RuntimeError
            If an internal zone assignment is incomplete.
        """
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
                ZoneDefinition(
                    zone_id=zone_id,
                    owner=owner,
                    material=material_name,
                    material_number=self.material_number(material_name),
                    n_cells=int(np.count_nonzero(mask)),
                )
            )

        if np.any(zone_map == 0):
            raise RuntimeError("Some filled cells were not assigned a DORT zone.")

        return ZoneData(zone_map=zone_map, zones=tuple(zones))

    def _build_material_zones(self) -> ZoneData:
        """Construct one DORT zone per material actually used.
        
        Returns
        -------
        ZoneData
            Material-based zone data.
        
        Raises
        ------
        ValueError
            If unfilled cells are present.
        RuntimeError
            If any cell remains without a generated zone.
        """
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
                ZoneDefinition(
                    zone_id=zone_id,
                    owner=f"material:{material_name}",
                    material=material_name,
                    material_number=self.material_number(material_name),
                    n_cells=int(np.count_nonzero(mask)),
                )
            )

        if np.any(zone_map == 0):
            raise RuntimeError("Some cells were not assigned a DORT zone.")

        return ZoneData(zone_map=zone_map, zones=tuple(zones))

    def ijzn_stream(self) -> np.ndarray:
        """Return the expanded DORT ``8$`` zone stream.
        
        Returns
        -------
        numpy.ndarray
            One-dimensional integer array of length ``IM * JM``.
        
        Notes
        -----
        R/I varies fastest and Z/J varies slowest. This is equivalent to
        ``zone_map.ravel(order='C')`` for the project's ``(JM, IM)`` map layout.
        """
        stream = self._zone_data.zone_map.ravel(order="C")
        if stream.size != self.im * self.jm:
            raise RuntimeError("Internal 8$ length mismatch.")
        return stream.copy()

    def izmt_stream(self) -> np.ndarray:
        """Return the expanded DORT ``9$`` zone-to-material stream.
        
        Returns
        -------
        numpy.ndarray
            One integer material number per generated zone.
        """
        return np.asarray([z.material_number for z in self.zones], dtype=int)

    def array2(self) -> str:
        """Generate DORT ``2*`` containing Z fine-mesh boundaries.
        
        Returns
        -------
        str
            FIDO-formatted ``2*`` array with ``JM + 1`` entries.
        """
        fields = [_format_real(v) for v in self.model.mesh.z.edges]
        return _wrap_fields("2**", fields, width=self.line_width)

    def array4(self) -> str:
        """Generate DORT ``4*`` containing R fine-mesh boundaries.
        
        Returns
        -------
        str
            FIDO-formatted ``4*`` array with ``IM + 1`` entries.
        """
        fields = [_format_real(v) for v in self.model.mesh.r.edges]
        return _wrap_fields("4**", fields, width=self.line_width)

    def array8(self) -> str:
        """Generate DORT ``8$`` containing zone number by fine-space cell.
        
        Returns
        -------
        str
            FIDO-formatted zone map.
        
        Notes
        -----
        Repeated values within a radial row are compressed with ``R`` clauses.
        Repeated complete radial rows are compressed with ``Q`` clauses.
        """
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
        """Generate DORT ``9$`` mapping material zone to material number.
        
        Returns
        -------
        str
            FIDO-formatted ``9$`` array with ``IZM`` entries.
        """
        fields = [str(int(v)) for v in self.izmt_stream()]
        return _wrap_fields("9$$", fields, width=self.line_width)

    def array84_identity(self) -> str:
        """Generate an identity DORT ``84$`` edit-region mapping.
        
        Returns
        -------
        str
            FIDO-formatted array in which edit-region number equals material-zone
            number.
        
        Notes
        -----
        Use this helper only when one edit region per material zone is appropriate for
        the intended calculation.
        """
        fields = [str(i) for i in range(1, self.izm + 1)]
        return _wrap_fields("84$$", fields, width=self.line_width)

    def block4_geometry_material_fragment(
        self,
        *,
        include_mesh: bool = True,
        terminate_block: bool = False,
    ) -> str:
        """Return a paste-ready Block-4 geometry/material fragment.
        
        Parameters
        ----------
        include_mesh : bool, optional
            Include ``2*`` and ``4*`` before ``8$`` and ``9$``.
        terminate_block : bool, optional
            Append a final ``T`` delimiter.
        
        Returns
        -------
        str
            Multi-line FIDO fragment.
        
        Notes
        -----
        The block is not terminated by default because a real DORT Block 4 may contain
        additional arrays after ``9$``.
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
        """Write the generated Block-4 fragment to disk.
        
        Parameters
        ----------
        filename : str or pathlib.Path
            Output path.
        include_mesh : bool, optional
            Include ``2*`` and ``4*``.
        terminate_block : bool, optional
            Append a final ``T`` delimiter.
        
        Returns
        -------
        pathlib.Path
            Path written.
        """
        path = Path(filename)
        path.write_text(
            self.block4_geometry_material_fragment(
                include_mesh=include_mesh,
                terminate_block=terminate_block,
            ) + "\n",
            encoding="ascii",
        )
        return path

    def zone_table_text(self) -> str:
        """Return a human-readable generated-zone table.
        
        Returns
        -------
        str
            Multi-line table containing zone ID, owner, material, DORT material number,
            and cell count.
        """
        lines = [
            "Zone  Owner                     Material                  Mat.No.    Cells",
            "--------------------------------------------------------------------------",
        ]
        for z in self.zones:
            lines.append(
                f"{z.zone_id:4d}  {z.owner[:25]:25s} {z.material[:24]:24s} "
                f"{z.material_number:7d} {z.n_cells:8d}"
            )
        return "\n".join(lines)

    def summary_text(self) -> str:
        """Return a human-readable writer summary.
        
        Returns
        -------
        str
            Geometry/control values, array lengths, and zone table suitable for
            pre-run verification.
        """
        return "\n".join(
            [
                f"DORT writer summary for: {self.model.name}",
                "",
                "Required/consistent 62$ values:",
                f"  IZM = {self.izm}",
                f"  IM  = {self.im}",
                f"  JM  = {self.jm}",
                "  INGEOM = 1  (R-Z)",
                "",
                f"2* entries = {self.jm + 1}",
                f"4* entries = {self.im + 1}",
                f"8$ entries = {self.im * self.jm}",
                f"9$ entries = {self.izm}",
                "",
                self.zone_table_text(),
            ]
        )


if __name__ == "__main__":
    model = DORTModel("writer_demo")
    for name in ("Sodium", "Core", "SS316", "Air"):
        model.add_material(name)

    model.mesh.r.add_segment(0.0, 200.0, step=10.0)
    model.mesh.z.add_segment(-100.0, 100.0, step=10.0)
    model.set_background("Sodium")

    model.add_region("core", material="Core", r=(0.0, 100.0), z=(-50.0, 50.0), priority=20)
    model.add_region("radial_shield", material="SS316", r=(100.0, 140.0), z=(-50.0, 50.0), priority=30)
    model.add_region("penetration", material="Air", r=(80.0, 120.0), z=(-10.0, 10.0), priority=50)
    model.build()

    writer = DORTWriter(model)
    print(writer.summary_text())
    print()
    print(writer.block4_geometry_material_fragment())
