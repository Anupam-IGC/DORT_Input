"""External microscopic-to-macroscopic mixture preparation for local DORT.

The locally modified DORT workflow used by this project does *not* use the
standard in-core DORT mixing table (10$/11$/12*).  Instead, an external
Fortran program reads ``mix.inp`` plus the microscopic ``igc-s3`` library and
writes a macroscopic cross-section file, normally ``mixf.cr``.

The recommended user workflow is spreadsheet-driven.  A workbook sheet
(default name ``Read``) contains ``Nuclide`` and ``MAT No.`` in the first
two columns, followed by one column per final mixture.  Nonblank cells are
atom densities.  The external mixer stores every physical mixture as
``L + 1`` consecutive cross-section records, where ``L`` is the Legendre order::

    mixture 1, P5 -> records  1..6 -> DORT 9$ value  -1
    mixture 2, P5 -> records  7..12 -> DORT 9$ value -7
    mixture 3, P5 -> records 13..18 -> DORT 9$ value -13

Thus the Python API keeps the user-facing mixture sequence natural
(1, 2, 3, ...) and derives the negative 9$ reference automatically.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import Iterable, Iterator, Mapping


# Limits hard-coded in the supplied m_ia_oa.for external mixture program.
MAX_MIXTURES = 70
MAX_COMPONENTS_PER_MIXTURE = 20
MAX_DISTINCT_MICRO_MATERIALS = 112
MAX_LEGENDRE_ORDER = 6
DEFAULT_ENERGY_GROUPS = 217
DEFAULT_COLUMNS_PER_GROUP = 220
DEFAULT_VALUES_PER_TABLE = DEFAULT_ENERGY_GROUPS * DEFAULT_COLUMNS_PER_GROUP


@dataclass(frozen=True)
class MixtureWorkbookSummary:
    """Summary of a spreadsheet mixture import.

    Parameters
    ----------
    filename
        Workbook used for the import.
    sheet_name
        Worksheet containing the mixture table.
    mixture_names
        Mixture columns in left-to-right workbook order.
    nuclide_rows
        Number of workbook rows containing a MAT number.
    legendre_order
        Common P_L order used for local DORT table numbering.
    """

    filename: str
    sheet_name: str
    mixture_names: tuple[str, ...]
    nuclide_rows: int
    legendre_order: int

    @property
    def mixture_count(self) -> int:
        return len(self.mixture_names)

    def summary_text(self) -> str:
        return (
            f"Workbook: {self.filename}\n"
            f"Sheet: {self.sheet_name}\n"
            f"Mixtures: {self.mixture_count}\n"
            f"Nuclide/MAT rows: {self.nuclide_rows}\n"
            f"Legendre order: P{self.legendre_order}\n"
            f"Mixture order: {', '.join(self.mixture_names)}"
        )


@dataclass(frozen=True)
class MixtureComponent:
    """One microscopic material contribution to a macroscopic mixture.

    Parameters
    ----------
    mat_number
        Integer microscopic material identifier appearing in the ``igc-s3``
        library and in ``mix.inp``.
    atom_density
        Atom density multiplier used by the external mixer.
    nuclide
        Optional readable nuclide/element label from the spreadsheet.
    """

    mat_number: int
    atom_density: float
    nuclide: str = ""

    def __post_init__(self) -> None:
        if isinstance(self.mat_number, bool) or not isinstance(self.mat_number, int):
            raise TypeError("mat_number must be an integer.")
        if self.mat_number <= 0:
            raise ValueError("mat_number must be a positive integer.")

        density = float(self.atom_density)
        if not isfinite(density):
            raise ValueError("atom_density must be finite.")
        if density < 0.0:
            raise ValueError("atom_density cannot be negative.")
        object.__setattr__(self, "atom_density", density)
        object.__setattr__(self, "nuclide", str(self.nuclide).strip())


@dataclass(frozen=True)
class Mixture:
    """One final macroscopic mixture produced by the external mixer."""

    name: str
    mixture_id: int
    components: tuple[MixtureComponent, ...]
    description: str = ""

    def __post_init__(self) -> None:
        name = str(self.name).strip()
        if not name:
            raise ValueError("Mixture name cannot be empty.")
        if isinstance(self.mixture_id, bool) or not isinstance(self.mixture_id, int):
            raise TypeError("mixture_id must be an integer.")
        if self.mixture_id <= 0:
            raise ValueError("mixture_id must be positive.")
        if not self.components:
            raise ValueError(f"Mixture {name!r} must contain at least one component.")
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "description", str(self.description).strip())


@dataclass(frozen=True)
class MixtureFileValidation:
    """Result of validating a generated ``mixf.cr`` file."""

    valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    table_count: int
    expected_table_count: int
    values_per_table: int

    def __bool__(self) -> bool:
        return self.valid

    def summary_text(self) -> str:
        lines = [
            f"valid = {self.valid}",
            f"tables = {self.table_count} (expected {self.expected_table_count})",
            f"values/table = {self.values_per_table}",
        ]
        if self.errors:
            lines.append("errors:")
            lines.extend(f"  - {item}" for item in self.errors)
        if self.warnings:
            lines.append("warnings:")
            lines.extend(f"  - {item}" for item in self.warnings)
        return "\n".join(lines)


class MixtureRegistry:
    """Manage external macroscopic mixtures in natural-number order.

    Components are microscopic MAT numbers, not DORT material-set numbers.
    The registry mirrors the supplied ``m_ia_oa.for`` input structure.
    """

    def __init__(self) -> None:
        self._mixtures: dict[str, Mixture] = {}

    @staticmethod
    def _normalize_components(
        components: Mapping[int, float]
        | Iterable[tuple[int, float] | MixtureComponent],
    ) -> tuple[MixtureComponent, ...]:
        raw = components.items() if isinstance(components, Mapping) else components
        result: list[MixtureComponent] = []
        seen: set[int] = set()

        for item in raw:
            if isinstance(item, MixtureComponent):
                component = item
            else:
                values = tuple(item)
                if len(values) == 2:
                    component = MixtureComponent(values[0], values[1])
                elif len(values) == 3:
                    component = MixtureComponent(values[0], values[1], values[2])
                else:
                    raise ValueError(
                        "Mixture component tuples must be (MAT, density) or "
                        "(MAT, density, nuclide_label)."
                    )
            if component.mat_number in seen:
                raise ValueError(
                    f"Microscopic MAT {component.mat_number} is repeated in one mixture. "
                    "Combine repeated contributions into a single atom density."
                )
            seen.add(component.mat_number)
            result.append(component)

        if not result:
            raise ValueError("A mixture must contain at least one microscopic material.")
        if len(result) > MAX_COMPONENTS_PER_MIXTURE:
            raise ValueError(
                f"The supplied external mixer supports at most "
                f"{MAX_COMPONENTS_PER_MIXTURE} components per mixture."
            )
        return tuple(result)

    def add(
        self,
        name: str,
        components: Mapping[int, float]
        | Iterable[tuple[int, float] | MixtureComponent],
        *,
        mixture_id: int | None = None,
        description: str = "",
    ) -> Mixture:
        """Register a mixture in the sequence 1, 2, 3, ... ."""
        name = str(name).strip()
        if not name:
            raise ValueError("Mixture name cannot be empty.")
        if name in self._mixtures:
            raise ValueError(f"Mixture {name!r} is already registered.")
        if len(self._mixtures) >= MAX_MIXTURES:
            raise ValueError(
                f"The supplied external mixer supports at most {MAX_MIXTURES} mixtures."
            )

        expected = len(self._mixtures) + 1
        if mixture_id is None:
            mixture_id = expected
        elif isinstance(mixture_id, bool) or not isinstance(mixture_id, int):
            raise TypeError("mixture_id must be an integer or None.")
        elif mixture_id != expected:
            raise ValueError(
                "Mixtures must follow the natural sequence 1, 2, 3, ...; "
                f"the next mixture_id must be {expected}, not {mixture_id}."
            )

        mixture = Mixture(
            name=name,
            mixture_id=mixture_id,
            components=self._normalize_components(components),
            description=description,
        )
        self._mixtures[name] = mixture
        self.validate()
        return mixture

    def replace(
        self,
        name: str,
        components: Mapping[int, float]
        | Iterable[tuple[int, float] | MixtureComponent],
        *,
        description: str | None = None,
    ) -> Mixture:
        if name not in self._mixtures:
            raise KeyError(f"Mixture {name!r} is not registered.")
        old = self._mixtures[name]
        mixture = Mixture(
            name=old.name,
            mixture_id=old.mixture_id,
            components=self._normalize_components(components),
            description=old.description if description is None else description,
        )
        self._mixtures[name] = mixture
        self.validate()
        return mixture

    def get(self, name: str) -> Mixture:
        try:
            return self._mixtures[name]
        except KeyError as exc:
            raise KeyError(f"Mixture {name!r} is not registered.") from exc

    def get_by_id(self, mixture_id: int) -> Mixture:
        for mixture in self._mixtures.values():
            if mixture.mixture_id == mixture_id:
                return mixture
        raise KeyError(f"No mixture is registered with mixture_id {mixture_id}.")

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(self._mixtures.keys())

    @property
    def mixtures(self) -> tuple[Mixture, ...]:
        return tuple(self._mixtures.values())

    @property
    def ids(self) -> tuple[int, ...]:
        return tuple(mixture.mixture_id for mixture in self._mixtures.values())

    @property
    def distinct_mat_numbers(self) -> tuple[int, ...]:
        """Return microscopic MAT numbers in first-occurrence order."""
        result: list[int] = []
        seen: set[int] = set()
        for mixture in self._mixtures.values():
            for component in mixture.components:
                if component.mat_number not in seen:
                    seen.add(component.mat_number)
                    result.append(component.mat_number)
        return tuple(result)

    @classmethod
    def from_excel(
        cls,
        filename: str | Path,
        *,
        sheet_name: str = "Read",
        nuclide_column: str = "Nuclide",
        mat_column: str = "MAT No.",
    ) -> "MixtureRegistry":
        """Create a registry from the spreadsheet format used by ``mixture.py``.

        The worksheet must contain the readable nuclide label and microscopic
        MAT number columns first, followed by one or more final-mixture columns.
        A nonblank cell in a mixture column is interpreted as that MAT's atom
        density in the mixture.  Mixture IDs follow the spreadsheet column
        order exactly.
        """
        try:
            import pandas as pd
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise ImportError(
                "Spreadsheet mixture import requires pandas and openpyxl. "
                "Install project requirements before using from_excel()."
            ) from exc

        path = Path(filename)
        if not path.is_file():
            raise FileNotFoundError(path)

        data = pd.read_excel(path, sheet_name=sheet_name)
        columns = [str(c).strip() for c in data.columns]
        data.columns = columns

        for required in (nuclide_column, mat_column):
            if required not in data.columns:
                raise ValueError(
                    f"Worksheet {sheet_name!r} must contain column {required!r}. "
                    f"Found columns: {columns}."
                )

        mat_position = columns.index(mat_column)
        mixture_names = [str(c).strip() for c in columns[mat_position + 1 :]]
        if not mixture_names:
            raise ValueError(
                f"Worksheet {sheet_name!r} contains no mixture columns after {mat_column!r}."
            )
        if any(not name or name.lower().startswith("unnamed:") for name in mixture_names):
            raise ValueError("All mixture columns must have non-empty names.")
        if len(mixture_names) != len(set(mixture_names)):
            raise ValueError("Mixture column names must be unique.")

        registry = cls()
        for mixture_name in mixture_names:
            raw_density = data[mixture_name]
            mask = ~raw_density.isna()
            if not bool(mask.any()):
                raise ValueError(
                    f"Mixture column {mixture_name!r} contains no atom densities."
                )

            components: list[MixtureComponent] = []
            seen_mat: set[int] = set()
            for row_index in data.index[mask]:
                mat_raw = data.at[row_index, mat_column]
                if pd.isna(mat_raw):
                    raise ValueError(
                        f"Mixture {mixture_name!r} has a density on spreadsheet row "
                        f"{int(row_index) + 2}, but {mat_column!r} is blank."
                    )
                try:
                    mat_float = float(mat_raw)
                except (TypeError, ValueError) as exc:
                    raise ValueError(
                        f"Invalid MAT number {mat_raw!r} on spreadsheet row "
                        f"{int(row_index) + 2}."
                    ) from exc
                mat_number = int(round(mat_float))
                if mat_number <= 0 or abs(mat_float - mat_number) > 1.0e-9:
                    raise ValueError(
                        f"MAT number on spreadsheet row {int(row_index) + 2} must be "
                        f"a positive integer; found {mat_raw!r}."
                    )
                if mat_number in seen_mat:
                    raise ValueError(
                        f"MAT {mat_number} occurs more than once in mixture "
                        f"{mixture_name!r}."
                    )
                seen_mat.add(mat_number)

                density_raw = data.at[row_index, mixture_name]
                try:
                    density = float(density_raw)
                except (TypeError, ValueError) as exc:
                    raise ValueError(
                        f"Invalid density {density_raw!r} for mixture {mixture_name!r} "
                        f"on spreadsheet row {int(row_index) + 2}."
                    ) from exc
                if not isfinite(density) or density < 0.0:
                    raise ValueError(
                        f"Density for mixture {mixture_name!r} on spreadsheet row "
                        f"{int(row_index) + 2} must be finite and non-negative."
                    )

                nuclide_raw = data.at[row_index, nuclide_column]
                nuclide = "" if pd.isna(nuclide_raw) else str(nuclide_raw).strip()
                components.append(MixtureComponent(mat_number, density, nuclide))

            registry.add(mixture_name, components)

        return registry

    def workbook_summary(
        self,
        filename: str | Path,
        *,
        sheet_name: str,
        legendre_order: int,
        nuclide_rows: int,
    ) -> MixtureWorkbookSummary:
        """Return a compact description of a spreadsheet import."""
        order = self._validate_legendre_order(legendre_order)
        return MixtureWorkbookSummary(
            filename=str(Path(filename)),
            sheet_name=sheet_name,
            mixture_names=self.names,
            nuclide_rows=int(nuclide_rows),
            legendre_order=order,
        )

    def render_mixture_names(self) -> str:
        """Render ``Mixture_Names.txt`` in the format used by ``mixture.py``."""
        lines = ["Mixture Number\tMixture Name"]
        lines.extend(f"{m.mixture_id}\t{m.name}" for m in self._mixtures.values())
        return "\n".join(lines)

    def write_mixture_names(self, filename: str | Path) -> Path:
        path = Path(filename)
        path.write_text(self.render_mixture_names() + "\n", encoding="utf-8")
        return path

    def render_dort_mix_cards(self, legendre_order: int) -> str:
        """Render the script-compatible ``84$$`` and negative ``9$$`` cards.

        This compact pair corresponds to one DORT zone per mixture/material,
        exactly as in the supplied standalone ``mixture.py``.  When a
        :class:`writer.DORTWriter` uses ``zone_policy='region'``, use the
        writer's ``array84_by_material()`` and ``array9()`` instead because the
        number of DORT zones may exceed the number of mixtures.
        """
        order = self._validate_legendre_order(legendre_order)
        zone_values = " ".join(str(m.mixture_id) for m in self._mixtures.values())
        material_values = " ".join(
            str(self.dort_material_number(m.mixture_id, order))
            for m in self._mixtures.values()
        )
        return f"84$$ {zone_values} t\n9$$ {material_values} t"

    def write_dort_mix_cards(self, filename: str | Path, legendre_order: int) -> Path:
        path = Path(filename)
        path.write_text(self.render_dort_mix_cards(legendre_order) + "\n", encoding="ascii")
        return path

    def write_preparation_files(
        self,
        output_dir: str | Path,
        legendre_order: int,
        *,
        mix_input_name: str = "mix.inp",
        mixture_names_name: str = "Mixture_Names.txt",
        dort_cards_name: str = "dort_mix_cards.txt",
    ) -> dict[str, Path]:
        """Write all three files produced by the supplied ``mixture.py`` workflow."""
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        return {
            "mix_input": self.write_mix_input(output / mix_input_name, legendre_order),
            "mixture_names": self.write_mixture_names(output / mixture_names_name),
            "dort_cards": self.write_dort_mix_cards(output / dort_cards_name, legendre_order),
        }

    def validate(self, *, material_names: tuple[str, ...] | None = None) -> None:
        ids = list(self.ids)
        expected = list(range(1, len(ids) + 1))
        if ids != expected:
            raise ValueError(
                f"Mixture IDs must be the natural sequence {expected}; found {ids}."
            )
        if len(self.distinct_mat_numbers) > MAX_DISTINCT_MICRO_MATERIALS:
            raise ValueError(
                f"The external mixer supports at most {MAX_DISTINCT_MICRO_MATERIALS} "
                "distinct microscopic MAT numbers."
            )
        if material_names is not None and self.names:
            # Mixtures need not cover unused model materials, but their ordering
            # must match the natural material order for names they define.
            for mixture in self._mixtures.values():
                if mixture.name not in material_names:
                    raise ValueError(
                        f"Mixture {mixture.name!r} has no corresponding model material."
                    )
                material_id = material_names.index(mixture.name) + 1
                if material_id != mixture.mixture_id:
                    raise ValueError(
                        f"Mixture {mixture.name!r} has mixture_id={mixture.mixture_id}, "
                        f"but the corresponding material ID is {material_id}."
                    )

    @staticmethod
    def _validate_legendre_order(legendre_order: int) -> int:
        if isinstance(legendre_order, bool) or not isinstance(legendre_order, int):
            raise TypeError("legendre_order must be an integer.")
        if not 0 <= legendre_order <= MAX_LEGENDRE_ORDER:
            raise ValueError(
                f"The supplied m_ia_oa.for mixer supports Legendre orders 0.."
                f"{MAX_LEGENDRE_ORDER}; received {legendre_order}."
            )
        return legendre_order

    def first_table_number(self, name_or_id: str | int, legendre_order: int) -> int:
        """Return the first (P0) record number in ``mixf.cr`` for a mixture."""
        order = self._validate_legendre_order(legendre_order)
        mixture = self.get(name_or_id) if isinstance(name_or_id, str) else self.get_by_id(name_or_id)
        return 1 + (mixture.mixture_id - 1) * (order + 1)

    def table_numbers(self, name_or_id: str | int, legendre_order: int) -> tuple[int, ...]:
        """Return record numbers for P0 through PL in ``mixf.cr``."""
        first = self.first_table_number(name_or_id, legendre_order)
        order = self._validate_legendre_order(legendre_order)
        return tuple(range(first, first + order + 1))

    def dort_material_number(self, name_or_id: str | int, legendre_order: int) -> int:
        """Return the negative material reference written to local DORT ``9$``."""
        return -self.first_table_number(name_or_id, legendre_order)

    def expected_table_count(self, legendre_order: int) -> int:
        order = self._validate_legendre_order(legendre_order)
        return len(self) * (order + 1)

    def render_mix_input(self, legendre_order: int) -> str:
        """Render ``mix.inp`` for the supplied ``m_ia_oa.for`` program."""
        order = self._validate_legendre_order(legendre_order)
        self.validate()

        lines = [str(order), str(len(self))]
        for mixture in self._mixtures.values():
            mats = " ".join(str(c.mat_number) for c in mixture.components)
            dens = " ".join(f"{c.atom_density:.5E}" for c in mixture.components)
            lines.append(f"{len(mixture.components)} {mats}")
            lines.append(dens)
        return "\n".join(lines)

    def write_mix_input(self, filename: str | Path, legendre_order: int) -> Path:
        path = Path(filename)
        path.write_text(self.render_mix_input(legendre_order) + "\n", encoding="ascii")
        return path

    def validate_mix_file(
        self,
        filename: str | Path,
        legendre_order: int,
        *,
        values_per_table: int = DEFAULT_VALUES_PER_TABLE,
    ) -> MixtureFileValidation:
        """Validate record numbering and table lengths in a generated ``mixf.cr``.

        The supplied Fortran mixer writes each table as two formatted records:
        one header containing four identical sequential integers, followed by
        one record containing 47,740 values (217 groups x 220 columns).
        """
        order = self._validate_legendre_order(legendre_order)
        expected_tables = self.expected_table_count(order)
        path = Path(filename)
        errors: list[str] = []
        warnings: list[str] = []

        if not path.is_file():
            return MixtureFileValidation(
                valid=False,
                errors=(f"File not found: {path}",),
                warnings=(),
                table_count=0,
                expected_table_count=expected_tables,
                values_per_table=values_per_table,
            )

        lines = path.read_text(encoding="ascii", errors="strict").splitlines()
        if len(lines) % 2:
            errors.append(
                f"Expected an even number of records (header/data pairs); found {len(lines)}."
            )

        table_count = len(lines) // 2
        if table_count != expected_tables:
            errors.append(
                f"mixf.cr contains {table_count} tables; expected {expected_tables} "
                f"for {len(self)} mixtures at P{order}."
            )

        for zero_based in range(table_count):
            header_line = lines[2 * zero_based]
            data_line = lines[2 * zero_based + 1]
            expected_index = zero_based + 1

            try:
                header = [int(token) for token in header_line.split()]
            except ValueError:
                errors.append(f"Table {expected_index}: header is not integer data.")
                continue

            if header != [expected_index] * 4:
                errors.append(
                    f"Table {expected_index}: expected header "
                    f"'{expected_index} {expected_index} {expected_index} {expected_index}', "
                    f"found {header}."
                )

            values = data_line.split()
            if len(values) != values_per_table:
                errors.append(
                    f"Table {expected_index}: contains {len(values)} cross-section "
                    f"values; expected {values_per_table}."
                )
                continue

            # Check numeric parseability without retaining the large array.
            try:
                for token in values:
                    value = float(token.replace("D", "E").replace("d", "e"))
                    if not isfinite(value):
                        raise ValueError
            except ValueError:
                errors.append(
                    f"Table {expected_index}: contains a non-finite or non-numeric value."
                )

        return MixtureFileValidation(
            valid=not errors,
            errors=tuple(errors),
            warnings=tuple(warnings),
            table_count=table_count,
            expected_table_count=expected_tables,
            values_per_table=values_per_table,
        )

    def layout_text(self, legendre_order: int) -> str:
        order = self._validate_legendre_order(legendre_order)
        lines = [
            "ID  Mixture                  mixf.cr tables      9$ value",
            "----------------------------------------------------------",
        ]
        for mixture in self._mixtures.values():
            tables = self.table_numbers(mixture.mixture_id, order)
            table_text = str(tables[0]) if len(tables) == 1 else f"{tables[0]}..{tables[-1]}"
            lines.append(
                f"{mixture.mixture_id:2d}  {mixture.name[:24]:24s} "
                f"{table_text:17s} {self.dort_material_number(mixture.mixture_id, order):8d}"
            )
        return "\n".join(lines)

    def clear(self) -> None:
        self._mixtures.clear()

    def __contains__(self, name: str) -> bool:
        return name in self._mixtures

    def __getitem__(self, name: str) -> Mixture:
        return self.get(name)

    def __iter__(self) -> Iterator[Mixture]:
        return iter(self._mixtures.values())

    def __len__(self) -> int:
        return len(self._mixtures)

    def __repr__(self) -> str:
        content = ", ".join(
            f"{m.name}:{m.mixture_id}" for m in self._mixtures.values()
        )
        return f"MixtureRegistry({{{content}}})"
