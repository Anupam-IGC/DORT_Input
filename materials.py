"""Material definitions and registry utilities for DORT input preparation.

The module manages readable material names and positive internal material IDs.
It deliberately contains no geometry or DORT/FIDO writing logic.

Notes
-----
``Material.dort_id`` is an internal project identifier.  A DORT/GIP
cross-section library may use a different, including negative, material
number.  Such external numbers are supplied separately to ``DORTWriter``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator


@dataclass(frozen=True)
class Material:
    """Represent one physical material registered in a model.
    
    Parameters
    ----------
    name : str
        Human-readable material name, for example ``"SS316"`` or ``"Sodium"``.
    dort_id : int
        Positive internal identifier used in the built material map.
    description : str, optional
        Free-text description of the material.
    
    Raises
    ------
    TypeError
        If ``dort_id`` is not an integer.
    ValueError
        If ``name`` is empty or ``dort_id`` is not positive.
    
    Notes
    -----
    The dataclass is frozen so a registered material cannot be modified
    accidentally.
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
    """Manage a collection of uniquely named materials and internal IDs.
    
    Materials are stored in insertion order. Names are case-sensitive.
    
    Examples
    --------
    >>> from materials import MaterialRegistry
    >>> materials = MaterialRegistry()
    >>> materials.add("Sodium")
    Material(name='Sodium', dort_id=1, description='')
    >>> materials.add("B4C", dort_id=10)
    Material(name='B4C', dort_id=10, description='')
    """

    def __init__(self) -> None:
        self._materials: dict[str, Material] = {}

    def _next_available_id(self) -> int:
        """Return the smallest unused positive internal material ID.
        
        Returns
        -------
        int
            Smallest positive integer not currently assigned.
        """
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
        """Create and register a material.
        
        Parameters
        ----------
        name : str
            Unique material name.
        dort_id : int, optional
            Positive internal ID. If omitted, the smallest available positive integer
            is selected automatically.
        description : str, optional
            Free-text material description.
        
        Returns
        -------
        Material
            Newly registered immutable material object.
        
        Raises
        ------
        TypeError
            If ``dort_id`` is provided but is not an integer.
        ValueError
            If the name is empty/already registered, or the requested ID is
            non-positive/already used.
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
        """Replace the definition of an existing material.
        
        Parameters
        ----------
        name : str
            Name of the registered material to replace.
        dort_id : int, optional
            New positive internal ID. ``None`` preserves the existing ID.
        description : str, optional
            New description. ``None`` preserves the existing description.
        
        Returns
        -------
        Material
            Replacement immutable material object.
        
        Raises
        ------
        KeyError
            If ``name`` is not registered.
        TypeError
            If the resulting ID is not an integer.
        ValueError
            If the resulting ID is non-positive or already assigned to another
            material.
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
        """Remove a material by name.
        
        Parameters
        ----------
        name : str
            Registered material name.
        
        Returns
        -------
        Material
            Removed material.
        
        Raises
        ------
        KeyError
            If the material is not registered.
        """
        try:
            return self._materials.pop(name)
        except KeyError as exc:
            raise KeyError(f"Material {name!r} is not registered.") from exc

    def get(self, name: str) -> Material:
        """Return a registered material by name.
        
        Parameters
        ----------
        name : str
            Registered material name.
        
        Returns
        -------
        Material
            Matching material.
        
        Raises
        ------
        KeyError
            If the material is not registered.
        """
        try:
            return self._materials[name]
        except KeyError as exc:
            raise KeyError(f"Material {name!r} is not registered.") from exc

    def get_by_id(self, dort_id: int) -> Material:
        """Return the material assigned to an internal ID.
        
        Parameters
        ----------
        dort_id : int
            Internal material identifier.
        
        Returns
        -------
        Material
            Material carrying the requested ID.
        
        Raises
        ------
        KeyError
            If no material uses the ID.
        """
        for material in self._materials.values():
            if material.dort_id == dort_id:
                return material

        raise KeyError(f"No material is registered with DORT ID {dort_id}.")

    def get_id(self, name: str) -> int:
        """Return the internal ID associated with a material name.
        
        Parameters
        ----------
        name : str
            Registered material name.
        
        Returns
        -------
        int
            Internal material ID.
        
        Raises
        ------
        KeyError
            If the material is not registered.
        """
        return self.get(name).dort_id

    def has_name(self, name: str) -> bool:
        """Test whether a material name is registered.
        
        Parameters
        ----------
        name : str
            Material name.
        
        Returns
        -------
        bool
            ``True`` when the name exists.
        """
        return name in self._materials

    def has_id(self, dort_id: int) -> bool:
        """Test whether an internal material ID is already in use.
        
        Parameters
        ----------
        dort_id : int
            Candidate internal ID.
        
        Returns
        -------
        bool
            ``True`` when the ID is assigned.
        """
        return any(
            material.dort_id == dort_id
            for material in self._materials.values()
        )

    @property
    def names(self) -> tuple[str, ...]:
        """Return registered material names in insertion order.
        
        Returns
        -------
        tuple of str
            Material names.
        """
        return tuple(self._materials.keys())

    @property
    def ids(self) -> tuple[int, ...]:
        """Return internal material IDs in insertion order.
        
        Returns
        -------
        tuple of int
            Material IDs.
        """
        return tuple(
            material.dort_id
            for material in self._materials.values()
        )

    @property
    def materials(self) -> tuple[Material, ...]:
        """Return registered material objects in insertion order.
        
        Returns
        -------
        tuple of Material
            Registered materials.
        """
        return tuple(self._materials.values())

    def validate(self) -> None:
        """Validate the complete registry.
        
        Returns
        -------
        None
        
        Raises
        ------
        ValueError
            If duplicate names, duplicate IDs, or a non-positive ID is detected.
        
        Notes
        -----
        Registration methods already enforce these constraints; this method provides
        a defensive whole-registry check before model building.
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
        """Remove all registered materials.
        
        Returns
        -------
        None
        """
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
