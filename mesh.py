"""Mesh construction utilities for DORT R-Z input preparation.

The module defines one-dimensional mesh axes and combines them into a
two-dimensional cylindrical R-Z mesh.  It contains no material, region, or
DORT/FIDO serialization logic.

The array convention used by the project is ``(nz, nr)``: axial index first,
radial index second.

Examples
--------
>>> from mesh import Mesh
>>> mesh = Mesh()
>>> mesh.r.add_segment(0.0, 100.0, step=10.0)
MeshAxis(name='R', n_cells=10, bounds=(0, 100))
>>> mesh.z.add_segment(-50.0, 50.0, n_cells=20)
MeshAxis(name='Z', n_cells=20, bounds=(-50, 50))
>>> mesh.shape
(20, 10)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

import numpy as np


def _as_1d_float_array(values: Iterable[float]) -> np.ndarray:
    """Convert an iterable of mesh coordinates to a validated float array.
    
    Parameters
    ----------
    values : iterable of float
        Candidate mesh-edge coordinates.
    
    Returns
    -------
    numpy.ndarray
        One-dimensional finite floating-point array.
    
    Raises
    ------
    ValueError
        If the result is not one-dimensional, contains fewer than two entries, or
        contains a non-finite value.
    """
    array = np.asarray(list(values), dtype=float)

    if array.ndim != 1:
        raise ValueError("Mesh edges must be one-dimensional.")

    if array.size < 2:
        raise ValueError("At least two mesh edges are required.")

    if not np.all(np.isfinite(array)):
        raise ValueError("Mesh edges must contain only finite numbers.")

    return array


@dataclass
class MeshAxis:
    """Represent one one-dimensional mesh axis.
    
    Parameters
    ----------
    name : str
        Human-readable axis name, normally ``"R"`` or ``"Z"``.
    
    Notes
    -----
    Segments are appended sequentially.  Once the axis contains edges, the first
    coordinate of every new segment must coincide with the current last edge. This
    prevents accidental gaps and overlaps between adjacent mesh segments.
    """

    name: str
    _edges: np.ndarray = field(
        default_factory=lambda: np.array([], dtype=float),
        init=False,
        repr=False,
    )

    # Relative/absolute tolerance used when comparing floating-point edges.
    _rtol: float = field(default=1.0e-10, init=False, repr=False)
    _atol: float = field(default=1.0e-12, init=False, repr=False)

    @property
    def edges(self) -> np.ndarray:
        """Return the mesh-edge coordinates.
        
        Returns
        -------
        numpy.ndarray
            Copy of the edge-coordinate array.
        """
        return self._edges.copy()

    @property
    def centers(self) -> np.ndarray:
        """Return mesh-cell centre coordinates.
        
        Returns
        -------
        numpy.ndarray
            Cell-centre coordinates. An empty array is returned when the axis has
            fewer than two edges.
        """
        if self._edges.size < 2:
            return np.array([], dtype=float)

        return 0.5 * (self._edges[:-1] + self._edges[1:])

    @property
    def widths(self) -> np.ndarray:
        """Return mesh-cell widths.
        
        Returns
        -------
        numpy.ndarray
            Differences between consecutive mesh edges.
        """
        if self._edges.size < 2:
            return np.array([], dtype=float)

        return np.diff(self._edges)

    @property
    def n_cells(self) -> int:
        """Return the number of mesh intervals.
        
        Returns
        -------
        int
            Number of cells on the axis.
        """
        return max(self._edges.size - 1, 0)

    @property
    def bounds(self) -> tuple[float, float] | None:
        """Return the minimum and maximum coordinate.
        
        Returns
        -------
        tuple of float or None
            ``(minimum, maximum)`` when the axis is defined; otherwise ``None``.
        """
        if self._edges.size == 0:
            return None

        return float(self._edges[0]), float(self._edges[-1])

    @property
    def is_defined(self) -> bool:
        """Return whether the axis contains at least one mesh cell.
        
        Returns
        -------
        bool
            ``True`` when at least two mesh edges have been defined.
        """
        return self.n_cells > 0

    def clear(self) -> None:
        """Remove all mesh edges from the axis.
        
        Returns
        -------
        None
        """
        self._edges = np.array([], dtype=float)

    def add_segment(
        self,
        start: float,
        end: float,
        *,
        step: float | None = None,
        n_cells: int | None = None,
    ) -> "MeshAxis":
        """Append a uniformly spaced mesh segment.
        
        Exactly one of ``step`` or ``n_cells`` must be supplied.
        
        Parameters
        ----------
        start : float
            Coordinate of the first edge of the segment.
        end : float
            Coordinate of the final edge of the segment. Must be greater than
            ``start``.
        step : float, optional
            Requested uniform cell width. The interval must be divisible by this
            value within the mesh floating-point tolerance.
        n_cells : int, optional
            Number of equal-width cells in the segment.
        
        Returns
        -------
        MeshAxis
            The modified axis, allowing chained calls.
        
        Raises
        ------
        ValueError
            If the bounds are invalid, the new segment is not contiguous with the
            existing axis, neither/both spacing options are supplied, ``step`` is not
            positive, ``step`` does not divide the interval, or ``n_cells`` is invalid.
        
        Examples
        --------
        >>> from mesh import MeshAxis
        >>> r = MeshAxis("R")
        >>> r.add_segment(0.0, 100.0, step=5.0)
        MeshAxis(name='R', n_cells=20, bounds=(0, 100))
        >>> r.add_segment(100.0, 150.0, n_cells=10)
        MeshAxis(name='R', n_cells=30, bounds=(0, 150))
        
        Notes
        -----
        Requiring exact subdivision avoids silently creating a shortened final cell.
        Use :meth:`add_edges` when an intentionally irregular final interval is
        required.
        """
        start = float(start)
        end = float(end)

        if not np.isfinite(start) or not np.isfinite(end):
            raise ValueError(f"{self.name}: segment bounds must be finite.")

        if end <= start:
            raise ValueError(
                f"{self.name}: segment end ({end}) must be greater "
                f"than start ({start})."
            )

        if (step is None) == (n_cells is None):
            raise ValueError(
                f"{self.name}: specify exactly one of 'step' or 'n_cells'."
            )

        if self._edges.size:
            if not np.isclose(
                start,
                self._edges[-1],
                rtol=self._rtol,
                atol=self._atol,
            ):
                raise ValueError(
                    f"{self.name}: new segment starts at {start}, but the "
                    f"current axis ends at {self._edges[-1]}. Segments must "
                    "be continuous."
                )

            # Replace a numerically equivalent start by the exact stored edge.
            start = float(self._edges[-1])

        if step is not None:
            step = float(step)

            if not np.isfinite(step) or step <= 0.0:
                raise ValueError(f"{self.name}: step must be a positive number.")

            exact_cells = (end - start) / step
            rounded_cells = int(round(exact_cells))

            if rounded_cells < 1 or not np.isclose(
                exact_cells,
                rounded_cells,
                rtol=self._rtol,
                atol=self._atol,
            ):
                raise ValueError(
                    f"{self.name}: step={step} does not divide the interval "
                    f"[{start}, {end}] exactly. Use a compatible step or "
                    "specify n_cells instead."
                )

            n_cells = rounded_cells

        else:
            if isinstance(n_cells, bool) or int(n_cells) != n_cells:
                raise ValueError(f"{self.name}: n_cells must be an integer.")

            n_cells = int(n_cells)

            if n_cells < 1:
                raise ValueError(f"{self.name}: n_cells must be at least 1.")

        new_edges = np.linspace(start, end, n_cells + 1, dtype=float)

        if self._edges.size == 0:
            self._edges = new_edges
        else:
            # Skip the first point because it duplicates the current last edge.
            self._edges = np.concatenate((self._edges, new_edges[1:]))

        self.validate()
        return self

    def add_edges(self, values: Iterable[float]) -> "MeshAxis":
        """Append explicitly supplied mesh edges.
        
        Parameters
        ----------
        values : iterable of float
            Strictly increasing edge coordinates. If the axis is already defined, the
            first supplied value must equal the current final edge within tolerance.
        
        Returns
        -------
        MeshAxis
            The modified axis.
        
        Raises
        ------
        ValueError
            If the supplied coordinates are invalid, not strictly increasing, or not
            contiguous with the existing axis.
        """
        new_edges = _as_1d_float_array(values)

        if not np.all(np.diff(new_edges) > 0.0):
            raise ValueError(
                f"{self.name}: explicit mesh edges must be strictly increasing."
            )

        if self._edges.size == 0:
            self._edges = new_edges
        else:
            if not np.isclose(
                new_edges[0],
                self._edges[-1],
                rtol=self._rtol,
                atol=self._atol,
            ):
                raise ValueError(
                    f"{self.name}: explicit edges begin at {new_edges[0]}, "
                    f"but the current axis ends at {self._edges[-1]}."
                )

            self._edges = np.concatenate((self._edges, new_edges[1:]))

        self.validate()
        return self

    def validate(self) -> None:
        """Validate the current axis definition.
        
        Returns
        -------
        None
        
        Raises
        ------
        ValueError
            If the edge array is not one-dimensional, contains non-finite values,
            contains fewer than two coordinates after definition, or is not strictly
            increasing.
        """
        if self._edges.size == 0:
            return

        if self._edges.ndim != 1:
            raise ValueError(f"{self.name}: mesh edges must be one-dimensional.")

        if not np.all(np.isfinite(self._edges)):
            raise ValueError(f"{self.name}: mesh edges contain non-finite values.")

        if self._edges.size < 2:
            raise ValueError(f"{self.name}: at least two mesh edges are required.")

        widths = np.diff(self._edges)

        if not np.all(widths > 0.0):
            raise ValueError(
                f"{self.name}: mesh edges must be strictly increasing."
            )

    def __len__(self) -> int:
        return self.n_cells

    def __repr__(self) -> str:
        if not self.is_defined:
            return f"MeshAxis(name={self.name!r}, empty=True)"

        lo, hi = self.bounds
        return (
            f"MeshAxis(name={self.name!r}, n_cells={self.n_cells}, "
            f"bounds=({lo:g}, {hi:g}))"
        )


@dataclass
class Mesh:
    """Represent a two-dimensional cylindrical R-Z mesh.
    
    Attributes
    ----------
    r : MeshAxis
        Radial mesh axis.
    z : MeshAxis
        Axial mesh axis.
    
    Notes
    -----
    All project maps use shape ``(nz, nr)`` so that the first array index is the
    Z index and the second is the R index.
    """

    r: MeshAxis = field(default_factory=lambda: MeshAxis("R"))
    z: MeshAxis = field(default_factory=lambda: MeshAxis("Z"))

    @property
    def shape(self) -> tuple[int, int]:
        """Return the project-standard two-dimensional map shape.
        
        Returns
        -------
        tuple of int
            ``(nz, nr)``.
        """
        return self.z.n_cells, self.r.n_cells

    @property
    def n_cells(self) -> int:
        """Return the total number of R-Z fine-mesh cells.
        
        Returns
        -------
        int
            Product of the radial and axial cell counts.
        """
        return self.r.n_cells * self.z.n_cells

    def validate(self) -> None:
        """Validate both mesh axes and require both to be defined.
        
        Returns
        -------
        None
        
        Raises
        ------
        ValueError
            If either axis definition is invalid or if R or Z has not been defined.
        """
        self.r.validate()
        self.z.validate()

        if not self.r.is_defined:
            raise ValueError("R mesh has not been defined.")

        if not self.z.is_defined:
            raise ValueError("Z mesh has not been defined.")

    def __repr__(self) -> str:
        return (
            "Mesh("
            f"nr={self.r.n_cells}, "
            f"nz={self.z.n_cells}, "
            f"shape={self.shape}"
            ")"
        )


if __name__ == "__main__":
    # Small demonstration / smoke test.
    mesh = Mesh()

    mesh.r.add_segment(0.0, 100.0, step=10.0)
    mesh.r.add_segment(100.0, 140.0, step=5.0)
    mesh.r.add_segment(140.0, 300.0, step=20.0)

    mesh.z.add_segment(-100.0, -50.0, step=10.0)
    mesh.z.add_segment(-50.0, 50.0, step=5.0)
    mesh.z.add_segment(50.0, 150.0, step=10.0)

    mesh.validate()

    print(mesh)
    print()
    print("R edges   :", mesh.r.edges)
    print("R centers :", mesh.r.centers)
    print("R widths  :", mesh.r.widths)
    print()
    print("Z edges   :", mesh.z.edges)
    print("Z centers :", mesh.z.centers)
    print("Z widths  :", mesh.z.widths)
    print()
    print("Map shape :", mesh.shape)
    print("Cell count:", mesh.n_cells)
