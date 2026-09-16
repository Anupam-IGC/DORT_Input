"""High-level run-mode control for the locally modified DORT workflow.

This module sits above the low-level geometry/material writer.  Its purpose is
to make the three run patterns used in the supplied working decks explicit:

``eigenvalue_first``
    k-eigenvalue calculation with an explicit factorized starting flux.
    ``KTYPE=1``, ``INPFXM=3``, ``NTFLX=0`` and cards 93*/94*/95*.

``eigenvalue_rerun``
    k-eigenvalue continuation using the unformatted flux file from a previous
    run. ``KTYPE=1``, ``INPFXM=0`` and ``NTFLX=20``.  The previous
    ``dortflux.bin`` (unit 21 output) is supplied to the next run as
    ``guessflux.bin`` (unit 20 input), so 93*/94*/95* are omitted.

``fixed_source``
    fixed-source calculation following the supplied sample deck.
    ``KTYPE=0`` with a factorized starting flux (93*/94*/95*) and a spatial x
    energy distributed source (``INPSRM=2`` -> 96* and 98*; 97* omitted).

The card-presence rules are derived from the DORT definitions of ``INPFXM``
and ``INPSRM`` and are checked independently of the preset, so advanced users
may change those two controls and still receive consistent validation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import re
import shutil
from typing import Iterable, Mapping, TYPE_CHECKING

if TYPE_CHECKING:
    from writer import DORTWriter
    from source import FixedSource


# Ordered positions in the local 62$$ array.  Positions 1..66 correspond to
# the established DORT control names.  NEUT is present as position 67 in the
# supplied eigenvalue decks but is omitted in the supplied fixed-source deck,
# so it is represented as an optional tail value rather than forced.
CONTROL62_NAMES: tuple[str, ...] = (
    "IADJ", "ISCTM", "IZM", "IM", "JM", "IGM", "IHT", "IHS", "IHM", "MIXL",
    "MCR", "MTP", "MTM", "IDFAC", "MM", "INGEOM", "IBL", "IBR", "IBB", "IBT",
    "ISRMX", "IFXMI", "IFXMF", "MODE", "KTYPE", "IACC", "KALF", "IGTYPE",
    "INPFXM", "INPSRM", "NJNTSR", "NINTSR", "NJNTFX", "NINTFX", "IACT", "IRED",
    "IPDB2", "IFXPRT", "ICSPRT", "IDIRF", "JDIRF", "JDIRL", "NBUF", "IEPSBZ",
    "MINBLK", "MAXBLK", "ISBT", "MSBT", "MSDM", "IBFSCL", "INTSCL", "ITMSCL",
    "NOFIS", "IFDB2Z", "ISWP", "KEYJN", "KEYIN", "NSIGTP", "NORPOS", "NORMAT",
    "MSTMAX", "NEGFIX", "LOCOBJ", "LCMOBJ", "NKEYFX", "NCNDIN",
)

CONTROL61_NAMES: tuple[str, ...] = (
    "NTFLX", "NTFOG", "NTSIG", "NTBSI", "NTDSI", "NTFCI", "NTIBI", "NTIBO",
    "NTNPR", "NTDIR", "NTDSO", "NTSCL", "NTZNF",
)


class RunMode(str, Enum):
    """Supported high-level calculation profiles."""

    EIGENVALUE_FIRST = "eigenvalue_first"
    EIGENVALUE_RERUN = "eigenvalue_rerun"
    FIXED_SOURCE = "fixed_source"


class FluxGuessMode(str, Enum):
    """DORT ``INPFXM`` representations used by the run-control API."""

    ZERO = "zero"                 # INPFXM=0, NTFLX=0
    RESTART_FILE = "restart_file" # INPFXM=0, NTFLX>0
    FULL_BY_GROUP = "full_by_group"  # INPFXM=1 -> 93*
    SPACE_ENERGY = "space_energy"    # INPFXM=2 -> 93*,95*
    FACTORIZED = "factorized"        # INPFXM=3 -> 93*,94*,95*


class DistributedSourceMode(str, Enum):
    """DORT ``INPSRM`` distributed-source representations."""

    NONE = "none"                    # INPSRM=0
    FULL_BY_GROUP = "full_by_group"  # INPSRM=1 -> 96*
    SPACE_ENERGY = "space_energy"    # INPSRM=2 -> 96*,98*
    FACTORIZED = "factorized"        # INPSRM=3 -> 96*,97*,98*


class BoundaryCondition(str, Enum):
    """Human-readable boundary-condition choices for the four R-Z boundaries."""

    VOID = "void"
    REFLECTED = "reflected"
    PERIODIC = "periodic"
    CYLINDRICAL = "cylindrical"
    FIXED_SOURCE = "fixed_source"
    ALBEDO = "albedo"


class FluxExtrapolation(str, Enum):
    """Flux-extrapolation choices corresponding to DORT ``MODE``."""

    LINEAR_ZERO_FIX = "linear_zero_fix"
    LINEAR = "linear"
    SCALAR_WEIGHTED = "scalar_weighted"
    ZERO_WEIGHTED = "zero_weighted"
    THETA_WEIGHTED = "theta_weighted"
    VECTOR_WEIGHTED = "vector_weighted"


class RebalanceMethod(str, Enum):
    """Rebalance/acceleration method corresponding to DORT ``IACC``."""

    GROUPWISE = "groupwise"
    SOURCE_CORRECTION = "source_correction"
    SPACE_DEPENDENT = "space_dependent"


class RebalanceStabilization(str, Enum):
    """Rebalance-stabilization choice corresponding to DORT ``KALF``."""

    J_METHOD = "j_method"
    PHI_METHOD = "phi_method"


class ScalarFluxPrinting(str, Enum):
    """Scalar-flux printing choice corresponding to DORT ``IFXPRT``."""

    FINAL = "final"
    NONE = "none"
    AFTER_EACH_GROUP = "after_each_group"


class CrossSectionPrinting(str, Enum):
    """Cross-section print choice corresponding to DORT ``ICSPRT``."""

    PRINT = "print"
    SUPPRESS = "suppress"


class DirectionalFluxOutput(str, Enum):
    """Directional-flux output choice corresponding to DORT ``IDIRF``."""

    NONE = "none"
    SAVE_AND_PRINT = "save_and_print"
    SAVE_ONLY = "save_only"


class ZoneConvergence(str, Enum):
    """Zone-importance convergence choice corresponding to DORT ``IEPSBZ``."""

    NONE = "none"
    USE = "use"
    USE_AND_PRINT_LAST_INNER = "use_and_print_last_inner"
    USE_AND_PRINT_EVERY_INNER = "use_and_print_every_inner"


class FissionTreatment(str, Enum):
    """Fission treatment corresponding to DORT ``NOFIS``."""

    NORMALIZED_CHI = "normalized_chi"
    INPUT_CHI = "input_chi"
    NO_FISSION = "no_fission"


class CrossSectionFormat(str, Enum):
    """Cross-section input format corresponding to DORT ``NSIGTP``."""

    GIP = "gip"
    ORDOSW = "ordosw"


_BOUNDARY_CODE = {
    BoundaryCondition.VOID: 0,
    BoundaryCondition.REFLECTED: 1,
    BoundaryCondition.PERIODIC: 2,
    BoundaryCondition.CYLINDRICAL: 3,
    BoundaryCondition.FIXED_SOURCE: 4,
    BoundaryCondition.ALBEDO: 5,
}
_FLUX_EXTRAPOLATION_CODE = {
    FluxExtrapolation.LINEAR_ZERO_FIX: 0,
    FluxExtrapolation.LINEAR: 1,
    FluxExtrapolation.SCALAR_WEIGHTED: 2,
    FluxExtrapolation.ZERO_WEIGHTED: 3,
    FluxExtrapolation.THETA_WEIGHTED: 4,
    FluxExtrapolation.VECTOR_WEIGHTED: 5,
}
_REBALANCE_CODE = {
    RebalanceMethod.GROUPWISE: 0,
    RebalanceMethod.SOURCE_CORRECTION: 1,
    RebalanceMethod.SPACE_DEPENDENT: 2,
}
_STABILIZATION_CODE = {
    RebalanceStabilization.J_METHOD: 0,
    RebalanceStabilization.PHI_METHOD: 1,
}
_SCALAR_PRINT_CODE = {
    ScalarFluxPrinting.FINAL: 0,
    ScalarFluxPrinting.NONE: 1,
    ScalarFluxPrinting.AFTER_EACH_GROUP: 2,
}
_XS_PRINT_CODE = {
    CrossSectionPrinting.PRINT: 0,
    CrossSectionPrinting.SUPPRESS: 1,
}
_DIRECTIONAL_FLUX_CODE = {
    DirectionalFluxOutput.NONE: 0,
    DirectionalFluxOutput.SAVE_AND_PRINT: 1,
    DirectionalFluxOutput.SAVE_ONLY: 2,
}
_ZONE_CONVERGENCE_CODE = {
    ZoneConvergence.NONE: 0,
    ZoneConvergence.USE: 1,
    ZoneConvergence.USE_AND_PRINT_LAST_INNER: 11,
    ZoneConvergence.USE_AND_PRINT_EVERY_INNER: 21,
}
_FISSION_CODE = {
    FissionTreatment.NORMALIZED_CHI: 0,
    FissionTreatment.INPUT_CHI: 1,
    FissionTreatment.NO_FISSION: 2,
}
_XS_FORMAT_CODE = {
    CrossSectionFormat.GIP: 0,
    CrossSectionFormat.ORDOSW: 1,
}


_INPFXM_BY_MODE = {
    FluxGuessMode.ZERO: 0,
    FluxGuessMode.RESTART_FILE: 0,
    FluxGuessMode.FULL_BY_GROUP: 1,
    FluxGuessMode.SPACE_ENERGY: 2,
    FluxGuessMode.FACTORIZED: 3,
}

_INPSRM_BY_MODE = {
    DistributedSourceMode.NONE: 0,
    DistributedSourceMode.FULL_BY_GROUP: 1,
    DistributedSourceMode.SPACE_ENERGY: 2,
    DistributedSourceMode.FACTORIZED: 3,
}


@dataclass(frozen=True)
class SettingSpec:
    """Metadata for one human-readable run setting."""

    name: str
    dort_name: str | None
    description: str
    enum_type: type[Enum] | None = None
    code_map: Mapping[Enum, int] | None = None
    integer: bool = False
    boolean: bool = False
    read_only: bool = False

    @property
    def options(self) -> tuple[str, ...]:
        if self.enum_type is not None:
            return tuple(member.value for member in self.enum_type)
        if self.boolean:
            return ("false", "true")
        if self.integer:
            return ("integer",)
        return ()


SETTING_SPECS: tuple[SettingSpec, ...] = (
    SettingSpec("starting_flux", "INPFXM", "How the initial scalar-flux guess is supplied.", FluxGuessMode, _INPFXM_BY_MODE),
    SettingSpec("distributed_source", "INPSRM", "How the distributed fixed source is supplied.", DistributedSourceMode, _INPSRM_BY_MODE),
    SettingSpec("left_boundary", "IBL", "Boundary condition on the left/radial-min boundary.", BoundaryCondition, _BOUNDARY_CODE),
    SettingSpec("right_boundary", "IBR", "Boundary condition on the right/radial-max boundary.", BoundaryCondition, _BOUNDARY_CODE),
    SettingSpec("bottom_boundary", "IBB", "Boundary condition on the bottom/axial-min boundary.", BoundaryCondition, _BOUNDARY_CODE),
    SettingSpec("top_boundary", "IBT", "Boundary condition on the top/axial-max boundary.", BoundaryCondition, _BOUNDARY_CODE),
    SettingSpec("maximum_outer_iterations", "ISRMX", "Maximum number of source (outer) iterations.", integer=True),
    SettingSpec("initial_inner_iterations", "IFXMI", "Initial maximum number of flux (inner) iterations per group.", integer=True),
    SettingSpec("final_inner_iterations", "IFXMF", "Final maximum number of flux (inner) iterations per group; 0 keeps the initial limit.", integer=True),
    SettingSpec("flux_extrapolation", "MODE", "Flux extrapolation model.", FluxExtrapolation, _FLUX_EXTRAPOLATION_CODE),
    SettingSpec("rebalance_method", "IACC", "Rebalance/acceleration method.", RebalanceMethod, _REBALANCE_CODE),
    SettingSpec("rebalance_stabilization", "KALF", "Rebalance stabilization method.", RebalanceStabilization, _STABILIZATION_CODE),
    SettingSpec("scalar_flux_printing", "IFXPRT", "When scalar fluxes are printed.", ScalarFluxPrinting, _SCALAR_PRINT_CODE),
    SettingSpec("cross_section_printing", "ICSPRT", "Whether cross-section data are printed.", CrossSectionPrinting, _XS_PRINT_CODE),
    SettingSpec("directional_flux_output", "IDIRF", "Whether directional flux is saved/printed.", DirectionalFluxOutput, _DIRECTIONAL_FLUX_CODE),
    SettingSpec("first_directional_flux_axial_interval", "JDIRF", "First axial interval included in directional-flux output.", integer=True),
    SettingSpec("last_directional_flux_axial_interval", "JDIRL", "Last axial interval included in directional-flux output.", integer=True),
    SettingSpec("zone_convergence", "IEPSBZ", "Zone-importance convergence/printing behavior.", ZoneConvergence, _ZONE_CONVERGENCE_CODE),
    SettingSpec("iterations_before_first_rebalance", "IBFSCL", "Number of flux iterations before the first rebalance.", integer=True),
    SettingSpec("iterations_between_rescaling", "INTSCL", "Number of flux iterations between rescaling operations.", integer=True),
    SettingSpec("maximum_rebalance_iterations", "ITMSCL", "Maximum number of rebalance iterations.", integer=True),
    SettingSpec("fission_treatment", "NOFIS", "How fission and chi are treated.", FissionTreatment, _FISSION_CODE),
    SettingSpec("cross_section_format", "NSIGTP", "Format of the cross-section data read from NTSIG.", CrossSectionFormat, _XS_FORMAT_CODE),
    SettingSpec("repair_negative_sources", "NEGFIX", "Repair negative source values when enabled.", boolean=True),
    SettingSpec("key_flux_axial_interval", "KEYJN", "Axial interval used for key-flux printing; 0 disables.", integer=True),
    SettingSpec("key_flux_radial_interval", "KEYIN", "Radial interval used for key-flux printing; 0 disables.", integer=True),
    SettingSpec("energy_groups", "IGM", "Number of energy groups.", integer=True),
    SettingSpec("quadrature_directions", "MM", "Maximum number of angular directions.", integer=True),
    SettingSpec("cross_section_table_length", "IHM", "Length of the cross-section table for each group.", integer=True),
    SettingSpec("total_xs_position", "IHT", "Position of total cross section in the group table.", integer=True),
    SettingSpec("self_scatter_position", "IHS", "Position of self-scatter cross section in the group table.", integer=True),
    SettingSpec("scattering_order", "ISCTM", "Legendre scattering order, derived from the material/mixture model.", integer=True, read_only=True),
    SettingSpec("material_zone_count", "IZM", "Number of material zones, derived from geometry.", integer=True, read_only=True),
    SettingSpec("radial_intervals", "IM", "Number of radial mesh intervals, derived from geometry.", integer=True, read_only=True),
    SettingSpec("axial_intervals", "JM", "Number of axial mesh intervals, derived from geometry.", integer=True, read_only=True),
)

_SETTING_BY_NAME = {spec.name: spec for spec in SETTING_SPECS}


def _coerce_enum(enum_type: type[Enum], value):
    if isinstance(value, enum_type):
        return value
    try:
        return enum_type(str(value))
    except ValueError as exc:
        options = ", ".join(member.value for member in enum_type)
        raise ValueError(f"Expected one of: {options}; got {value!r}.") from exc


def _reverse_code(code_map: Mapping[Enum, int], code: int):
    for member, value in code_map.items():
        if value == code:
            return member.value
    return f"raw:{code}"



@dataclass(frozen=True)
class CardPolicy:
    """Required and forbidden optional input cards for the selected controls."""

    required: tuple[int, ...]
    forbidden: tuple[int, ...]
    optional: tuple[int, ...] = ()

    def summary_text(self) -> str:
        req = ", ".join(f"{n}*" for n in self.required) or "none"
        bad = ", ".join(f"{n}*" for n in self.forbidden) or "none"
        opt = ", ".join(f"{n}*" for n in self.optional) or "none"
        return f"Required: {req}\nForbidden: {bad}\nOptional: {opt}"


@dataclass(frozen=True)
class DeckValidation:
    """Result of validating run-control cards in an input deck."""

    valid: bool
    present_cards: tuple[int, ...]
    missing_required: tuple[int, ...]
    forbidden_present: tuple[int, ...]
    control_mismatches: tuple[str, ...]

    def summary_text(self) -> str:
        lines = [f"valid = {self.valid}"]
        lines.append("present optional cards = " + (
            ", ".join(f"{n}*" for n in self.present_cards) or "none"
        ))
        if self.missing_required:
            lines.append("missing required = " + ", ".join(f"{n}*" for n in self.missing_required))
        if self.forbidden_present:
            lines.append("forbidden present = " + ", ".join(f"{n}*" for n in self.forbidden_present))
        lines.extend(self.control_mismatches)
        return "\n".join(lines)


class DORT62Controls:
    """Named access to the positional DORT ``62$$`` integer array.

    The class intentionally behaves like a small ordered mapping.  This avoids
    asking users to remember that, for example, ``KTYPE`` is entry 25,
    ``INPFXM`` is entry 29 and ``INPSRM`` is entry 30.
    """

    def __init__(self, values: Mapping[str, int] | None = None, *, neut: int | None = None) -> None:
        self._values = {name: 0 for name in CONTROL62_NAMES}
        if values:
            self.update(**dict(values))
        self.neut = None if neut is None else self._validate_int("NEUT", neut)

    @staticmethod
    def _validate_int(name: str, value: int) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{name} must be an integer.")
        return value

    def __getitem__(self, name: str) -> int:
        key = str(name).upper()
        if key not in self._values:
            raise KeyError(f"Unknown 62$ control {name!r}.")
        return self._values[key]

    def __setitem__(self, name: str, value: int) -> None:
        key = str(name).upper()
        if key not in self._values:
            raise KeyError(f"Unknown 62$ control {name!r}.")
        self._values[key] = self._validate_int(key, value)

    def update(self, **values: int) -> "DORT62Controls":
        for name, value in values.items():
            self[name] = value
        return self

    def as_dict(self) -> dict[str, int]:
        result = dict(self._values)
        if self.neut is not None:
            result["NEUT"] = self.neut
        return result

    def as_list(self) -> list[int]:
        values = [self._values[name] for name in CONTROL62_NAMES]
        if self.neut is not None:
            values.append(self.neut)
        return values

    def copy(self) -> "DORT62Controls":
        return DORT62Controls(self._values, neut=self.neut)


class DORTRunControl:
    """Configure and validate DORT run type, file units and optional cards.

    Use :meth:`from_writer` in normal API usage so geometry/material quantities
    such as ``ISCTM``, ``IZM``, ``IM``, ``JM`` and the external cross-section
    unit are taken from the existing :class:`writer.DORTWriter`.
    """

    def __init__(
        self,
        *,
        mode: RunMode | str,
        controls62: DORT62Controls,
        ntsig: int = 51,
        flux_guess_mode: FluxGuessMode | str | None = None,
        source_mode: DistributedSourceMode | str | None = None,
        flux_guess_unit: int = 20,
        flux_output_unit: int = 21,
        distributed_source_unit: int = 23,
        print_unit: int = 6,
        guess_flux_filename: str = "guessflux.bin",
        output_flux_filename: str = "dortflux.bin",
    ) -> None:
        self.mode = RunMode(mode)
        self.controls62 = controls62.copy()
        self.ntsig = self._positive_unit("NTSIG", ntsig)
        self.flux_guess_unit = self._positive_unit("flux_guess_unit", flux_guess_unit)
        self.flux_output_unit = self._positive_unit("flux_output_unit", flux_output_unit)
        self.distributed_source_unit = self._positive_unit(
            "distributed_source_unit", distributed_source_unit
        )
        self.print_unit = self._nonnegative_unit("print_unit", print_unit)
        self.guess_flux_filename = str(guess_flux_filename)
        self.output_flux_filename = str(output_flux_filename)
        self._source: "FixedSource | None" = None

        default_flux, default_source = self._mode_defaults(self.mode)
        self.flux_guess_mode = FluxGuessMode(flux_guess_mode or default_flux)
        self.source_mode = DistributedSourceMode(source_mode or default_source)

        self._apply_mode_controls()

    @staticmethod
    def _positive_unit(name: str, value: int) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{name} must be an integer.")
        if value <= 0:
            raise ValueError(f"{name} must be positive.")
        return value

    @staticmethod
    def _nonnegative_unit(name: str, value: int) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{name} must be an integer.")
        if value < 0:
            raise ValueError(f"{name} cannot be negative.")
        return value

    @staticmethod
    def _mode_defaults(mode: RunMode) -> tuple[FluxGuessMode, DistributedSourceMode]:
        if mode is RunMode.EIGENVALUE_FIRST:
            return FluxGuessMode.FACTORIZED, DistributedSourceMode.NONE
        if mode is RunMode.EIGENVALUE_RERUN:
            return FluxGuessMode.RESTART_FILE, DistributedSourceMode.NONE
        return FluxGuessMode.FACTORIZED, DistributedSourceMode.SPACE_ENERGY

    @classmethod
    def from_writer(
        cls,
        writer: "DORTWriter",
        *,
        mode: RunMode | str,
        energy_groups: int,
        quadrature_directions: int,
        neutron_groups: int | None = None,
        total_xs_position: int = 3,
        self_scatter_position: int = 4,
        cross_section_table_length: int | None = None,
        maximum_outer_iterations: int = 10,
        initial_inner_iterations: int = 20,
        final_inner_iterations: int | None = None,
        advanced_dort62_overrides: Mapping[str, int] | None = None,
        # Backward-compatible aliases from the first run-control API.
        iht: int | None = None,
        ihs: int | None = None,
        ihm: int | None = None,
        outer_iterations: int | None = None,
        inner_iterations: int | None = None,
        controls62_overrides: Mapping[str, int] | None = None,
        **kwargs,
    ) -> "DORTRunControl":
        """Construct run controls using dimensions from a built writer.

        The solver-iteration defaults are intentionally modest and may be
        overridden.  They are not treated as run-mode semantics.
        """
        if isinstance(energy_groups, bool) or int(energy_groups) != energy_groups or energy_groups <= 0:
            raise ValueError("energy_groups must be a positive integer.")
        if isinstance(quadrature_directions, bool) or int(quadrature_directions) != quadrature_directions or quadrature_directions <= 0:
            raise ValueError("quadrature_directions must be a positive integer.")
        energy_groups = int(energy_groups)
        quadrature_directions = int(quadrature_directions)

        # Translate legacy keyword aliases, while rejecting ambiguous double input.
        if iht is not None:
            total_xs_position = iht
        if ihs is not None:
            self_scatter_position = ihs
        if ihm is not None:
            cross_section_table_length = ihm
        if outer_iterations is not None:
            maximum_outer_iterations = outer_iterations
        if inner_iterations is not None:
            initial_inner_iterations = inner_iterations
            if final_inner_iterations is None:
                final_inner_iterations = inner_iterations
        if controls62_overrides is not None:
            if advanced_dort62_overrides is not None:
                raise ValueError(
                    "Use only advanced_dort62_overrides; controls62_overrides is a legacy alias."
                )
            advanced_dort62_overrides = controls62_overrides

        if cross_section_table_length is None:
            cross_section_table_length = energy_groups + 3
        if final_inner_iterations is None:
            final_inner_iterations = initial_inner_iterations

        n_material_sets = len(writer.model.mixtures) if writer.external_mixtures_enabled else len(writer.model.materials)

        base = {
            "IADJ": 0,
            "ISCTM": writer.isctm,
            "IZM": writer.izm,
            "IM": writer.im,
            "JM": writer.jm,
            "IGM": energy_groups,
            "IHT": total_xs_position,
            "IHS": self_scatter_position,
            "IHM": cross_section_table_length,
            "MIXL": 0,
            "MCR": 0,
            "MTP": n_material_sets,
            "MTM": n_material_sets,
            "IDFAC": 0,
            "MM": quadrature_directions,
            "INGEOM": 1,
            "IBL": 1,
            "IBR": 0,
            "IBB": 0,
            "IBT": 0,
            "ISRMX": maximum_outer_iterations,
            "IFXMI": initial_inner_iterations,
            "IFXMF": final_inner_iterations,
            "MODE": 3,
            "KTYPE": 0,
            "IACC": 0,
            "KALF": 0,
            "IGTYPE": 0,
            "INPFXM": 0,
            "INPSRM": 0,
            "NJNTSR": 0,
            "NINTSR": 0,
            "NJNTFX": 0,
            "NINTFX": 0,
            "IACT": 0,
            "IRED": 0,
            "IPDB2": 0,
            "IFXPRT": 1,
            "ICSPRT": 1,
            "IDIRF": 0,
            "JDIRF": 0,
            "JDIRL": 0,
            "NBUF": 0,
            "IEPSBZ": 0,
            "MINBLK": 0,
            "MAXBLK": 0,
            "ISBT": 1,
            "MSBT": 1,
            "MSDM": 1,
            "IBFSCL": 1,
            "INTSCL": 4,
            "ITMSCL": 100,
            "NOFIS": 0,
            "IFDB2Z": 0,
            "ISWP": 0,
            "KEYJN": 1,
            "KEYIN": 1,
            "NSIGTP": 0,
            "NORPOS": 0,
            "NORMAT": 0,
            "MSTMAX": 0,
            "NEGFIX": 0,
            "LOCOBJ": 0,
            "LCMOBJ": 0,
            "NKEYFX": 0,
            "NCNDIN": 4,
        }
        if advanced_dort62_overrides:
            base.update({str(k).upper(): v for k, v in advanced_dort62_overrides.items()})
        controls = DORT62Controls(base, neut=neutron_groups)

        # Any remaining keyword whose name is part of the public settings API is
        # applied after the preset has been created.  This permits concise calls
        # such as create_run_control(..., left_boundary="reflected").
        public_settings = {
            key: kwargs.pop(key)
            for key in list(kwargs)
            if key in _SETTING_BY_NAME and not _SETTING_BY_NAME[key].read_only
        }

        run = cls(
            mode=mode,
            controls62=controls,
            ntsig=writer.cross_section_unit,
            **kwargs,
        )
        if public_settings:
            run.configure(**public_settings)
        return run

    def _apply_mode_controls(self) -> None:
        c = self.controls62
        # Run type.
        if self.mode in {RunMode.EIGENVALUE_FIRST, RunMode.EIGENVALUE_RERUN}:
            c["KTYPE"] = 1
            c["NOFIS"] = 0
            # These two values reproduce the supplied eigenvalue control style.
            c["IACC"] = 0
            c["KALF"] = 1
        else:
            c["KTYPE"] = 0
            c["NOFIS"] = 2
            # Supplied fixed-source deck settings; still user-overridable after creation.
            c["IACC"] = 2
            c["KALF"] = 0

        c["INPFXM"] = _INPFXM_BY_MODE[self.flux_guess_mode]
        c["INPSRM"] = _INPSRM_BY_MODE[self.source_mode]

    @property
    def settings(self) -> dict[str, object]:
        """Return a snapshot of the human-readable run settings."""
        return {spec.name: self.get_setting(spec.name) for spec in SETTING_SPECS}

    def get_setting(self, name: str):
        """Return one human-readable setting value."""
        try:
            spec = _SETTING_BY_NAME[str(name)]
        except KeyError as exc:
            raise KeyError(
                f"Unknown setting {name!r}. Use available_options() or settings_help()."
            ) from exc

        if spec.name == "starting_flux":
            return self.flux_guess_mode.value
        if spec.name == "distributed_source":
            return self.source_mode.value

        raw = self.controls62[spec.dort_name]
        if spec.enum_type is not None and spec.code_map is not None:
            return _reverse_code(spec.code_map, raw)
        if spec.boolean:
            return bool(raw)
        return raw

    def configure(self, **settings) -> "DORTRunControl":
        """Modify run controls using descriptive public setting names.

        Examples
        --------
        >>> run.configure(
        ...     maximum_outer_iterations=20,
        ...     left_boundary="reflected",
        ...     flux_extrapolation="theta_weighted",
        ... )

        Use :meth:`available_options` to discover enumerated choices and
        :meth:`settings_help` for a complete table.
        """
        for name, value in settings.items():
            if name not in _SETTING_BY_NAME:
                raise KeyError(
                    f"Unknown human-readable setting {name!r}. "
                    "Use settings_help() to list available names."
                )
            spec = _SETTING_BY_NAME[name]
            if spec.read_only:
                raise ValueError(
                    f"{name!r} is derived automatically and cannot be changed directly."
                )

            if name == "starting_flux":
                self.flux_guess_mode = _coerce_enum(FluxGuessMode, value)
                self.controls62["INPFXM"] = _INPFXM_BY_MODE[self.flux_guess_mode]
                continue
            if name == "distributed_source":
                self.source_mode = _coerce_enum(DistributedSourceMode, value)
                self.controls62["INPSRM"] = _INPSRM_BY_MODE[self.source_mode]
                continue

            if spec.enum_type is not None and spec.code_map is not None:
                member = _coerce_enum(spec.enum_type, value)
                self.controls62[spec.dort_name] = spec.code_map[member]
            elif spec.boolean:
                if not isinstance(value, bool):
                    raise TypeError(f"{name} must be True or False.")
                self.controls62[spec.dort_name] = int(value)
            elif spec.integer:
                if isinstance(value, bool) or not isinstance(value, int):
                    raise TypeError(f"{name} must be an integer.")
                self.controls62[spec.dort_name] = value
            else:
                raise RuntimeError(f"Unsupported setting specification for {name!r}.")

        self.validate()
        return self

    def available_options(self, name: str | None = None):
        """Return discoverable choices for one setting or all public settings."""
        if name is not None:
            if name not in _SETTING_BY_NAME:
                raise KeyError(f"Unknown setting {name!r}.")
            return _SETTING_BY_NAME[name].options
        return {spec.name: spec.options for spec in SETTING_SPECS}

    def describe_setting(self, name: str) -> str:
        """Describe a setting, its current value, options and DORT mapping."""
        if name not in _SETTING_BY_NAME:
            raise KeyError(f"Unknown setting {name!r}.")
        spec = _SETTING_BY_NAME[name]
        options = ", ".join(spec.options) if spec.options else "n/a"
        raw = f" ({spec.dort_name})" if spec.dort_name else ""
        derived = " [automatic]" if spec.read_only else ""
        return (
            f"{name}{raw}{derived}\n"
            f"  current: {self.get_setting(name)}\n"
            f"  options: {options}\n"
            f"  {spec.description}"
        )

    def settings_help(self, *, include_automatic: bool = True) -> str:
        """Return a human-readable table of settings and available options."""
        rows = []
        for spec in SETTING_SPECS:
            if spec.read_only and not include_automatic:
                continue
            options = "|".join(spec.options) if spec.options else ""
            if spec.read_only:
                options = "automatic"
            rows.append((spec.name, str(self.get_setting(spec.name)), options, spec.dort_name or ""))

        widths = [
            max(len(title), *(len(row[i]) for row in rows))
            for i, title in enumerate(("Setting", "Current", "Options", "DORT"))
        ]
        header = (
            f"{'Setting':<{widths[0]}}  {'Current':<{widths[1]}}  "
            f"{'Options':<{widths[2]}}  {'DORT':<{widths[3]}}"
        )
        lines = [header, "-" * len(header)]
        for row in rows:
            lines.append(
                f"{row[0]:<{widths[0]}}  {row[1]:<{widths[1]}}  "
                f"{row[2]:<{widths[2]}}  {row[3]:<{widths[3]}}"
            )
        return "\n".join(lines)

    def set_raw_dort62(self, **values: int) -> "DORTRunControl":
        """Advanced escape hatch: override raw DORT ``62$$`` variable names."""
        self.controls62.update(**values)
        self.validate()
        return self

    def set62(self, **values: int) -> "DORTRunControl":
        """Legacy alias for :meth:`set_raw_dort62`.

        New code should prefer :meth:`configure` with human-readable names.
        """
        return self.set_raw_dort62(**values)

    @property
    def source(self):
        """Attached :class:`source.FixedSource`, or ``None`` when not defined."""
        return self._source

    def attach_source(self, source: "FixedSource") -> "DORTRunControl":
        """Attach a mesh-based fixed source and select ``space_energy`` mode.

        The attached source must use the same ``(JM, IM)`` mesh shape and its
        energy spectrum must contain exactly ``IGM`` values.  This method sets
        the public distributed-source representation to ``space_energy``, for
        which cards 96** and 98** are required and 97** is forbidden.
        """
        if self.mode is not RunMode.FIXED_SOURCE:
            raise ValueError("A distributed fixed source can only be attached to fixed_source mode.")
        from source import FixedSource
        if not isinstance(source, FixedSource):
            raise TypeError("source must be a source.FixedSource instance.")
        expected_shape = (self.controls62["JM"], self.controls62["IM"])
        if source.spatial.shape != expected_shape:
            raise ValueError(
                f"Source shape {source.spatial.shape} does not match DORT mesh {expected_shape}."
            )
        source.validate(energy_groups=self.controls62["IGM"])
        self._source = source
        self.source_mode = DistributedSourceMode.SPACE_ENERGY
        self.controls62["INPSRM"] = _INPSRM_BY_MODE[self.source_mode]
        self.validate()
        return self

    def source_fragment(self) -> str:
        """Generate attached fixed-source cards 96** and 98**."""
        if self._source is None:
            raise RuntimeError(
                "No fixed source is attached. Create one with writer.create_source() "
                "and call run.attach_source(source)."
            )
        if self.source_mode is not DistributedSourceMode.SPACE_ENERGY:
            raise ValueError(
                "The mesh-based source builder serializes INPSRM=2 (space_energy) only."
            )
        return self._source.fragment(energy_groups=self.controls62["IGM"])

    def control_and_source_fragment(
        self, *, include_63: bool = True, line_width: int = 72
    ) -> str:
        """Return 61$$/62$$/63** followed by attached 96**/98** cards."""
        return self.control_fragment(include_63=include_63, line_width=line_width) + "\n" + self.source_fragment()

    @property
    def file_units(self) -> dict[str, int]:
        ntflx = self.flux_guess_unit if self.flux_guess_mode is FluxGuessMode.RESTART_FILE else 0
        ntdsi = self.distributed_source_unit if self.source_mode is not DistributedSourceMode.NONE else 0
        return {
            "NTFLX": ntflx,
            "NTFOG": self.flux_output_unit,
            "NTSIG": self.ntsig,
            "NTBSI": 0,
            "NTDSI": ntdsi,
            "NTFCI": 0,
            "NTIBI": 0,
            "NTIBO": 0,
            "NTNPR": self.print_unit,
            "NTDIR": 0,
            "NTDSO": 0,
            "NTSCL": 0,
            "NTZNF": 0,
        }

    @property
    def card_policy(self) -> CardPolicy:
        inpfxm = self.controls62["INPFXM"]
        inpsrm = self.controls62["INPSRM"]
        required: set[int] = set()
        forbidden: set[int] = set()

        # Flux-guess cards 93..95.
        if inpfxm == 0:
            forbidden.update((93, 94, 95))
        elif inpfxm == 1:
            required.add(93); forbidden.update((94, 95))
        elif inpfxm == 2:
            required.update((93, 95)); forbidden.add(94)
        elif inpfxm == 3:
            required.update((93, 94, 95))
        else:
            raise ValueError(f"Unsupported INPFXM={inpfxm}; expected 0..3.")

        # Distributed-source cards 96..98.
        if inpsrm == 0:
            forbidden.update((96, 97, 98))
        elif inpsrm == 1:
            required.add(96); forbidden.update((97, 98))
        elif inpsrm == 2:
            required.update((96, 98)); forbidden.add(97)
        elif inpsrm == 3:
            required.update((96, 97, 98))
        else:
            raise ValueError(f"Unsupported INPSRM={inpsrm}; expected 0..3.")

        return CardPolicy(tuple(sorted(required)), tuple(sorted(forbidden)))

    def validate(self) -> None:
        """Validate consistency between 61$$ units, 62$$ controls and run mode."""
        c = self.controls62
        if self.mode in {RunMode.EIGENVALUE_FIRST, RunMode.EIGENVALUE_RERUN} and c["KTYPE"] != 1:
            raise ValueError("Eigenvalue run modes require KTYPE=1.")
        if self.mode is RunMode.FIXED_SOURCE and c["KTYPE"] != 0:
            raise ValueError("fixed_source requires KTYPE=0.")

        if self.flux_guess_mode is FluxGuessMode.RESTART_FILE:
            if c["INPFXM"] != 0 or self.file_units["NTFLX"] <= 0:
                raise ValueError("Restart flux requires INPFXM=0 and NTFLX>0.")
        elif c["INPFXM"] > 0 and self.file_units["NTFLX"] != 0:
            raise ValueError("Explicit 93*-95* flux guess should use NTFLX=0.")

        if c["INPSRM"] > 0 and self.file_units["NTDSI"] <= 0:
            raise ValueError("INPSRM>0 requires a non-zero NTDSI in this workflow.")
        if c["INPSRM"] == 0 and self.file_units["NTDSI"] != 0:
            raise ValueError("INPSRM=0 should not use a distributed-source input unit.")

    def array61(self, *, line_width: int = 72) -> str:
        self.validate()
        fields = [str(self.file_units[name]) for name in CONTROL61_NAMES] + ["E"]
        return _wrap_fields("61$$", fields, width=line_width)

    def array62(self, *, line_width: int = 72, fields_per_line: int = 10) -> str:
        self.validate()
        values = self.controls62.as_list()
        return _format_positional_array("62$$", values, fields_per_line=fields_per_line, line_width=line_width)

    def array63(self, *, line_width: int = 72) -> str:
        """Return a mode-appropriate default 63** real-control array.

        The eigenvalue form reproduces the compact 12-value pattern in the two
        supplied eigenvalue decks.  The fixed-source form reproduces the full
        28-value pattern in the supplied fixed-source deck.  Users may replace
        this card if their convergence strategy differs.
        """
        if self.mode in {RunMode.EIGENVALUE_FIRST, RunMode.EIGENVALUE_RERUN}:
            values = [
                0.0, 1.0, 1.0e-4, 1.0e-3, 1.0e-5, 1.0e-3,
                1.0, 0.2, 1.5, 10.0, 1.0, 1.03126,
            ]
        else:
            values = [
                0.0, 0.0, 1.0e-4, 1.0e-3, 1.0e-5, 1.0e-3,
                1.0, 0.2, 1.5, 10.0, 1.0, 1.0, -1.0, 0.3,
                1.2, 3.0e-2, 1.0e-4, 0.0, 0.3, 1.0, 2.0, 0.6,
                0.0, 1.0e-30, 0.0, 1.0, 0.1, 0.9,
            ]
        fields = [_format_real(v) for v in values] + ["E"]
        return _wrap_fields("63**", fields, width=line_width)

    def control_fragment(self, *, include_63: bool = True, line_width: int = 72) -> str:
        """Generate the 61$$/62$$/(optional)63** control fragment."""
        parts = [self.array61(line_width=line_width), self.array62(line_width=line_width)]
        if include_63:
            parts.append(self.array63(line_width=line_width))
        return "\n".join(parts)

    def validate_present_cards(self, cards: Iterable[int]) -> DeckValidation:
        present = tuple(sorted({int(card) for card in cards if 93 <= int(card) <= 98}))
        policy = self.card_policy
        missing = tuple(card for card in policy.required if card not in present)
        forbidden = tuple(card for card in policy.forbidden if card in present)
        return DeckValidation(
            valid=not missing and not forbidden,
            present_cards=present,
            missing_required=missing,
            forbidden_present=forbidden,
            control_mismatches=(),
        )

    def validate_deck_text(
        self,
        text: str,
        *,
        strict_controls: bool = False,
    ) -> DeckValidation:
        """Check run selectors and 93*..98* card presence in an input deck.

        Parameters
        ----------
        text
            Complete DORT input text.
        strict_controls
            If ``False`` (default), compare only the fields that define the run
            workflow: relevant file units plus ``KTYPE``, ``INPFXM``,
            ``INPSRM`` and ``NOFIS``.  If ``True``, compare every supplied
            61$$/62$$ entry against this profile.
        """
        cards = _find_cards(text)
        result = self.validate_present_cards(cards)
        mismatches: list[str] = []

        parsed61 = _parse_integer_card(text, 61)
        if parsed61 is not None:
            actual61 = dict(zip(CONTROL61_NAMES, parsed61))
            compare61 = CONTROL61_NAMES if strict_controls else ("NTFLX", "NTFOG", "NTSIG", "NTDSI")
            for name in compare61:
                if name in actual61 and actual61[name] != self.file_units[name]:
                    mismatches.append(
                        f"61$ {name}: deck={actual61[name]}, profile={self.file_units[name]}"
                    )

        parsed62 = _parse_integer_card(text, 62)
        if parsed62 is not None:
            actual62 = dict(zip(CONTROL62_NAMES, parsed62[:len(CONTROL62_NAMES)]))
            compare62 = CONTROL62_NAMES if strict_controls else ("KTYPE", "INPFXM", "INPSRM", "NOFIS")
            for name in compare62:
                if name in actual62 and actual62[name] != self.controls62[name]:
                    mismatches.append(
                        f"62$ {name}: deck={actual62[name]}, profile={self.controls62[name]}"
                    )
            if strict_controls and self.controls62.neut is not None and len(parsed62) > len(CONTROL62_NAMES):
                actual_neut = parsed62[len(CONTROL62_NAMES)]
                if actual_neut != self.controls62.neut:
                    mismatches.append(
                        f"62$ NEUT: deck={actual_neut}, profile={self.controls62.neut}"
                    )

        return DeckValidation(
            valid=result.valid and not mismatches,
            present_cards=result.present_cards,
            missing_required=result.missing_required,
            forbidden_present=result.forbidden_present,
            control_mismatches=tuple(mismatches),
        )

    def prepare_rerun_flux(self, directory: str | Path = ".", *, overwrite: bool = False) -> Path:
        """Copy ``dortflux.bin`` to ``guessflux.bin`` for an eigenvalue rerun.

        The files are copied byte-for-byte; no attempt is made to interpret the
        Fortran unformatted records.
        """
        if self.flux_guess_mode is not FluxGuessMode.RESTART_FILE:
            raise ValueError(
                "prepare_rerun_flux() requires starting_flux='restart_file'."
            )
        directory = Path(directory)
        source = directory / self.output_flux_filename
        target = directory / self.guess_flux_filename
        if not source.is_file():
            raise FileNotFoundError(source)
        if target.exists() and not overwrite:
            raise FileExistsError(
                f"{target} already exists. Pass overwrite=True to replace it."
            )
        shutil.copyfile(source, target)
        return target

    def summary_text(self) -> str:
        self.validate()
        c = self.controls62
        lines = [
            f"Base run profile: {self.mode.value}",
            f"Starting flux: {self.flux_guess_mode.value}",
            f"Distributed source: {self.source_mode.value}",
            f"Outer-iteration limit: {self.get_setting('maximum_outer_iterations')}",
            f"Inner-iteration limits: {self.get_setting('initial_inner_iterations')} -> "
            f"{self.get_setting('final_inner_iterations')}",
            f"Boundaries: left={self.get_setting('left_boundary')}, "
            f"right={self.get_setting('right_boundary')}, "
            f"bottom={self.get_setting('bottom_boundary')}, "
            f"top={self.get_setting('top_boundary')}",
            "",
            "File units:",
            f"  starting-flux input = {self.file_units['NTFLX']}",
            f"  flux output = {self.file_units['NTFOG']}  ({self.output_flux_filename}, unformatted)",
            f"  cross sections = {self.file_units['NTSIG']}  (mixf.cr workflow)",
            f"  distributed-source input = {self.file_units['NTDSI']}",
            "",
            "Optional-card policy:",
            self.card_policy.summary_text(),
            "",
            "Raw DORT selectors (reference only):",
            f"  KTYPE={c['KTYPE']}  INPFXM={c['INPFXM']}  INPSRM={c['INPSRM']}  NOFIS={c['NOFIS']}",
        ]
        if self.mode is RunMode.EIGENVALUE_RERUN:
            lines += [
                "",
                "Restart file flow:",
                f"  previous unit {self.flux_output_unit}: {self.output_flux_filename}",
                f"        -> copy/rename to unit {self.flux_guess_unit}: {self.guess_flux_filename}",
            ]
        return "\n".join(lines)


def _format_real(value: float) -> str:
    value = float(value)
    if value == 0.0:
        return "0.0"
    if 1.0e-4 <= abs(value) < 1.0e7:
        return f"{value:.8g}"
    return f"{value:.8E}"


def _wrap_fields(origin: str, fields: list[str], *, width: int = 72) -> str:
    lines: list[str] = []
    current = origin.rstrip()
    for field in fields:
        token = str(field).strip()
        candidate = f"{current} {token}" if current else token
        if len(candidate) <= width:
            current = candidate
        else:
            lines.append(current.rstrip())
            current = "    " + token
    if current:
        lines.append(current.rstrip())
    return "\n".join(lines)


def _format_positional_array(
    origin: str,
    values: list[int],
    *,
    fields_per_line: int = 10,
    line_width: int = 72,
) -> str:
    # Preserve the human-readable 10-values-per-line style used by the supplied decks.
    lines: list[str] = []
    for start in range(0, len(values), fields_per_line):
        chunk = values[start:start + fields_per_line]
        prefix = origin if start == 0 else "    "
        line = prefix + " " + " ".join(f"{v:d}" for v in chunk)
        if len(line) > line_width:
            # Fall back to ordinary free-field wrapping if unusually large integers appear.
            return _wrap_fields(origin, [str(v) for v in values] + ["E"], width=line_width)
        lines.append(line.rstrip())
    if lines:
        lines[-1] += " E"
    return "\n".join(lines)


def _find_cards(text: str) -> set[int]:
    return {
        int(m.group(1))
        for m in re.finditer(r"(?m)^\s*(\d+)(?:\$\$|\*\*)", text)
    }


def _parse_integer_card(text: str, card: int) -> list[int] | None:
    lines = text.splitlines()
    pattern = re.compile(rf"^\s*{card}\$\$")
    start = next((i for i, line in enumerate(lines) if pattern.match(line)), None)
    if start is None:
        return None
    block = lines[start]
    i = start + 1
    while not re.search(r"\be\b", block, flags=re.IGNORECASE) and i < len(lines):
        block += " " + lines[i]
        i += 1
    block = pattern.sub("", block, count=1)
    block = re.split(r"\be\b", block, maxsplit=1, flags=re.IGNORECASE)[0]
    return [int(x) for x in re.findall(r"[-+]?\d+", block)]
