"""
materials.py
============

Material definitions and registry utilities for the DORT preparation API.

This module deliberately does not contain any geometry or DORT input-writing
logic. Its job is only to manage material objects, names, and numerical IDs.

Example
-------
from materials import MaterialRegistry

materials = MaterialRegistry()

materials.add("Sodium")
materials.add("SS316")
materials.add("B4C", dort_id=10)

print(materials["SS316"])
print(materials.get_id("B4C"))
print(materials.names)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator


@dataclass(frozen=True)
class Material:
    """
    Representation of one physical material.

    Parameters
    ----------
    name
        Human-readable material name, e.g. ``"SS316"`` or ``"Sodium"``.
    dort_id
        Positive integer ID used when exporting to DORT.
    description
        Optional explanatory text.

    Notes
    -----
    The dataclass is frozen so that a material already registered in a model
    cannot be modified accidentally. If a definition needs to change, replace
    it explicitly through the registry.
    """

    name: str
    dort_id: int
    description: str = ""

    def __post_init__(self) -> None:
        name = self.name.strip()

        if not name:
            raise ValueError("Material name cannot be empty.")

        if isinstance(self.dort_id, bool) or not isinstance(self.dort_id, int):
            raise TypeError("Material dort_id must be an integer.")

        if self.dort_id <= 0:
            raise ValueError("Material dort_id must be a positive integer.")

        # Preserve a cleaned name even though the dataclass is frozen.
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "description", self.description.strip())

    def __repr__(self) -> str:
        return (
            f"Material(name={self.name!r}, "
            f"dort_id={self.dort_id}, "
            f"description={self.description!r})"
        )


class MaterialRegistry:
    """
    Collection that manages materials and unique DORT material IDs.

    Materials are stored by name. Names are matched case-sensitively by default;
    this avoids silently treating distinct user labels as the same material.

    Examples
    --------
    >>> registry = MaterialRegistry()
    >>> registry.add("Sodium")
    Material(name='Sodium', dort_id=1, description='')
    >>> registry.add("SS316")
    Material(name='SS316', dort_id=2, description='')
    >>> registry.add("B4C", dort_id=10)
    Material(name='B4C', dort_id=10, description='')
    """

    def __init__(self) -> None:
        self._materials: dict[str, Material] = {}

    def _next_available_id(self) -> int:
        """Return the smallest positive integer not already assigned."""
        used = {material.dort_id for material in self._materials.values()}

        candidate = 1
        while candidate in used:
            candidate += 1

        return candidate

    def add(
        self,
        name: str,
        *,
        dort_id: int | None = None,
        description: str = "",
    ) -> Material:
        """
        Add and return a new material.

        If ``dort_id`` is omitted, the smallest unused positive integer is
        assigned automatically.

        Raises
        ------
        ValueError
            If the name already exists or the requested ID is already used.
        """
        clean_name = str(name).strip()

        if not clean_name:
            raise ValueError("Material name cannot be empty.")

        if clean_name in self._materials:
            existing = self._materials[clean_name]
            raise ValueError(
                f"Material {clean_name!r} already exists "
                f"with DORT ID {existing.dort_id}."
            )

        if dort_id is None:
            dort_id = self._next_available_id()
        else:
            if isinstance(dort_id, bool) or not isinstance(dort_id, int):
                raise TypeError("dort_id must be an integer or None.")

            if dort_id <= 0:
                raise ValueError("dort_id must be a positive integer.")

            if self.has_id(dort_id):
                other = self.get_by_id(dort_id)
                raise ValueError(
                    f"DORT ID {dort_id} is already assigned to "
                    f"material {other.name!r}."
                )

        material = Material(
            name=clean_name,
            dort_id=dort_id,
            description=description,
        )

        self._materials[clean_name] = material
        return material

    def replace(
        self,
        name: str,
        *,
        dort_id: int | None = None,
        description: str | None = None,
    ) -> Material:
        """
        Replace an existing material definition.

        Any argument left as ``None`` keeps its current value.
        """
        if name not in self._materials:
            raise KeyError(f"Material {name!r} is not registered.")

        old = self._materials[name]

        new_id = old.dort_id if dort_id is None else dort_id
        new_description = (
            old.description if description is None else description
        )

        if isinstance(new_id, bool) or not isinstance(new_id, int):
            raise TypeError("dort_id must be an integer.")

        if new_id <= 0:
            raise ValueError("dort_id must be a positive integer.")

        for other_name, other in self._materials.items():
            if other_name != name and other.dort_id == new_id:
                raise ValueError(
                    f"DORT ID {new_id} is already assigned to "
                    f"material {other_name!r}."
                )

        updated = Material(
            name=name,
            dort_id=new_id,
            description=new_description,
        )

        self._materials[name] = updated
        return updated

    def remove(self, name: str) -> Material:
        """Remove and return a material."""
        try:
            return self._materials.pop(name)
        except KeyError as exc:
            raise KeyError(f"Material {name!r} is not registered.") from exc

    def get(self, name: str) -> Material:
        """Return a material by name."""
        try:
            return self._materials[name]
        except KeyError as exc:
            raise KeyError(f"Material {name!r} is not registered.") from exc

    def get_by_id(self, dort_id: int) -> Material:
        """Return the material assigned to a DORT ID."""
        for material in self._materials.values():
            if material.dort_id == dort_id:
                return material

        raise KeyError(f"No material is registered with DORT ID {dort_id}.")

    def get_id(self, name: str) -> int:
        """Return the DORT ID associated with a material name."""
        return self.get(name).dort_id

    def has_name(self, name: str) -> bool:
        """Return whether a material name is registered."""
        return name in self._materials

    def has_id(self, dort_id: int) -> bool:
        """Return whether a DORT material ID is already in use."""
        return any(
            material.dort_id == dort_id
            for material in self._materials.values()
        )

    @property
    def names(self) -> tuple[str, ...]:
        """Registered material names in insertion order."""
        return tuple(self._materials.keys())

    @property
    def ids(self) -> tuple[int, ...]:
        """Registered DORT IDs in insertion order."""
        return tuple(
            material.dort_id
            for material in self._materials.values()
        )

    @property
    def materials(self) -> tuple[Material, ...]:
        """Registered Material objects in insertion order."""
        return tuple(self._materials.values())

    def validate(self) -> None:
        """
        Validate all registered material definitions.

        This is mostly defensive because ``add`` and ``replace`` already
        enforce the same constraints.
        """
        names = list(self._materials.keys())
        ids = [material.dort_id for material in self._materials.values()]

        if len(names) != len(set(names)):
            raise ValueError("Duplicate material names detected.")

        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate DORT material IDs detected.")

        for material in self._materials.values():
            if material.dort_id <= 0:
                raise ValueError(
                    f"Material {material.name!r} has invalid "
                    f"DORT ID {material.dort_id}."
                )

    def clear(self) -> None:
        """Remove all registered materials."""
        self._materials.clear()

    def __contains__(self, name: str) -> bool:
        return self.has_name(name)

    def __getitem__(self, name: str) -> Material:
        return self.get(name)

    def __iter__(self) -> Iterator[Material]:
        return iter(self._materials.values())

    def __len__(self) -> int:
        return len(self._materials)

    def __repr__(self) -> str:
        content = ", ".join(
            f"{material.name}:{material.dort_id}"
            for material in self._materials.values()
        )

        return f"MaterialRegistry({{{content}}})"


if __name__ == "__main__":
    # Small demonstration / smoke test.
    materials = MaterialRegistry()

    materials.add(
        "Sodium",
        description="Primary/background coolant",
    )
    materials.add(
        "SS316",
        description="Stainless-steel shielding material",
    )
    materials.add(
        "B4C",
        dort_id=10,
        description="Boron-carbide shielding material",
    )

    # ID 3 is still unused, so automatic numbering should choose it.
    materials.add("Air")

    materials.validate()

    print(materials)
    print()
    print("Names :", materials.names)
    print("IDs   :", materials.ids)
    print()
    print("SS316      :", materials["SS316"])
    print("B4C ID     :", materials.get_id("B4C"))
    print("Material 10:", materials.get_by_id(10))
