"""Fixed-source construction on an existing DORT R-Z model.

The locally verified fixed-source workflow uses ``INPSRM=2``: card ``96*``
contains a two-dimensional spatial source over the R-Z fine mesh and card
``98*`` contains the energy dependence.  This module lets users construct the
spatial field using the same materials, regions, DORT zones, or mesh coordinates
that were already used to build the geometry.

All internal source arrays use project ordering ``(JM, IM) == (nz, nr)``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable, Mapping, TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from model import DORTModel
    from writer import DORTWriter


def _format_real(value: float, precision: int = 8) -> str:
    value = float(value)
    if not np.isfinite(value):
        raise ValueError("Source values must be finite.")
    if value == 0.0:
        return "0.0"
    if 1.0e-4 <= abs(value) < 1.0e7:
        return f"{value:.{precision}g}"
    return f"{value:.{precision}E}"


def _wrap_fields(origin: str, fields: list[str], *, width: int = 72) -> str:
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


def _rle_real_row(row: np.ndarray) -> list[str]:
    row = np.asarray(row, dtype=float)
    if row.ndim != 1:
        raise ValueError("Source row must be one-dimensional.")
    fields: list[str] = []
    i = 0
    while i < row.size:
        value = float(row[i])
        j = i + 1
        while j < row.size and float(row[j]) == value:
            j += 1
        count = j - i
        token = _format_real(value)
        if count >= 2:
            fields.append(f"{count}R {token}")
        else:
            fields.append(token)
        i = j
    return fields


def _parse_spectrum_text(text: str) -> np.ndarray:
    """Parse a simple numeric spectrum, including basic FIDO ``nR value`` syntax."""
    values: list[float] = []
    tokens: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].split("!", 1)[0].strip()
        if line:
            tokens.extend(line.replace(",", " ").split())

    i = 0
    while i < len(tokens):
        token = tokens[i]
        low = token.lower()
        if low in {"98**", "98*", "t", "e"}:
            i += 1
            continue
        if low.endswith("r") and low[:-1].isdigit():
            count = int(low[:-1])
            if i + 1 >= len(tokens):
                raise ValueError(f"Missing value after repetition token {token!r}.")
            raw = tokens[i + 1].replace("D", "E").replace("d", "e")
            value = float(raw)
            values.extend([value] * count)
            i += 2
            continue
        raw = token.replace("D", "E").replace("d", "e")
        try:
            values.append(float(raw))
        except ValueError as exc:
            raise ValueError(f"Unrecognized spectrum token {token!r}.") from exc
        i += 1

    array = np.asarray(values, dtype=float)
    if array.size == 0:
        raise ValueError("Energy-spectrum file contains no numeric values.")
    if not np.all(np.isfinite(array)):
        raise ValueError("Energy spectrum contains non-finite values.")
    return array


class FixedSource:
    """Build DORT ``96*`` spatial and ``98*`` energy source arrays.

    Instances are normally created with :meth:`writer.DORTWriter.create_source`
    so DORT-zone selectors are available in addition to materials and regions.
    """

    def __init__(
        self,
        model: "DORTModel",
        *,
        zone_map: np.ndarray | None = None,
        background: float = 0.0,
        line_width: int = 72,
    ) -> None:
        if not model.is_built:
            raise RuntimeError("Call model.build() before creating a fixed source.")
        background = float(background)
        if not np.isfinite(background):
            raise ValueError("background must be finite.")
        self.model = model
        self.line_width = int(line_width)
        self._background = background
        self._spatial = np.full(model.mesh.shape, background, dtype=float)
        self._spectrum: np.ndarray | None = None
        self._spectrum_filename: str | None = None
        self._zone_map = None if zone_map is None else np.asarray(zone_map, dtype=int).copy()
        if self._zone_map is not None and self._zone_map.shape != model.mesh.shape:
            raise ValueError("zone_map shape does not match the model mesh.")

    @classmethod
    def from_writer(cls, writer: "DORTWriter", *, background: float = 0.0) -> "FixedSource":
        return cls(
            writer.model,
            zone_map=writer.zone_map,
            background=background,
            line_width=writer.line_width,
        )

    @property
    def spatial(self) -> np.ndarray:
        return self._spatial.copy()

    @property
    def energy_spectrum(self) -> np.ndarray | None:
        return None if self._spectrum is None else self._spectrum.copy()

    @property
    def energy_groups(self) -> int | None:
        return None if self._spectrum is None else int(self._spectrum.size)

    @property
    def spectrum_filename(self) -> str | None:
        return self._spectrum_filename

    def clear(self, value: float | None = None) -> "FixedSource":
        fill = self._background if value is None else float(value)
        if not np.isfinite(fill):
            raise ValueError("Source fill value must be finite.")
        self._spatial.fill(fill)
        return self

    def _apply(self, mask: np.ndarray, strength: float, *, combine: str = "replace") -> None:
        mask = np.asarray(mask, dtype=bool)
        if mask.shape != self.model.mesh.shape:
            raise ValueError("Source mask shape does not match model mesh.")
        strength = float(strength)
        if not np.isfinite(strength):
            raise ValueError("Source strength must be finite.")
        if combine == "replace":
            self._spatial[mask] = strength
        elif combine == "add":
            self._spatial[mask] += strength
        elif combine == "multiply":
            self._spatial[mask] *= strength
        else:
            raise ValueError("combine must be 'replace', 'add', or 'multiply'.")

    def by_material(
        self,
        material: str | Mapping[str, float],
        strength: float = 1.0,
        *,
        combine: str = "replace",
    ) -> "FixedSource":
        """Assign source strength to cells by final material name."""
        items = material.items() if isinstance(material, Mapping) else [(material, strength)]
        material_map = self.model.material_name_map
        for name, value in items:
            name = str(name)
            if name not in self.model.materials:
                raise KeyError(f"Material {name!r} is not registered.")
            mask = material_map == name
            if not np.any(mask):
                raise ValueError(f"Material {name!r} occupies no cells in the built model.")
            self._apply(mask, value, combine=combine)
        return self

    def by_region(
        self,
        region: str | Mapping[str, float],
        strength: float = 1.0,
        *,
        combine: str = "replace",
    ) -> "FixedSource":
        """Assign source strength by final region/owner name."""
        items = region.items() if isinstance(region, Mapping) else [(region, strength)]
        region_map = self.model.region_map
        for name, value in items:
            name = str(name)
            if name != "background" and name not in self.model.regions:
                raise KeyError(f"Region {name!r} is not registered.")
            mask = region_map == name
            if not np.any(mask):
                raise ValueError(f"Region {name!r} occupies no final mesh cells.")
            self._apply(mask, value, combine=combine)
        return self

    def by_zone(
        self,
        zone: int | Mapping[int, float],
        strength: float = 1.0,
        *,
        combine: str = "replace",
    ) -> "FixedSource":
        """Assign source strength by generated DORT zone number."""
        if self._zone_map is None:
            raise RuntimeError("DORT-zone selection requires source creation from DORTWriter.")
        items = zone.items() if isinstance(zone, Mapping) else [(zone, strength)]
        for zone_id, value in items:
            if isinstance(zone_id, bool) or not isinstance(zone_id, int) or zone_id <= 0:
                raise ValueError("zone IDs must be positive integers.")
            mask = self._zone_map == zone_id
            if not np.any(mask):
                raise ValueError(f"DORT zone {zone_id} does not exist in this writer.")
            self._apply(mask, value, combine=combine)
        return self

    def by_mesh(
        self,
        *,
        r: tuple[float, float] | None = None,
        z: tuple[float, float] | None = None,
        strength: float = 1.0,
        combine: str = "replace",
    ) -> "FixedSource":
        """Assign source to a rectangular R-Z selection using cell centres."""
        rr = self.model.mesh.r.centers
        zz = self.model.mesh.z.centers
        rmask = np.ones(rr.shape, dtype=bool)
        zmask = np.ones(zz.shape, dtype=bool)
        if r is not None:
            r0, r1 = map(float, r)
            if r1 <= r0:
                raise ValueError("r must satisfy r_max > r_min.")
            rmask = (rr >= r0) & (rr < r1)
        if z is not None:
            z0, z1 = map(float, z)
            if z1 <= z0:
                raise ValueError("z must satisfy z_max > z_min.")
            zmask = (zz >= z0) & (zz < z1)
        mask = zmask[:, None] & rmask[None, :]
        if not np.any(mask):
            raise ValueError("Mesh source selection contains no cell centres.")
        self._apply(mask, strength, combine=combine)
        return self

    def set_spatial_array(self, values: np.ndarray) -> "FixedSource":
        values = np.asarray(values, dtype=float)
        if values.shape != self.model.mesh.shape:
            raise ValueError(
                f"Spatial source must have shape {self.model.mesh.shape}; got {values.shape}."
            )
        if not np.all(np.isfinite(values)):
            raise ValueError("Spatial source contains non-finite values.")
        self._spatial = values.copy()
        return self

    def set_spatial_function(self, function: Callable[[float, float], float]) -> "FixedSource":
        """Evaluate ``function(r_center, z_center)`` over the complete mesh."""
        out = np.empty(self.model.mesh.shape, dtype=float)
        for j, zc in enumerate(self.model.mesh.z.centers):
            for i, rc in enumerate(self.model.mesh.r.centers):
                out[j, i] = float(function(float(rc), float(zc)))
        return self.set_spatial_array(out)

    def set_energy_spectrum(self, values: Iterable[float], *, normalize: bool = False) -> "FixedSource":
        spectrum = np.asarray(list(values), dtype=float)
        if spectrum.ndim != 1 or spectrum.size == 0:
            raise ValueError("Energy spectrum must be a non-empty one-dimensional sequence.")
        if not np.all(np.isfinite(spectrum)):
            raise ValueError("Energy spectrum contains non-finite values.")
        if normalize:
            total = float(np.sum(spectrum))
            if total == 0.0:
                raise ValueError("Cannot normalize a zero-sum energy spectrum.")
            spectrum = spectrum / total
        self._spectrum = spectrum
        self._spectrum_filename = None
        return self

    def set_energy_spectrum_file(
        self,
        filename: str | Path,
        *,
        normalize: bool = False,
    ) -> "FixedSource":
        path = Path(filename)
        spectrum = _parse_spectrum_text(path.read_text())
        self.set_energy_spectrum(spectrum, normalize=normalize)
        self._spectrum_filename = str(path)
        return self

    def validate(self, *, energy_groups: int | None = None) -> None:
        if self._spatial.shape != self.model.mesh.shape:
            raise ValueError("Spatial source shape no longer matches the model mesh.")
        if not np.all(np.isfinite(self._spatial)):
            raise ValueError("Spatial source contains non-finite values.")
        if self._spectrum is None:
            raise ValueError("Energy spectrum has not been defined.")
        if energy_groups is not None and self._spectrum.size != int(energy_groups):
            raise ValueError(
                f"Energy spectrum has {self._spectrum.size} values but IGM={energy_groups}."
            )

    def array96(self) -> str:
        """Generate DORT ``96**`` using R repetition and Q repeated-row compression."""
        lines: list[str] = []
        j = 0
        group = 0
        jm, im = self._spatial.shape
        while j < jm:
            row = self._spatial[j, :]
            fields = _rle_real_row(row)
            repeats = 0
            k = j + 1
            while k < jm and np.array_equal(self._spatial[k, :], row):
                repeats += 1
                k += 1
            if repeats:
                fields.append(f"{repeats}Q {im}")
            origin = "96**" if group == 0 else "    "
            lines.extend(_wrap_fields(origin, fields, width=self.line_width).splitlines())
            group += 1
            j = k
        if lines:
            lines[-1] = lines[-1] + " t"
        return "\n".join(lines)

    def array98(self, *, energy_groups: int | None = None) -> str:
        self.validate(energy_groups=energy_groups)
        fields = [_format_real(v) for v in self._spectrum]
        text = _wrap_fields("98**", fields, width=self.line_width)
        lines = text.splitlines()
        lines[-1] = lines[-1] + " t"
        return "\n".join(lines)

    def fragment(self, *, energy_groups: int | None = None) -> str:
        """Return ``96**`` followed by ``98**`` for ``INPSRM=2``."""
        self.validate(energy_groups=energy_groups)
        return self.array96() + "\n" + self.array98(energy_groups=energy_groups)

    def summary_text(self) -> str:
        nz = int(np.count_nonzero(self._spatial))
        return (
            f"FixedSource(shape={self._spatial.shape}, nonzero_cells={nz}, "
            f"min={self._spatial.min():.6g}, max={self._spatial.max():.6g}, "
            f"energy_groups={self.energy_groups}, spectrum_file={self._spectrum_filename!r})"
        )
