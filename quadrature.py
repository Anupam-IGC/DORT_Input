"""
quadrature.py
=============

Modern quadrature generation for DORT two-dimensional discrete-ordinates
calculations.

The module provides two complementary quadrature families:

``legacy``
    Reproduces the numerical construction used by the historical DOQDP
    generator supplied with DORT.  This is useful for reproducing established
    S_N sets and legacy calculations.

``product``
    A modern positive-weight Gauss product quadrature intended for higher
    angular resolution.  It does not solve the increasingly ill-conditioned
    moment-fitting system used by the legacy generator.

The public API deliberately uses descriptive Python names instead of the
short variable names and integer flags used in the original Fortran code.

DORT arrays
-----------
A generated :class:`QuadratureSet` can be written directly as:

``81*``
    Directional weights.

``82*``
    Radial/first-dimension direction cosine, conventionally called MU in
    DORT documentation.

``83*``
    Axial/second-dimension direction cosine, conventionally called ETA in
    DORT documentation.

For R-Z geometry, the first dimension is R and the second dimension is Z.

Recommended usage
-----------------
Reproduce a conventional legacy S8 set::

    from quadrature import generate_legacy_quadrature

    quadrature = generate_legacy_quadrature(
        order=8,
        symmetry="half",
    )

Generate a robust higher-resolution product set::

    from quadrature import generate_product_quadrature

    quadrature = generate_product_quadrature(
        polar_order=24,
        azimuthal_order=32,
    )

Inspect and write the set::

    print(quadrature.summary_text())
    print(quadrature.validation_text())
    quadrature.write_dort("quadrature.inc")

Notes on high-order calculations
--------------------------------
Increasing the order of the historical moment-fitted quadrature does not
necessarily produce a numerically better set.  At sufficiently high order,
the legacy coefficient matrix becomes ill-conditioned and negative weights
can appear.

The product family avoids that solve.  It uses:

* Gauss-Legendre integration in the axial cosine;
* Gauss-Legendre integration in azimuth over the half-sphere represented by
  a two-dimensional DORT calculation;
* positive integration weights;
* an explicit zero-weight initiating direction for every axial-cosine level;
* increasing radial cosine within every level.

The product family is therefore the recommended choice when the goal is
higher angular resolution rather than exact reproduction of an old DOQDP set.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np


# ===========================================================================
# Public result/validation classes
# ===========================================================================


@dataclass(frozen=True)
class QuadratureValidation:
    """
    Result of validating a DORT quadrature set.

    Parameters
    ----------
    valid
        ``True`` when no validation errors were detected.
    errors
        Conditions that make the set unsuitable for DORT output.
    warnings
        Non-fatal numerical or quality concerns.
    weight_sum
        Sum of the final directional weights.
    minimum_nonzero_weight
        Smallest weight among actual integration directions.  Zero-weight
        level initiators are excluded.
    maximum_sphere_error
        Maximum positive violation of
        ``radial_cosine**2 + axial_cosine**2 <= 1``.
    maximum_level_current
        Largest absolute value of the weighted radial cosine summed within
        one axial-cosine level.
    maximum_moment_error
        Largest error among the reference angular moments checked.
    """

    valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    weight_sum: float
    minimum_nonzero_weight: float
    maximum_sphere_error: float
    maximum_level_current: float
    maximum_moment_error: float

    def text(self) -> str:
        """Return a human-readable validation report."""
        lines = [
            f"Valid quadrature          : {self.valid}",
            f"Weight sum                : {self.weight_sum:.15g}",
            f"Minimum nonzero weight    : {self.minimum_nonzero_weight:.6E}",
            f"Maximum sphere error      : {self.maximum_sphere_error:.6E}",
            f"Maximum level current     : {self.maximum_level_current:.6E}",
            f"Maximum moment error      : {self.maximum_moment_error:.6E}",
        ]

        if self.errors:
            lines.extend(["", "Errors:"])
            lines.extend(f"  - {message}" for message in self.errors)

        if self.warnings:
            lines.extend(["", "Warnings:"])
            lines.extend(f"  - {message}" for message in self.warnings)

        return "\n".join(lines)


@dataclass(frozen=True)
class QuadratureSet:
    """
    A completed DORT quadrature set.

    Parameters
    ----------
    family
        Name of the generation method, currently ``"legacy"`` or
        ``"product"``.
    radial_cosine
        First-dimension direction cosine.  In DORT documentation this is MU.
    axial_cosine
        Second-dimension direction cosine.  In DORT documentation this is ETA.
    weights
        Directional integration weights.  Level-initiating directions have
        zero weight.
    reference_moments
        Moment pairs ``(radial_power, axial_power)`` used for numerical
        verification.
    metadata
        Generation-specific information.
    """

    family: str
    radial_cosine: np.ndarray
    axial_cosine: np.ndarray
    weights: np.ndarray
    reference_moments: tuple[tuple[int, int], ...]
    metadata: dict[str, object]

    # ------------------------------------------------------------------
    # Familiar DORT aliases
    # ------------------------------------------------------------------

    @property
    def mu(self) -> np.ndarray:
        """
        Alias for :attr:`radial_cosine`.

        ``mu`` is retained only because it is standard DORT terminology.
        New application code can use ``radial_cosine`` for clarity.
        """
        return self.radial_cosine.copy()

    @property
    def eta(self) -> np.ndarray:
        """
        Alias for :attr:`axial_cosine`.

        ``eta`` is retained only because it is standard DORT terminology.
        """
        return self.axial_cosine.copy()

    # ------------------------------------------------------------------
    # Basic properties
    # ------------------------------------------------------------------

    @property
    def direction_count(self) -> int:
        """Total number of DORT directions, including zero-weight initiators."""
        return int(self.weights.size)

    @property
    def integration_direction_count(self) -> int:
        """Number of nonzero-weight integration directions."""
        return int(np.count_nonzero(np.abs(self.weights) > 1.0e-15))

    @property
    def zero_weight_direction_count(self) -> int:
        """Number of zero-weight level-initiating directions."""
        return self.direction_count - self.integration_direction_count

    @property
    def weight_sum(self) -> float:
        """Sum of all final directional weights."""
        return float(np.sum(self.weights))

    @property
    def third_cosine(self) -> np.ndarray:
        """
        Magnitude of the unrepresented third direction cosine.

        For an R-Z calculation this is the azimuthal direction-cosine
        magnitude.
        """
        remainder = (
            1.0
            - self.radial_cosine * self.radial_cosine
            - self.axial_cosine * self.axial_cosine
        )
        return np.sqrt(np.clip(remainder, 0.0, None))

    @property
    def axial_level_count(self) -> int:
        """Number of contiguous axial-cosine levels."""
        return len(_find_level_slices(self.axial_cosine))

    # ------------------------------------------------------------------
    # Moment checks
    # ------------------------------------------------------------------

    def moment_value(self, radial_power: int, axial_power: int) -> float:
        """
        Numerically integrate one angular monomial.

        The weights are normalized so that the zeroth moment is 1.
        """
        return float(
            np.sum(
                self.weights
                * self.radial_cosine**radial_power
                * self.axial_cosine**axial_power
            )
        )

    def moment_table(self) -> list[tuple[int, int, float, float, float]]:
        """
        Return reference-moment results.

        Each tuple contains::

            (radial_power, axial_power, calculated, analytical, error)
        """
        rows = []

        for radial_power, axial_power in self.reference_moments:
            analytical = _analytical_sphere_moment(
                radial_power,
                axial_power,
            )
            calculated = self.moment_value(
                radial_power,
                axial_power,
            )
            rows.append(
                (
                    radial_power,
                    axial_power,
                    calculated,
                    analytical,
                    calculated - analytical,
                )
            )

        return rows

    @property
    def maximum_moment_error(self) -> float:
        """Largest absolute error among the configured reference moments."""
        rows = self.moment_table()

        if not rows:
            return 0.0

        return max(abs(row[4]) for row in rows)

    def moment_table_text(self) -> str:
        """Return a formatted table of angular-moment checks."""
        lines = [
            " radial  axial          calculated              analytical"
            "                error",
            "--------------------------------------------------------------------------"
            "----------------",
        ]

        for (
            radial_power,
            axial_power,
            calculated,
            analytical,
            error,
        ) in self.moment_table():
            lines.append(
                f"{radial_power:7d} {axial_power:6d} "
                f"{calculated:20.12E} "
                f"{analytical:20.12E} "
                f"{error:14.5E}"
            )

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(
        self,
        *,
        tolerance: float = 1.0e-11,
        moment_tolerance: float = 1.0e-8,
        require_positive_weights: bool | None = None,
    ) -> QuadratureValidation:
        """
        Validate DORT ordering, normalization, geometry and angular moments.

        Parameters
        ----------
        tolerance
            Numerical tolerance for geometry, ordering, normalization and
            level-current checks.
        moment_tolerance
            Warning threshold for the reference moment errors.
        require_positive_weights
            If ``True``, negative integration weights are treated as errors.
            If ``False``, they are only reported as warnings.  If omitted,
            product quadratures require positive weights while legacy
            quadratures only warn about negative weights.

        Returns
        -------
        QuadratureValidation
            Structured validation result.
        """
        if tolerance <= 0.0:
            raise ValueError("tolerance must be positive.")

        if moment_tolerance <= 0.0:
            raise ValueError("moment_tolerance must be positive.")

        if require_positive_weights is None:
            require_positive_weights = self.family == "product"

        errors: list[str] = []
        warnings: list[str] = []

        radial = np.asarray(self.radial_cosine, dtype=float)
        axial = np.asarray(self.axial_cosine, dtype=float)
        weights = np.asarray(self.weights, dtype=float)

        if not (
            radial.ndim == axial.ndim == weights.ndim == 1
            and radial.size == axial.size == weights.size
        ):
            errors.append(
                "radial_cosine, axial_cosine and weights must be "
                "one-dimensional arrays of equal length."
            )

            return QuadratureValidation(
                valid=False,
                errors=tuple(errors),
                warnings=tuple(warnings),
                weight_sum=float("nan"),
                minimum_nonzero_weight=float("nan"),
                maximum_sphere_error=float("nan"),
                maximum_level_current=float("nan"),
                maximum_moment_error=float("nan"),
            )

        if radial.size == 0:
            errors.append("Quadrature contains no directions.")

        if not (
            np.all(np.isfinite(radial))
            and np.all(np.isfinite(axial))
            and np.all(np.isfinite(weights))
        ):
            errors.append("Quadrature contains non-finite values.")

        weight_sum = float(np.sum(weights))

        if not np.isclose(weight_sum, 1.0, rtol=tolerance, atol=tolerance):
            errors.append(
                f"Directional weights sum to {weight_sum:.15g}; "
                "DORT full-set normalization should be 1."
            )

        nonzero_mask = np.abs(weights) > tolerance

        if np.any(nonzero_mask):
            minimum_nonzero_weight = float(np.min(weights[nonzero_mask]))
        else:
            minimum_nonzero_weight = 0.0
            errors.append("Quadrature has no nonzero integration weights.")

        negative_count = int(np.count_nonzero(weights < -tolerance))

        if negative_count:
            message = (
                f"{negative_count} integration direction(s) have negative "
                f"weights; minimum = {float(np.min(weights)):.6E}."
            )

            if require_positive_weights:
                errors.append(message)
            else:
                warnings.append(message)

        sphere_residual = radial * radial + axial * axial - 1.0
        maximum_sphere_error = max(
            0.0,
            float(np.max(sphere_residual)) if sphere_residual.size else 0.0,
        )

        if maximum_sphere_error > tolerance:
            errors.append(
                "At least one direction violates "
                "radial_cosine^2 + axial_cosine^2 <= 1."
            )

        level_slices = _find_level_slices(axial, tolerance=tolerance)

        if level_slices:
            level_values = np.array(
                [float(axial[level.start]) for level in level_slices]
            )

            # DORT requires all negative axial-cosine levels to precede all
            # positive levels.  The historical DOQDP set does not require
            # the magnitudes within each sign group to be globally sorted,
            # so validating a simple monotonic sequence would incorrectly
            # reject valid legacy sets.
            positive_seen = False
            for level_value in level_values:
                if level_value > tolerance:
                    positive_seen = True
                elif level_value < -tolerance and positive_seen:
                    errors.append(
                        "A negative axial-cosine level appears after a "
                        "positive level."
                    )
                    break

        maximum_level_current = 0.0

        for level_index, level in enumerate(level_slices, start=1):
            level_radial = radial[level]
            level_weights = weights[level]
            level_axial = float(axial[level.start])

            if not np.allclose(
                axial[level],
                level_axial,
                rtol=0.0,
                atol=tolerance,
            ):
                errors.append(
                    f"Axial level {level_index} is not constant."
                )

            if np.any(np.diff(level_radial) < -tolerance):
                errors.append(
                    f"Radial cosines are not increasing within axial level "
                    f"{level_index}."
                )

            if level_weights.size == 0:
                continue

            if abs(level_weights[0]) > tolerance:
                errors.append(
                    f"Axial level {level_index} does not begin with a "
                    "zero-weight initiating direction."
                )

            expected_initiator = -np.sqrt(max(0.0, 1.0 - level_axial**2))

            if not np.isclose(
                level_radial[0],
                expected_initiator,
                rtol=0.0,
                atol=5.0 * tolerance,
            ):
                errors.append(
                    f"Axial level {level_index} has an unexpected initiating "
                    "radial cosine."
                )

            level_current = float(
                np.sum(level_radial * level_weights)
            )
            maximum_level_current = max(
                maximum_level_current,
                abs(level_current),
            )

        if maximum_level_current > 10.0 * tolerance:
            errors.append(
                "Weighted radial-cosine balance is not zero within one or "
                "more axial levels."
            )

        maximum_moment_error = self.maximum_moment_error

        if maximum_moment_error > moment_tolerance:
            warnings.append(
                "Reference angular moments are not reproduced within "
                f"{moment_tolerance:.3E}; maximum error is "
                f"{maximum_moment_error:.3E}."
            )

        condition_number = self.metadata.get("condition_number")

        if condition_number is not None:
            condition_number = float(condition_number)

            if condition_number > 1.0e12:
                warnings.append(
                    "Legacy moment-fitting matrix is poorly conditioned: "
                    f"condition number = {condition_number:.3E}."
                )

        return QuadratureValidation(
            valid=not errors,
            errors=tuple(errors),
            warnings=tuple(warnings),
            weight_sum=weight_sum,
            minimum_nonzero_weight=minimum_nonzero_weight,
            maximum_sphere_error=maximum_sphere_error,
            maximum_level_current=maximum_level_current,
            maximum_moment_error=maximum_moment_error,
        )

    def validation_text(self, **kwargs: object) -> str:
        """Convenience wrapper returning :meth:`validate` as formatted text."""
        return self.validate(**kwargs).text()

    # ------------------------------------------------------------------
    # DORT formatting
    # ------------------------------------------------------------------

    def array81(
        self,
        *,
        values_per_line: int = 4,
        precision: int = 6,
    ) -> str:
        """Return the DORT ``81*`` directional-weight array."""
        return _format_dort_array(
            81,
            self.weights,
            values_per_line=values_per_line,
            precision=precision,
        )

    def array82(
        self,
        *,
        values_per_line: int = 4,
        precision: int = 6,
    ) -> str:
        """Return the DORT ``82*`` radial-cosine array."""
        return _format_dort_array(
            82,
            self.radial_cosine,
            values_per_line=values_per_line,
            precision=precision,
        )

    def array83(
        self,
        *,
        values_per_line: int = 4,
        precision: int = 6,
    ) -> str:
        """Return the DORT ``83*`` axial-cosine array."""
        return _format_dort_array(
            83,
            self.axial_cosine,
            values_per_line=values_per_line,
            precision=precision,
        )

    def dort_text(
        self,
        *,
        values_per_line: int = 4,
        precision: int = 6,
        array_order: Sequence[int] = (82, 83, 81),
        terminate_block: bool = False,
    ) -> str:
        """
        Return a DORT quadrature fragment.

        Parameters
        ----------
        values_per_line
            Number of numerical values per output line.
        precision
            Digits after the decimal in scientific notation.
        array_order
            Ordering of arrays in the text.  The default matches the supplied
            sample input: ``82*``, ``83*``, then ``81*``.
        terminate_block
            Append ``T`` if this is the final content of DORT input block 3.
        """
        validation = self.validate()

        if not validation.valid:
            raise ValueError(
                "Quadrature failed validation and will not be written:\n"
                + validation.text()
            )

        requested = tuple(int(number) for number in array_order)

        if sorted(requested) != [81, 82, 83]:
            raise ValueError(
                "array_order must contain 81, 82 and 83 exactly once."
            )

        formatters = {
            81: self.array81,
            82: self.array82,
            83: self.array83,
        }

        parts = [
            formatters[number](
                values_per_line=values_per_line,
                precision=precision,
            )
            for number in requested
        ]

        if terminate_block:
            parts.append("T")

        return "\n".join(parts)

    def write_dort(
        self,
        filename: str | Path,
        *,
        values_per_line: int = 4,
        precision: int = 6,
        array_order: Sequence[int] = (82, 83, 81),
        terminate_block: bool = False,
    ) -> Path:
        """Write a validated DORT quadrature fragment to disk."""
        path = Path(filename)

        path.write_text(
            self.dort_text(
                values_per_line=values_per_line,
                precision=precision,
                array_order=array_order,
                terminate_block=terminate_block,
            )
            + "\n",
            encoding="ascii",
        )

        return path

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def summary_text(self) -> str:
        """Return a concise description of the quadrature."""
        lines = [
            f"Quadrature family         : {self.family}",
            f"Total DORT directions    : {self.direction_count}",
            f"Integration directions   : {self.integration_direction_count}",
            f"Axial levels             : {self.axial_level_count}",
            f"Zero-weight initiators   : {self.zero_weight_direction_count}",
            f"Weight sum               : {self.weight_sum:.15g}",
        ]

        for key, label in (
            ("order", "Legacy S_N order"),
            ("symmetry", "Legacy symmetry"),
            ("polar_order", "Polar order"),
            ("azimuthal_order", "Azimuthal order"),
            ("condition_number", "Matrix condition"),
        ):
            if key in self.metadata:
                value = self.metadata[key]

                if key == "condition_number":
                    lines.append(f"{label:26s}: {float(value):.6E}")
                else:
                    lines.append(f"{label:26s}: {value}")

        lines.append(
            f"{'Maximum moment error':26s}: "
            f"{self.maximum_moment_error:.6E}"
        )

        return "\n".join(lines)


# ===========================================================================
# Public generation functions
# ===========================================================================


def generate_legacy_quadrature(
    *,
    order: int,
    symmetry: str = "half",
    radial_cosine_levels: Iterable[float] | None = None,
    smallest_radial_cosine: float | None = None,
    axial_cosine_levels: Iterable[float] | None = None,
    moment_pairs: Sequence[tuple[int, int]] | None = None,
    solve_tolerance: float = 1.0e-14,
    maximum_refinements: int = 30,
) -> QuadratureSet:
    """
    Generate a DOQDP-compatible legacy DORT quadrature.

    Parameters
    ----------
    order
        Even S_N order, e.g. ``8`` for S8.
    symmetry
        Weight-sharing symmetry used by the old moment fit:
        ``"none"``, ``"half"`` or ``"full"``.
        ``"half"`` is the recommended legacy choice.
    radial_cosine_levels
        Optional explicit positive radial-cosine levels, supplied in strictly
        descending order.  The number of entries must be ``order/2``.
        If omitted, levels are generated from one smallest positive cosine.
    smallest_radial_cosine
        Smallest positive radial cosine used to construct the remaining
        levels.  If omitted, the historical recommended value

        ``sqrt(1 / (3*order - 3))``

        is used.

        Do not specify this together with ``radial_cosine_levels``.
    axial_cosine_levels
        Optional explicit positive axial-cosine levels in descending order.
        If omitted, the radial levels are reused.
    moment_pairs
        Optional list of moment powers
        ``(radial_power, axial_power)``.  If omitted, the historical moment
        selection algorithm is used.
    solve_tolerance
        Tolerance used by iterative refinement of the weight solve.
    maximum_refinements
        Maximum iterative-refinement corrections.

    Returns
    -------
    QuadratureSet
        Full DORT direction set normalized to unit total weight.

    Notes
    -----
    This function is intended primarily for reproducibility.  For genuinely
    high angular resolution, prefer :func:`generate_product_quadrature`.
    """
    order = _validate_even_order(order, name="order")
    symmetry_code = _parse_legacy_symmetry(symmetry)
    positive_level_count = order // 2

    if (
        radial_cosine_levels is not None
        and smallest_radial_cosine is not None
    ):
        raise ValueError(
            "Specify radial_cosine_levels or smallest_radial_cosine, not both."
        )

    if radial_cosine_levels is None:
        radial_levels, used_smallest_cosine = (
            _generate_legacy_radial_levels(
                order,
                smallest_radial_cosine,
            )
        )
    else:
        radial_levels = _validate_positive_levels(
            radial_cosine_levels,
            count=positive_level_count,
            name="radial_cosine_levels",
        )
        used_smallest_cosine = None

    if axial_cosine_levels is None:
        axial_levels = radial_levels.copy()
    else:
        axial_levels = _validate_positive_levels(
            axial_cosine_levels,
            count=positive_level_count,
            name="axial_cosine_levels",
        )

    independent_weight_count = _legacy_independent_weight_count(
        order,
        symmetry_code,
    )

    if moment_pairs is None:
        selected_moments = tuple(
            _select_legacy_moment_pair(
                equation_number,
                positive_level_count,
                symmetry_code,
            )
            for equation_number in range(
                1,
                independent_weight_count + 1,
            )
        )
    else:
        selected_moments = _validate_moment_pairs(
            moment_pairs,
            expected_count=independent_weight_count,
        )

    coefficient_matrix = np.empty(
        (independent_weight_count, independent_weight_count),
        dtype=float,
    )
    target_vector = np.empty(independent_weight_count, dtype=float)
    weight_group_map: np.ndarray | None = None

    for row, (radial_power, axial_power) in enumerate(selected_moments):
        point_moments = _legacy_point_moment_table(
            radial_levels,
            axial_levels,
            radial_power,
            axial_power,
        )

        (
            grouped_coefficients,
            current_group_map,
        ) = _legacy_group_symmetric_points(
            point_moments,
            symmetry_code,
        )

        coefficient_matrix[row, :] = grouped_coefficients
        target_vector[row] = _analytical_sphere_moment(
            radial_power,
            axial_power,
        )

        if weight_group_map is None:
            weight_group_map = current_group_map
        elif not np.array_equal(weight_group_map, current_group_map):
            raise RuntimeError(
                "Internal legacy weight-group map changed between moments."
            )

    assert weight_group_map is not None

    (
        independent_weights,
        refinement_iterations,
    ) = _solve_with_refinement(
        coefficient_matrix,
        target_vector,
        tolerance=solve_tolerance,
        maximum_refinements=maximum_refinements,
    )

    (
        radial_cosine,
        axial_cosine,
        weights,
    ) = _assemble_legacy_dort_directions(
        radial_levels,
        axial_levels,
        independent_weights,
        weight_group_map,
    )

    condition_number = float(np.linalg.cond(coefficient_matrix))

    metadata: dict[str, object] = {
        "order": order,
        "symmetry": symmetry,
        "condition_number": condition_number,
        "independent_weight_count": independent_weight_count,
        "refinement_iterations": refinement_iterations,
        "radial_cosine_levels": radial_levels.copy(),
        "axial_cosine_levels": axial_levels.copy(),
    }

    if used_smallest_cosine is not None:
        metadata["smallest_radial_cosine"] = used_smallest_cosine

    result = QuadratureSet(
        family="legacy",
        radial_cosine=radial_cosine,
        axial_cosine=axial_cosine,
        weights=weights,
        reference_moments=selected_moments,
        metadata=metadata,
    )

    # Geometry/order must always be valid.  Negative weights are retained for
    # reproducibility and reported as warnings.
    validation = result.validate(require_positive_weights=False)

    if validation.errors:
        raise ValueError(
            "Generated legacy quadrature is not DORT-compatible:\n"
            + validation.text()
        )

    return result


def generate_product_quadrature(
    *,
    polar_order: int,
    azimuthal_order: int,
    reference_moment_degree: int = 6,
) -> QuadratureSet:
    """
    Generate a positive-weight Gauss product quadrature for DORT.

    Parameters
    ----------
    polar_order
        Number of Gauss-Legendre axial-cosine levels over ``[-1, 1]``.
        It must be an even integer so that no zero axial-cosine level is
        introduced and negative levels precede positive levels cleanly.
    azimuthal_order
        Number of Gauss-Legendre azimuthal integration directions in each
        axial level over the represented half-sphere ``phi in [0, pi]``.
        Larger values resolve radial/azimuthal angular variation more finely.
    reference_moment_degree
        Highest even total polynomial degree included in automatic moment
        validation.  The default checks moments through degree 6.

    Returns
    -------
    QuadratureSet
        Positive-weight full DORT quadrature normalized to unit total weight.

    Notes
    -----
    For every axial level, one additional zero-weight initiating direction is
    inserted at the most negative radial cosine.  Therefore:

    ``MM = polar_order * (azimuthal_order + 1)``

    where ``MM`` is the number of directions that should be used in DORT's
    control input.
    """
    polar_order = _validate_even_order(
        polar_order,
        name="polar_order",
    )

    if (
        isinstance(azimuthal_order, bool)
        or not isinstance(azimuthal_order, int)
        or azimuthal_order < 2
    ):
        raise ValueError(
            "azimuthal_order must be an integer >= 2."
        )

    if (
        isinstance(reference_moment_degree, bool)
        or not isinstance(reference_moment_degree, int)
        or reference_moment_degree < 0
        or reference_moment_degree % 2 != 0
    ):
        raise ValueError(
            "reference_moment_degree must be a non-negative even integer."
        )

    # Gauss-Legendre integration in the axial cosine eta over [-1, 1].
    axial_nodes, axial_weights = np.polynomial.legendre.leggauss(
        polar_order
    )

    # Gauss-Legendre integration in azimuth phi over [0, pi].  The 2-D DORT
    # representation exploits symmetry in the unrepresented third cosine, so
    # this half-azimuth carries the full normalized angular integral.
    azimuth_nodes, azimuth_weights = np.polynomial.legendre.leggauss(
        azimuthal_order
    )

    azimuth = 0.5 * np.pi * (azimuth_nodes + 1.0)
    mapped_azimuth_weights = 0.5 * np.pi * azimuth_weights

    radial_values: list[float] = []
    axial_values: list[float] = []
    direction_weights: list[float] = []

    for axial_cosine, axial_weight in zip(
        axial_nodes,
        axial_weights,
        strict=True,
    ):
        radial_radius = np.sqrt(max(0.0, 1.0 - axial_cosine**2))

        radial_integration_cosines = radial_radius * np.cos(azimuth)

        # Normalized full-sphere weight after exploiting the symmetry of the
        # unrepresented third direction cosine:
        #
        #   dOmega/(4*pi) -> d(eta) d(phi)/(2*pi), phi in [0, pi]
        #
        integration_weights = (
            axial_weight
            * mapped_azimuth_weights
            / (2.0 * np.pi)
        )

        order = np.argsort(radial_integration_cosines)

        radial_integration_cosines = radial_integration_cosines[order]
        integration_weights = integration_weights[order]

        # DORT uses a zero-weight direction at the start of each axial level
        # to initialize its curved-geometry angular recursion.
        radial_values.append(-radial_radius)
        axial_values.append(float(axial_cosine))
        direction_weights.append(0.0)

        radial_values.extend(
            radial_integration_cosines.astype(float).tolist()
        )
        axial_values.extend(
            [float(axial_cosine)] * azimuthal_order
        )
        direction_weights.extend(
            integration_weights.astype(float).tolist()
        )

    reference_moments = _standard_reference_moments(
        reference_moment_degree
    )

    result = QuadratureSet(
        family="product",
        radial_cosine=np.asarray(radial_values, dtype=float),
        axial_cosine=np.asarray(axial_values, dtype=float),
        weights=np.asarray(direction_weights, dtype=float),
        reference_moments=reference_moments,
        metadata={
            "polar_order": polar_order,
            "azimuthal_order": azimuthal_order,
            "integration_direction_count": (
                polar_order * azimuthal_order
            ),
            "dort_direction_count": (
                polar_order * (azimuthal_order + 1)
            ),
        },
    )

    validation = result.validate(require_positive_weights=True)

    if validation.errors:
        raise ValueError(
            "Generated product quadrature is not DORT-compatible:\n"
            + validation.text()
        )

    return result


def generate_quadrature(
    *,
    family: str = "legacy",
    **options: object,
) -> QuadratureSet:
    """
    Unified convenience dispatcher.

    Parameters
    ----------
    family
        ``"legacy"`` or ``"product"``.
    **options
        Arguments for the selected generator.

    Examples
    --------
    Legacy S8::

        q = generate_quadrature(
            family="legacy",
            order=8,
            symmetry="half",
        )

    High-order product quadrature::

        q = generate_quadrature(
            family="product",
            polar_order=24,
            azimuthal_order=32,
        )
    """
    normalized = str(family).strip().lower()

    if normalized in {"legacy", "doqdp", "level_symmetric"}:
        return generate_legacy_quadrature(**options)

    if normalized in {"product", "gauss_product", "high_order"}:
        return generate_product_quadrature(**options)

    raise ValueError(
        "Unknown quadrature family. Use 'legacy' or 'product'."
    )


# ===========================================================================
# Modern helper functions
# ===========================================================================


def _validate_even_order(value: int, *, name: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 2
        or value % 2 != 0
    ):
        raise ValueError(
            f"{name} must be an even integer >= 2."
        )

    return value


def _parse_legacy_symmetry(symmetry: str) -> int:
    normalized = (
        str(symmetry)
        .strip()
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
    )

    mapping = {
        "none": 1,
        "no_symmetry": 1,
        "half": 2,
        "half_symmetry": 2,
        "full": 3,
        "full_symmetry": 3,
    }

    try:
        return mapping[normalized]
    except KeyError as exc:
        raise ValueError(
            "symmetry must be 'none', 'half', or 'full'."
        ) from exc


def _validate_positive_levels(
    values: Iterable[float],
    *,
    count: int,
    name: str,
) -> np.ndarray:
    levels = np.asarray(list(values), dtype=float)

    if levels.ndim != 1 or levels.size != count:
        raise ValueError(
            f"{name} must contain exactly {count} values."
        )

    if not np.all(np.isfinite(levels)):
        raise ValueError(f"{name} contains non-finite values.")

    if np.any(levels <= 0.0) or np.any(levels > 1.0):
        raise ValueError(
            f"{name} values must satisfy 0 < value <= 1."
        )

    if levels.size > 1 and not np.all(np.diff(levels) < 0.0):
        raise ValueError(
            f"{name} must be supplied in strictly descending order."
        )

    return levels


def _validate_moment_pairs(
    moment_pairs: Sequence[tuple[int, int]],
    *,
    expected_count: int,
) -> tuple[tuple[int, int], ...]:
    parsed: list[tuple[int, int]] = []

    for pair in moment_pairs:
        if len(pair) != 2:
            raise ValueError(
                "Each moment must be a "
                "(radial_power, axial_power) pair."
            )

        radial_power, axial_power = pair

        if (
            isinstance(radial_power, bool)
            or isinstance(axial_power, bool)
            or not isinstance(radial_power, int)
            or not isinstance(axial_power, int)
        ):
            raise TypeError("Moment powers must be integers.")

        if radial_power < 0 or axial_power < 0:
            raise ValueError("Moment powers must be non-negative.")

        if radial_power % 2 or axial_power % 2:
            raise ValueError(
                "Legacy fitted moments should use even powers."
            )

        parsed.append((radial_power, axial_power))

    if len(parsed) != expected_count:
        raise ValueError(
            f"This legacy configuration requires {expected_count} moment "
            f"equations; received {len(parsed)}."
        )

    return tuple(parsed)


def _standard_reference_moments(
    maximum_total_degree: int,
) -> tuple[tuple[int, int], ...]:
    moments: list[tuple[int, int]] = []

    for total_degree in range(0, maximum_total_degree + 1, 2):
        for radial_power in range(total_degree, -1, -2):
            axial_power = total_degree - radial_power
            moments.append((radial_power, axial_power))

    return tuple(moments)


def _analytical_sphere_moment(
    radial_power: int,
    axial_power: int,
) -> float:
    """
    Analytical normalized spherical moment E[mu^p eta^q].

    Odd powers vanish by symmetry.  The legacy moment fitter only uses even
    powers, but supporting the general parity rule makes this helper useful
    for product-set validation too.
    """
    if radial_power < 0 or axial_power < 0:
        raise ValueError("Moment powers must be non-negative.")

    if radial_power % 2 or axial_power % 2:
        return 0.0

    value = 1.0

    if axial_power:
        for odd_number in range(1, axial_power, 2):
            value *= (
                float(odd_number)
                / (radial_power + odd_number + 2.0)
            )

    value *= 1.0 / (radial_power + 1.0)
    return value


def _find_level_slices(
    axial_cosine: np.ndarray,
    *,
    tolerance: float = 1.0e-12,
) -> list[slice]:
    if axial_cosine.size == 0:
        return []

    starts = [0]

    for index in range(1, axial_cosine.size):
        if not np.isclose(
            axial_cosine[index],
            axial_cosine[index - 1],
            rtol=0.0,
            atol=tolerance,
        ):
            starts.append(index)

    slices: list[slice] = []

    for index, start in enumerate(starts):
        stop = (
            starts[index + 1]
            if index + 1 < len(starts)
            else axial_cosine.size
        )
        slices.append(slice(start, stop))

    return slices


def _format_dort_array(
    array_number: int,
    values: np.ndarray,
    *,
    values_per_line: int,
    precision: int,
) -> str:
    if values_per_line < 1:
        raise ValueError("values_per_line must be >= 1.")

    if precision < 1:
        raise ValueError("precision must be >= 1.")

    values = np.asarray(values, dtype=float)
    prefix = f"{array_number}** "
    continuation = " " * len(prefix)
    lines: list[str] = []

    for start in range(0, values.size, values_per_line):
        chunk = values[start : start + values_per_line]
        body = " ".join(
            f"{value: .{precision}E}"
            for value in chunk
        )
        lines.append(
            (prefix if start == 0 else continuation) + body
        )

    return "\n".join(lines)


# ===========================================================================
# Legacy DOQDP numerical implementation
#
# These functions are private deliberately.  Their names describe the
# numerical operation rather than preserving the terse original Fortran
# subroutine/variable names.
# ===========================================================================


def _legacy_independent_weight_count(
    order: int,
    symmetry_code: int,
) -> int:
    positive_level_count = order // 2

    if symmetry_code == 1:
        return sum(range(1, positive_level_count + 1))

    if symmetry_code == 2:
        return sum(
            (level // 2) + (1 if level % 2 else 0)
            for level in range(1, positive_level_count + 1)
        )

    remaining = positive_level_count
    total = 0

    for _ in range((positive_level_count + 2) // 3):
        total += (
            remaining // 2
            + (1 if remaining % 2 else 0)
        )
        remaining -= 3

    return total


def _select_legacy_moment_pair(
    equation_number: int,
    positive_level_count: int,
    symmetry_code: int,
) -> tuple[int, int]:
    adjusted_number = equation_number

    if symmetry_code == 3 and equation_number > 1:
        adjusted_number += 1

    lower_limit = 0
    upper_limit = positive_level_count
    last_band = 0

    for band in range(
        1,
        (positive_level_count + 1) // 2 + 1,
    ):
        last_band = band

        if adjusted_number <= upper_limit:
            radial_power = 2 * (
                adjusted_number
                - lower_limit
                + band
                - 2
            )
            axial_power = 2 * (band - 1)
            return radial_power, axial_power

        lower_limit = upper_limit
        upper_limit += positive_level_count - 2 * band

    upper_limit = (
        upper_limit
        - 1
        + 2 * last_band
    )

    for band in range(1, positive_level_count // 2 + 1):
        if adjusted_number <= upper_limit:
            radial_power = 2 * (band - 1)
            axial_power = 2 * (
                adjusted_number
                - lower_limit
                + band
                - 1
            )
            return radial_power, axial_power

        lower_limit = upper_limit
        upper_limit += positive_level_count - 1 + 2 * band

    raise RuntimeError(
        "Could not select enough legacy moment equations."
    )


def _generate_legacy_radial_levels(
    order: int,
    smallest_positive_cosine: float | None,
) -> tuple[np.ndarray, float]:
    if order <= 2:
        raise ValueError(
            "Automatic legacy level generation requires order > 2. "
            "For S2 provide radial_cosine_levels explicitly."
        )

    if smallest_positive_cosine is None:
        smallest_positive_cosine = float(
            np.sqrt(1.0 / (3.0 * order - 3.0))
        )
    else:
        smallest_positive_cosine = float(
            smallest_positive_cosine
        )

    if not (
        np.isfinite(smallest_positive_cosine)
        and 0.0 < smallest_positive_cosine < 1.0
    ):
        raise ValueError(
            "smallest_radial_cosine must satisfy 0 < value < 1."
        )

    positive_level_count = order // 2

    spacing = (
        2.0
        * (
            1.0
            - 3.0 * smallest_positive_cosine**2
        )
        / (order - 2.0)
    )

    if spacing <= 0.0:
        raise ValueError(
            "The selected smallest_radial_cosine gives a non-positive "
            "legacy level spacing."
        )

    ascending_levels = np.empty(
        positive_level_count,
        dtype=float,
    )
    ascending_levels[0] = smallest_positive_cosine

    for index in range(1, positive_level_count):
        squared_level = (
            smallest_positive_cosine**2
            + index * spacing
        )

        if squared_level <= 0.0 or squared_level > 1.0 + 1.0e-12:
            raise ValueError(
                "Generated legacy radial-cosine level is outside [0, 1]."
            )

        ascending_levels[index] = np.sqrt(
            max(squared_level, 0.0)
        )

    return ascending_levels[::-1].copy(), smallest_positive_cosine


def _legacy_point_moment_table(
    radial_levels: np.ndarray,
    axial_levels: np.ndarray,
    radial_power: int,
    axial_power: int,
) -> np.ndarray:
    level_count = radial_levels.size
    table = np.zeros(
        (level_count, level_count),
        dtype=float,
    )

    for radial_index in range(level_count):
        for triangular_index in range(radial_index + 1):
            reversed_axial_index = (
                level_count - 1 - triangular_index
            )

            table[
                radial_index,
                reversed_axial_index,
            ] = (
                radial_levels[radial_index] ** radial_power
                * axial_levels[reversed_axial_index] ** axial_power
            )

    return table


def _legacy_group_symmetric_points(
    point_moments: np.ndarray,
    symmetry_code: int,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Group symmetry-equivalent legacy quadrature points.

    Returns
    -------
    grouped_coefficients
        One coefficient per independent point weight.
    weight_group_map
        One-based weight-group index for each triangular point location.
    """
    level_count = point_moments.shape[0]
    weight_group_map = np.zeros(
        (level_count, level_count),
        dtype=int,
    )
    grouped_values: list[float] = []

    if symmetry_code == 1:
        for row in range(1, level_count + 1):
            for triangular_column in range(1, row + 1):
                column = level_count + 1 - triangular_column
                grouped_values.append(
                    float(point_moments[row - 1, column - 1])
                )
                weight_group_map[row - 1, column - 1] = (
                    len(grouped_values)
                )

    elif symmetry_code == 2:
        remaining = level_count
        outer_count = (level_count + 1) // 2
        stopped = False

        for outer in range(1, outer_count + 1):
            partner = level_count + 1 - outer

            for offset in range(1, remaining):
                first = outer + offset - 1

                grouped_values.append(
                    float(
                        point_moments[first - 1, partner - 1]
                        + point_moments[partner - 1, first - 1]
                    )
                )

                group_number = len(grouped_values)
                weight_group_map[first - 1, partner - 1] = group_number
                weight_group_map[partner - 1, first - 1] = group_number

            grouped_values.append(
                float(point_moments[partner - 1, partner - 1])
            )
            weight_group_map[partner - 1, partner - 1] = len(
                grouped_values
            )

            remaining -= 2

            if remaining < 2:
                stopped = True
                break

        if stopped and remaining == 1:
            centre = level_count // 2 + 1
            grouped_values.append(
                float(point_moments[centre - 1, centre - 1])
            )
            weight_group_map[centre - 1, centre - 1] = len(
                grouped_values
            )

    else:
        diagonal_offset = 1
        remaining = level_count

        for outer in range(1, (level_count + 1) // 3 + 1):
            first_corner = 2 * outer - 1
            last_corner = level_count + 1 - outer

            grouped_values.append(
                float(
                    point_moments[first_corner - 1, last_corner - 1]
                    + point_moments[last_corner - 1, first_corner - 1]
                    + point_moments[last_corner - 1, last_corner - 1]
                )
            )

            group_number = len(grouped_values)

            for row, column in (
                (first_corner, last_corner),
                (last_corner, first_corner),
                (last_corner, last_corner),
            ):
                weight_group_map[row - 1, column - 1] = group_number

            if remaining == 2:
                break

            if remaining != 3:
                for offset in range(1, remaining // 2):
                    inner = first_corner + offset
                    outer_partner = last_corner - offset

                    grouped_values.append(
                        float(
                            point_moments[inner - 1, outer_partner - 1]
                            + point_moments[inner - 1, last_corner - 1]
                            + point_moments[outer_partner - 1, inner - 1]
                            + point_moments[last_corner - 1, inner - 1]
                            + point_moments[last_corner - 1, outer_partner - 1]
                            + point_moments[outer_partner - 1, last_corner - 1]
                        )
                    )

                    group_number = len(grouped_values)

                    for row, column in (
                        (inner, outer_partner),
                        (inner, last_corner),
                        (outer_partner, inner),
                        (last_corner, inner),
                        (last_corner, outer_partner),
                        (outer_partner, last_corner),
                    ):
                        weight_group_map[row - 1, column - 1] = group_number

            if remaining % 2:
                centre = level_count // 2 + diagonal_offset

                grouped_values.append(
                    float(
                        point_moments[centre - 1, centre - 1]
                        + point_moments[last_corner - 1, centre - 1]
                        + point_moments[centre - 1, last_corner - 1]
                    )
                )

                group_number = len(grouped_values)

                for row, column in (
                    (centre, centre),
                    (last_corner, centre),
                    (centre, last_corner),
                ):
                    weight_group_map[row - 1, column - 1] = group_number

                diagonal_offset += 1

            remaining -= 3

            if remaining == 1:
                centre = first_corner + 2
                grouped_values.append(
                    float(point_moments[centre - 1, centre - 1])
                )
                weight_group_map[centre - 1, centre - 1] = len(
                    grouped_values
                )
                break

            if remaining == 0:
                break

    # Mirror the group identifiers exactly as required by the final legacy
    # DORT direction ordering.
    for first in range(1, level_count + 1):
        for second in range(first, level_count + 1):
            mirrored_row = level_count + 1 - second
            mirrored_source_row = level_count + 1 - first

            weight_group_map[
                mirrored_row - 1,
                first - 1,
            ] = weight_group_map[
                mirrored_source_row - 1,
                second - 1,
            ]

    return (
        np.asarray(grouped_values, dtype=float),
        weight_group_map,
    )


def _solve_with_refinement(
    coefficient_matrix: np.ndarray,
    target_vector: np.ndarray,
    *,
    tolerance: float,
    maximum_refinements: int,
) -> tuple[np.ndarray, int]:
    if tolerance <= 0.0:
        raise ValueError("solve_tolerance must be positive.")

    if maximum_refinements < 0:
        raise ValueError(
            "maximum_refinements cannot be negative."
        )

    try:
        solution = np.linalg.solve(
            coefficient_matrix,
            target_vector,
        )
    except np.linalg.LinAlgError as exc:
        raise ValueError(
            "Legacy quadrature moment matrix is singular."
        ) from exc

    refinements = 0

    for iteration in range(maximum_refinements):
        residual = (
            target_vector
            - coefficient_matrix @ solution
        )

        if np.max(np.abs(residual)) <= tolerance:
            break

        try:
            correction = np.linalg.solve(
                coefficient_matrix,
                residual,
            )
        except np.linalg.LinAlgError as exc:
            raise ValueError(
                "Legacy quadrature matrix became singular during "
                "iterative refinement."
            ) from exc

        updated_solution = solution + correction

        relative_change = np.max(
            np.abs(correction)
            / np.maximum(
                np.abs(updated_solution),
                1.0e-300,
            )
        )

        solution = updated_solution
        refinements = iteration + 1

        if relative_change <= tolerance:
            break

    return solution, refinements


def _assemble_legacy_dort_directions(
    radial_levels: np.ndarray,
    axial_levels: np.ndarray,
    independent_weights: np.ndarray,
    weight_group_map: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Arrange a legacy fitted set into full two-dimensional DORT ordering.

    The returned weights are normalized to sum to 1, corresponding to the
    normal full 2-D DORT use case.
    """
    level_count = radial_levels.size

    initiating_radial_cosines = np.empty(
        level_count,
        dtype=float,
    )

    for level in range(1, level_count + 1):
        reversed_level = level_count + 1 - level
        remainder = (
            1.0
            - radial_levels[reversed_level - 1] ** 2
        )

        if remainder < -1.0e-12:
            raise ValueError(
                "Legacy cosine levels produce an invalid initiating direction."
            )

        initiating_radial_cosines[level - 1] = np.sqrt(
            max(remainder, 0.0)
        )

    half_radial: list[float] = []

    for level in range(1, level_count + 1):
        reversed_level = level_count + 1 - level

        half_radial.append(
            -initiating_radial_cosines[reversed_level - 1]
        )

        for index in range(reversed_level, level_count + 1):
            half_radial.append(-float(radial_levels[index - 1]))

        for index in range(1, level + 1):
            reversed_index = level_count + 1 - index
            half_radial.append(
                float(radial_levels[reversed_index - 1])
            )

    negative_axial: list[float] = []
    positive_axial: list[float] = []

    for level in range(1, level_count + 1):
        directions_in_level = 2 * level + 1
        negative_axial.extend(
            [-float(axial_levels[level - 1])] * directions_in_level
        )
        positive_axial.extend(
            [float(axial_levels[level - 1])] * directions_in_level
        )

    # The historical full 2-D DORT normalization divides independent point
    # weights by four before mapping them to the two axial signs.
    scaled_weights = independent_weights / 4.0
    half_weights: list[float] = []

    for level in range(1, level_count + 1):
        half_weights.append(0.0)
        reversed_level = level_count + 1 - level

        for index in range(1, level + 1):
            paired_index = level + 1 - index
            group_number = int(
                weight_group_map[
                    reversed_level - 1,
                    paired_index - 1,
                ]
            )
            half_weights.append(
                float(scaled_weights[group_number - 1])
            )

        for index in range(1, level + 1):
            group_number = int(
                weight_group_map[
                    reversed_level - 1,
                    index - 1,
                ]
            )
            half_weights.append(
                float(scaled_weights[group_number - 1])
            )

    radial = np.asarray(
        half_radial + half_radial,
        dtype=float,
    )
    axial = np.asarray(
        negative_axial + positive_axial,
        dtype=float,
    )
    weights = np.asarray(
        half_weights + half_weights,
        dtype=float,
    )

    return radial, axial, weights


# ===========================================================================
# Demonstration
# ===========================================================================


if __name__ == "__main__":
    print("Legacy S8 example")
    print("=================")

    legacy = generate_legacy_quadrature(
        order=8,
        symmetry="half",
    )

    print(legacy.summary_text())
    print()
    print(legacy.validation_text())
    print()

    print("High-order product example")
    print("==========================")

    product = generate_product_quadrature(
        polar_order=24,
        azimuthal_order=32,
    )

    print(product.summary_text())
    print()
    print(product.validation_text())
