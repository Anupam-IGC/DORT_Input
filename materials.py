"""Physical material definitions for DORT input preparation.

Materials are user-facing geometry labels and are numbered naturally as
1, 2, 3, ... .  In the local DORT workflow, their microscopic composition is
stored separately in :mod:`mixtures`; the external mixer creates ``mixf.cr``.

``legendre_order`` remains part of the material definition because it controls
both DORT ``ISCTM`` and how many consecutive cross-section tables the external
mixer writes for each physical mixture.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator


@dataclass(frozen=True)
class Material:
    """One physical material used by the geometry.

    Parameters
    ----------
    name
        Human-readable material name.
    material_id
        Natural-number material/mixture sequence ID.
    legendre_order
        Scattering expansion order L for P_L. All materials in one model must
        use the same order.
    description
        Optional explanatory text.
    """

    name: str
    material_id: int
    legendre_order: int = 0
    description: str = ""

    def __post_init__(self) -> None:
        name = str(self.name).strip()
        if not name:
            raise ValueError("Material name cannot be empty.")
        if isinstance(self.material_id, bool) or not isinstance(self.material_id, int):
            raise TypeError("material_id must be an integer.")
        if self.material_id <= 0:
            raise ValueError("material_id must be a positive integer.")
        if isinstance(self.legendre_order, bool) or not isinstance(self.legendre_order, int):
            raise TypeError("legendre_order must be an integer.")
        if self.legendre_order < 0:
            raise ValueError("legendre_order cannot be negative.")

        object.__setattr__(self, "name", name)
        object.__setattr__(self, "description", str(self.description).strip())

    @property
    def dort_id(self) -> int:
        """Legacy alias for the natural-number ``material_id``."""
        return self.material_id

    @property
    def n_legendre_tables(self) -> int:
        """Number of external cross-section tables P0 through PL."""
        return self.legendre_order + 1

    def __repr__(self) -> str:
        return (
            f"Material(name={self.name!r}, material_id={self.material_id}, "
            f"legendre_order={self.legendre_order}, "
            f"description={self.description!r})"
        )


class MaterialRegistry:
    """Ordered collection of materials with IDs 1, 2, 3, ... ."""

    def __init__(self) -> None:
        self._materials: dict[str, Material] = {}

    def _next_id(self) -> int:
        return len(self._materials) + 1

    def add(
        self,
        name: str,
        *,
        material_id: int | None = None,
        dort_id: int | None = None,
        legendre_order: int = 0,
        description: str = "",
    ) -> Material:
        name = str(name).strip()
        if not name:
            raise ValueError("Material name cannot be empty.")
        if name in self._materials:
            raise ValueError(f"Material {name!r} is already registered.")
        if material_id is not None and dort_id is not None:
            raise ValueError("Specify only material_id; dort_id is a legacy alias.")

        requested = material_id if material_id is not None else dort_id
        expected = self._next_id()
        if requested is None:
            requested = expected
        elif isinstance(requested, bool) or not isinstance(requested, int):
            raise TypeError("material_id must be an integer or None.")
        elif requested != expected:
            raise ValueError(
                "Materials must follow the natural sequence 1, 2, 3, ...; "
                f"the next material_id must be {expected}, not {requested}."
            )

        material = Material(
            name=name,
            material_id=requested,
            legendre_order=legendre_order,
            description=description,
        )
        self._materials[name] = material
        return material

    def replace(
        self,
        name: str,
        *,
        material_id: int | None = None,
        dort_id: int | None = None,
        legendre_order: int | None = None,
        description: str | None = None,
    ) -> Material:
        if name not in self._materials:
            raise KeyError(f"Material {name!r} is not registered.")
        if material_id is not None and dort_id is not None:
            raise ValueError("Specify only material_id; dort_id is a legacy alias.")

        old = self._materials[name]
        requested = material_id if material_id is not None else dort_id
        if requested is not None and requested != old.material_id:
            raise ValueError("Material IDs are fixed by the natural registration sequence.")

        updated = Material(
            name=old.name,
            material_id=old.material_id,
            legendre_order=old.legendre_order if legendre_order is None else legendre_order,
            description=old.description if description is None else description,
        )
        self._materials[name] = updated
        return updated

    def remove(self, name: str) -> Material:
        if name not in self._materials:
            raise KeyError(f"Material {name!r} is not registered.")
        material = self._materials[name]
        if material.material_id != len(self._materials):
            raise ValueError(
                "Only the last material can be removed because IDs must remain 1, 2, 3, ...."
            )
        return self._materials.pop(name)

    def get(self, name: str) -> Material:
        try:
            return self._materials[name]
        except KeyError as exc:
            raise KeyError(f"Material {name!r} is not registered.") from exc

    def get_by_id(self, material_id: int) -> Material:
        for material in self._materials.values():
            if material.material_id == material_id:
                return material
        raise KeyError(f"No material is registered with material_id {material_id}.")

    def get_id(self, name: str) -> int:
        return self.get(name).material_id

    def has_name(self, name: str) -> bool:
        return name in self._materials

    def has_id(self, material_id: int) -> bool:
        return any(m.material_id == material_id for m in self._materials.values())

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(self._materials.keys())

    @property
    def ids(self) -> tuple[int, ...]:
        return tuple(m.material_id for m in self._materials.values())

    @property
    def materials(self) -> tuple[Material, ...]:
        return tuple(self._materials.values())

    @property
    def legendre_order(self) -> int:
        """Return the common P_L order used by the model."""
        if not self._materials:
            return 0
        orders = {m.legendre_order for m in self._materials.values()}
        if len(orders) != 1:
            raise ValueError(
                "All materials must use one common legendre_order; "
                f"found {sorted(orders)}."
            )
        return next(iter(orders))

    def validate(self) -> None:
        ids = list(self.ids)
        expected = list(range(1, len(ids) + 1))
        if ids != expected:
            raise ValueError(
                f"Material IDs must be the natural sequence {expected}; found {ids}."
            )
        _ = self.legendre_order

    def clear(self) -> None:
        self._materials.clear()

    def __contains__(self, name: str) -> bool:
        return name in self._materials

    def __getitem__(self, name: str) -> Material:
        return self.get(name)

    def __iter__(self) -> Iterator[Material]:
        return iter(self._materials.values())

    def __len__(self) -> int:
        return len(self._materials)

    def __repr__(self) -> str:
        content = ", ".join(
            f"{m.name}:{m.material_id}(P{m.legendre_order})"
            for m in self._materials.values()
        )
        return f"MaterialRegistry({{{content}}})"


if __name__ == "__main__":
    materials = MaterialRegistry()
    materials.add("Mixture-1", legendre_order=5)
    materials.add("Mixture-2", legendre_order=5)
    materials.add("Mixture-3", legendre_order=5)
    materials.validate()
    print(materials)
