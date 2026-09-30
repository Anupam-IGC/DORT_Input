"""Read DORT VARFLM flux output and form R-Z response fields.

The format follows section 4.6 (VARFLM) of the DORT manual. Each record has
Fortran sequential-unformatted length markers. Scalar flux is moment zero in
each J record; later moments and the group boundary-flux record are skipped.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence
import struct

import numpy as np


class DortFluxFormatError(ValueError):
    """The binary record layout or VARFLM metadata is inconsistent."""


@dataclass(frozen=True)
class FluxMetadata:
    """Mesh, group, and normalization data stored in a VARFLM file.

    Group indices are zero-based in Python. The first ``neutron_groups``
    groups are neutrons; remaining groups are photons. A row's I mesh is
    ``radial_edges(j)``. Distinct J rows may use different I meshes.
    """

    group_count: int
    neutron_groups: int
    axial_intervals: int
    max_radial_intervals: int
    boundary_directions: int
    boundary_set: int
    outer_iteration: int
    moments_per_group: np.ndarray
    radial_intervals_per_set: np.ndarray
    set_per_axial_interval: np.ndarray
    z_edges: np.ndarray
    r_edges_by_set: tuple[np.ndarray, ...]
    group_top_energies: np.ndarray
    lowest_energy: float
    last_neutron_energy: float
    eigenvalue: float
    effective_multiplication_factor: float
    power_watts: float
    byte_order: str
    record_marker_bytes: int
    real_bytes: int

    @property
    def photon_groups(self) -> int:
        """Number of photon groups."""
        return self.group_count - self.neutron_groups

    @property
    def shape(self) -> tuple[int, int, int]:
        """Shape of a complete scalar flux cube: (group, axial, radial)."""
        return self.group_count, self.axial_intervals, self.max_radial_intervals

    def radial_edges(self, axial_index: int) -> np.ndarray:
        """Return radial cell boundaries for the zero-based axial interval."""
        if not 0 <= axial_index < self.axial_intervals:
            raise IndexError("Axial interval index is out of range.")
        return self.r_edges_by_set[int(self.set_per_axial_interval[axial_index]) - 1]

    @property
    def regular_radial_mesh(self) -> bool:
        """Whether every axial row has the same I boundaries."""
        first = self.radial_edges(0)
        return all(np.array_equal(first, self.radial_edges(j))
                   for j in range(1, self.axial_intervals))


@dataclass(frozen=True)
class DoseFields:
    """Separate and combined dose fields, shaped (axial, radial).

    Values have the units implied by the supplied conversion coefficients
    and the explicit ``scale`` argument. Cells outside a J row's I mesh are
    NaN; they are never treated as physical zero-flux cells.
    """

    neutron: np.ndarray
    photon: np.ndarray
    total: np.ndarray


class _FortranRecords:
    def __init__(self, stream, endian: str, marker_bytes: int):
        self.stream = stream
        self.marker = struct.Struct(endian + ("i" if marker_bytes == 4 else "q"))
        self.number = 0
        position = stream.tell()
        stream.seek(0, 2)
        self.file_size = stream.tell()
        stream.seek(position)

    def read(self, expected: int | None = None, prefix: int | None = None) -> bytes:
        """Read a record, optionally retaining only its first ``prefix`` bytes."""
        self.number += 1
        raw = self.stream.read(self.marker.size)
        if len(raw) != self.marker.size:
            raise DortFluxFormatError(f"Missing record {self.number} length marker.")
        (size,) = self.marker.unpack(raw)
        if size < 0:
            raise DortFluxFormatError(
                f"Record {self.number} uses a split/subrecord format; it is not supported."
            )
        if expected is not None and size != expected:
            raise DortFluxFormatError(
                f"Record {self.number} has {size} data bytes; expected {expected}."
            )
        if size > self.file_size - self.stream.tell() - self.marker.size:
            raise DortFluxFormatError(f"Record {self.number} is truncated.")
        keep = size if prefix is None else prefix
        if keep < 0 or keep > size:
            raise DortFluxFormatError(f"Invalid prefix length for record {self.number}.")
        data = self.stream.read(keep)
        if len(data) != keep:
            raise DortFluxFormatError(f"Record {self.number} is truncated.")
        # Seek past unused flux moments, without storing them in memory.
        self.stream.seek(size - keep, 1)
        trailer = self.stream.read(self.marker.size)
        if len(trailer) != self.marker.size or self.marker.unpack(trailer)[0] != size:
            raise DortFluxFormatError(f"Record {self.number} has a missing/mismatched trailer.")
        return data


def _parse_header(records: _FortranRecords) -> FluxMetadata:
    records.read(prefix=0)  # identification (compiler-specific Hollerith encoding)
    records.read(prefix=0)  # label: date, user, case and 12 title fields
    control = np.frombuffer(records.read(expected=25 * 4), dtype=records.marker.format[0] + "i4")
    ig, neut, jm, lm, ima, mma, ism, imsism, isbt, iteration = map(int, control[:10])
    if not (0 < ig <= 100_000 and 0 <= neut <= ig and 0 < jm <= 10_000_000
            and 0 < lm <= 10_000 and 0 < ima <= 10_000_000 and mma >= 0
            and 0 < ism <= jm and ism <= imsism <= ism * ima
            and 1 <= isbt <= ism):
        raise DortFluxFormatError("Invalid VARFLM file-control values.")
    ints = np.frombuffer(records.read(expected=4 * (ig + ism + jm)),
                         dtype=records.marker.format[0] + "i4").astype(np.int64)
    moments = ints[:ig]
    counts = ints[ig:ig + ism]
    row_sets = ints[ig + ism:]
    if (np.any(moments < 1) or np.any(moments > lm) or np.any(counts < 1)
            or np.any(counts > ima) or int(counts.sum()) != imsism
            or np.any(row_sets < 1) or np.any(row_sets > ism)
            or int(counts.max()) != ima):
        raise DortFluxFormatError("Invalid VARFLM moment or I-set parameters.")
    real_count = jm + imsism + ism + ig + 20
    real_record = records.read()
    if len(real_record) not in (real_count * 4, real_count * 8):
        raise DortFluxFormatError(
            f"Real-parameter record has {len(real_record)} bytes; "
            f"expected {real_count * 4} or {real_count * 8}."
        )
    real_bytes = len(real_record) // real_count
    values = np.frombuffer(real_record,
                           dtype=records.marker.format[0] + f"f{real_bytes}").copy()
    z = values[:jm + 1]
    at = jm + 1
    radii = []
    for count in counts:
        radii.append(values[at:at + count + 1].copy())
        at += count + 1
    tops = values[at:at + ig].copy()
    at += ig
    if not np.all(np.isfinite(z)) or np.any(np.diff(z) <= 0):
        raise DortFluxFormatError("Invalid or non-monotonic axial boundaries.")
    if any(not np.all(np.isfinite(r)) or np.any(np.diff(r) <= 0) for r in radii):
        raise DortFluxFormatError("Invalid or non-monotonic radial boundaries.")
    return FluxMetadata(
        group_count=ig, neutron_groups=neut, axial_intervals=jm,
        max_radial_intervals=ima, boundary_directions=mma,
        boundary_set=isbt, outer_iteration=iteration,
        moments_per_group=moments, radial_intervals_per_set=counts,
        set_per_axial_interval=row_sets, z_edges=z, r_edges_by_set=tuple(radii),
        group_top_energies=tops, lowest_energy=float(values[at]),
        last_neutron_energy=float(values[at + 1]),
        eigenvalue=float(values[at + 2]),
        effective_multiplication_factor=float(values[at + 4]),
        power_watts=float(values[at + 5]),
        byte_order=records.marker.format[0],
        record_marker_bytes=records.marker.size, real_bytes=real_bytes,
    )


class DortFluxReader:
    """Reader for a DORT ``dortflux.bin`` VARFLM output file.

    Record-marker size and byte order are detected from the five header
    records. No geometry or group counts need be entered by hand. Flux units
    and normalization are those of the DORT run; no implicit scaling occurs.

    Parameters
    ----------
    path : str or Path
        VARFLM file written on the ``NTFOG`` output unit.
    byte_order : {'auto', 'little', 'big'}, optional
        Override when autodetection is ambiguous.
    record_marker_bytes : {None, 4, 8}, optional
        Length of the Fortran sequential record markers.
    """

    def __init__(self, path: str | Path, *, byte_order: str = "auto",
                 record_marker_bytes: int | None = None):
        self.path = Path(path)
        if byte_order not in ("auto", "little", "big"):
            raise ValueError("byte_order must be 'auto', 'little' or 'big'.")
        if record_marker_bytes not in (None, 4, 8):
            raise ValueError("record_marker_bytes must be 4 or 8.")
        orders = ("<", ">") if byte_order == "auto" else (
            ("<",) if byte_order == "little" else (">",))
        widths = (4, 8) if record_marker_bytes is None else (record_marker_bytes,)
        errors = []
        with self.path.open("rb") as stream:
            for order in orders:
                for width in widths:
                    try:
                        stream.seek(0)
                        records = _FortranRecords(stream, order, width)
                        metadata = _parse_header(records)
                    except DortFluxFormatError as exc:
                        errors.append(f"{order}, {width}-byte markers: {exc}")
                    else:
                        self.metadata = metadata
                        self._data_offset = stream.tell()
                        return
        raise DortFluxFormatError("Not a supported VARFLM file. " + "; ".join(errors))

    def _groups(self, groups: Sequence[int] | slice | None) -> list[int]:
        if groups is None:
            return list(range(self.metadata.group_count))
        if isinstance(groups, slice):
            return list(range(self.metadata.group_count))[groups]
        indices = list(groups)
        if any(not isinstance(g, (int, np.integer)) or isinstance(g, (bool, np.bool_))
               or g < 0 or g >= self.metadata.group_count for g in indices):
            raise ValueError("Group indices must be zero-based integers within the file.")
        if len(set(indices)) != len(indices):
            raise ValueError("Repeated group indices are not allowed.")
        return indices

    def _visit(self, groups: set[int], visit: Callable[[int, int, np.ndarray], None]) -> None:
        m = self.metadata
        real = np.dtype(m.byte_order + f"f{m.real_bytes}")
        with self.path.open("rb") as stream:
            stream.seek(self._data_offset)
            records = _FortranRecords(stream, m.byte_order, m.record_marker_bytes)
            for g in range(m.group_count):
                for j, iset in enumerate(m.set_per_axial_interval):
                    n = int(m.radial_intervals_per_set[iset - 1])
                    expected = n * int(m.moments_per_group[g]) * m.real_bytes
                    scalar = n * m.real_bytes if g in groups else 0
                    data = records.read(expected=expected, prefix=scalar)
                    if scalar:
                        visit(g, j, np.frombuffer(data, dtype=real))
                boundary_count = m.boundary_directions * (
                    m.axial_intervals + m.radial_intervals_per_set[m.boundary_set - 1]
                )
                records.read(expected=int(boundary_count) * m.real_bytes, prefix=0)
            if stream.read(1):
                raise DortFluxFormatError("Unexpected data after the final group record.")

    def read_scalar_flux(self, groups: Sequence[int] | slice | None = None) -> np.ndarray:
        """Read selected scalar groups as ``[group, axial, radial]``.

        ``groups`` uses zero-based file indices; the returned first axis uses
        the requested order. Padding in variable I meshes is NaN. This method
        loads the selected groups in memory. Use :meth:`weighted_sums` for
        integrated flux or dose without allocating the complete flux cube.
        """
        indices = self._groups(groups)
        m = self.metadata
        flux = np.full((len(indices), m.axial_intervals, m.max_radial_intervals),
                       np.nan, dtype=np.float32 if m.real_bytes == 4 else np.float64)
        positions = {g: idx for idx, g in enumerate(indices)}

        def visit(g: int, j: int, row: np.ndarray) -> None:
            flux[positions[g], j, :len(row)] = row

        self._visit(set(indices), visit)
        return flux

    def weighted_sums(self, weights: Sequence[float] | np.ndarray) -> np.ndarray:
        """Stream weighted scalar-flux sums over groups.

        One row of weights returns ``[axial, radial]``; a 2-D array with shape
        ``[field, group]`` returns ``[field, axial, radial]``. Each weight row
        must cover every group in file order. No physical units are imposed.
        """
        m = self.metadata
        values = np.asarray(weights, dtype=np.float64)
        if values.ndim not in (1, 2) or values.shape[-1] != m.group_count:
            raise ValueError(f"weights must have {m.group_count} groups on the last axis.")
        if not np.all(np.isfinite(values)):
            raise ValueError("weights must be finite.")
        one = values.ndim == 1
        values = np.atleast_2d(values)
        result = np.zeros((values.shape[0], m.axial_intervals,
                           m.max_radial_intervals), dtype=np.float64)
        nonzero = set(map(int, np.flatnonzero(np.any(values != 0, axis=0))))

        def visit(g: int, j: int, row: np.ndarray) -> None:
            result[:, j, :len(row)] += values[:, g, None] * row[None, :]

        self._visit(nonzero, visit)
        for j, iset in enumerate(m.set_per_axial_interval):
            result[:, j, m.radial_intervals_per_set[iset - 1]:] = np.nan
        return result[0] if one else result

    def integrated_flux(self) -> DoseFields:
        """Sum neutron, photon, and all scalar-flux groups separately."""
        m = self.metadata
        weights = np.zeros((2, m.group_count))
        weights[0, :m.neutron_groups] = 1.0
        weights[1, m.neutron_groups:] = 1.0
        neutron, photon = self.weighted_sums(weights)
        return DoseFields(neutron, photon, neutron + photon)

    def dose_rate(self, neutron_factors: Sequence[float], photon_factors: Sequence[float],
                  *, scale: float = 1.0) -> DoseFields:
        """Apply groupwise flux-to-dose factors, streaming the file once.

        Factor lengths must match NEUT and IGM-NEUT in file order. DORT output
        flux times the factors gives the native response units; ``scale`` is
        an explicit unit conversion (e.g. 3600 for per-second to per-hour).
        """
        m = self.metadata
        n = np.asarray(neutron_factors, dtype=np.float64)
        p = np.asarray(photon_factors, dtype=np.float64)
        if n.shape != (m.neutron_groups,) or p.shape != (m.photon_groups,):
            raise ValueError(
                f"Expected {m.neutron_groups} neutron and {m.photon_groups} photon factors."
            )
        if not np.all(np.isfinite(n)) or not np.all(np.isfinite(p)):
            raise ValueError("Dose conversion factors must be finite.")
        if not np.isfinite(scale):
            raise ValueError("scale must be finite.")
        weights = np.zeros((2, m.group_count))
        weights[0, :m.neutron_groups] = n * scale
        weights[1, m.neutron_groups:] = p * scale
        neutron, photon = self.weighted_sums(weights)
        return DoseFields(neutron, photon, neutron + photon)

    def plot_field(self, field: np.ndarray, **kwargs):
        """Plot an R-Z scalar field using the mesh stored in the file."""
        return plot_rz_field(self.metadata, field, **kwargs)

    def write_rz_csv(self, field: np.ndarray, path: str | Path) -> Path:
        """Write one scalar flux or dose field as ``R,Z,Value`` cell centres."""
        return write_rz_csv(self.metadata, field, path)


def write_rz_csv(metadata: FluxMetadata, field: np.ndarray,
                 path: str | Path) -> Path:
    """Export a two-dimensional DORT field in Origin-compatible XYZ form.

    Each row contains the centre ``R`` and ``Z`` of one active cell, then its
    value. The input field is indexed ``[axial, radial]`` and may be a selected
    group, an integrated flux, or a dose result. Padded cells in variable
    radial meshes are omitted; actual cell values are written unchanged.
    Coordinates retain the mesh units stored by DORT. No interpolation,
    normalization, or dose conversion is performed.

    Parameters
    ----------
    metadata : FluxMetadata
        Mesh metadata from :class:`DortFluxReader`.
    field : numpy.ndarray
        Scalar array with shape ``(axial_intervals, max_radial_intervals)``.
    path : str or pathlib.Path
        Destination CSV path. Its parent directory must exist.

    Returns
    -------
    pathlib.Path
        Path of the CSV file with columns ``R,Z,Value``.
    """
    values = np.asarray(field)
    expected = (metadata.axial_intervals, metadata.max_radial_intervals)
    if values.shape != expected:
        raise ValueError(f"field must have shape {expected} (axial, radial).")

    output = Path(path)
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(("R", "Z", "Value"))
        for j in range(metadata.axial_intervals):
            zc = (float(metadata.z_edges[j]) + float(metadata.z_edges[j + 1])) / 2
            r_edges = metadata.radial_edges(j)
            for i in range(len(r_edges) - 1):
                rc = (float(r_edges[i]) + float(r_edges[i + 1])) / 2
                writer.writerow((format(rc, ".17g"), format(zc, ".17g"),
                                 format(float(values[j, i]), ".17g")))
    return output


def load_group_factors(path: str | Path, group_count: int) -> np.ndarray:
    """Read a text file with one groupwise conversion factor per line."""
    values = np.atleast_1d(np.loadtxt(path, dtype=np.float64))
    if values.shape != (group_count,) or not np.all(np.isfinite(values)):
        raise ValueError(f"Expected exactly {group_count} finite values in {path}.")
    return values


def plot_rz_field(metadata: FluxMetadata, field: np.ndarray, *, ax=None,
                  label: str = "", log: bool = False, cmap: str = "viridis",
                  colorbar: bool = True, **kwargs):
    """Draw an R-Z field with a single color scale, including variable I sets.

    Return ``(figure, axes)``. For logarithmic plots, nonpositive values are
    masked. ``kwargs`` are passed to ``pcolormesh`` on regular meshes and to
    ``PolyCollection`` on variable meshes.
    """
    import matplotlib.pyplot as plt
    from matplotlib.colors import LogNorm, Normalize
    from matplotlib.collections import PolyCollection

    data = np.asarray(field, dtype=np.float64)
    if data.shape != (metadata.axial_intervals, metadata.max_radial_intervals):
        raise ValueError("field must have shape (axial_intervals, max_radial_intervals).")
    if ax is None:
        fig, ax = plt.subplots(figsize=(9, 6))
    else:
        fig = ax.figure
    finite = data[np.isfinite(data) & ((data > 0) if log else np.ones_like(data, bool))]
    if not len(finite):
        raise ValueError("No finite values available for the requested color scale.")
    norm = (LogNorm(vmin=float(finite.min()), vmax=float(finite.max())) if log
            else Normalize(vmin=float(finite.min()), vmax=float(finite.max())))
    if metadata.regular_radial_mesh:
        mesh = ax.pcolormesh(metadata.radial_edges(0), metadata.z_edges,
                             np.ma.masked_invalid(data) if not log else
                             np.ma.masked_less_equal(data, 0), shading="flat",
                             norm=norm, cmap=cmap, **kwargs)
    else:
        vertices, colors = [], []
        for j in range(metadata.axial_intervals):
            radii = metadata.radial_edges(j)
            for i in range(len(radii) - 1):
                value = data[j, i]
                if not np.isfinite(value) or (log and value <= 0):
                    continue
                vertices.append([(radii[i], metadata.z_edges[j]),
                                 (radii[i + 1], metadata.z_edges[j]),
                                 (radii[i + 1], metadata.z_edges[j + 1]),
                                 (radii[i], metadata.z_edges[j + 1])])
                colors.append(value)
        mesh = PolyCollection(vertices, array=np.asarray(colors), norm=norm,
                              cmap=cmap, edgecolors="none", **kwargs)
        ax.add_collection(mesh)
        ax.autoscale_view()
    ax.set_xlabel("R")
    ax.set_ylabel("Z")
    if colorbar:
        fig.colorbar(mesh, ax=ax, label=label)
    return fig, ax
