"""Independent sequential-unformatted fixtures for DORT VARFLM parsing."""

import csv
from pathlib import Path
import struct

import numpy as np
import pytest

from dort_input import (DortFluxFormatError, DortFluxReader, load_group_factors,
                        write_rz_csv)


def make_varflm(path: Path, *, endian: str = "<", marker_bytes: int = 4,
                real_bytes: int = 4, variable_mesh: bool = True) -> None:
    marker = struct.Struct(endian + ("i" if marker_bytes == 4 else "q"))
    i4 = np.dtype(endian + "i4")
    real = np.dtype(endian + f"f{real_bytes}")
    counts = [2, 3] if variable_mesh else [3]
    row_sets = [1, 2, 1] if variable_mesh else [1, 1, 1]
    radii = ([0, 1, 4], [0, 1, 2, 4]) if variable_mesh else ([0, 1, 2, 4],)
    moments = [2, 1, 3]
    controls = [3, 2, 3, 3, 3, 2, len(counts), sum(counts), len(counts), 11]
    controls += [0] * 15
    values = [0, 10, 20, 30]
    for edges in radii:
        values += list(edges)
    values += [1e7, 1e4, 1e3]  # top energy of each group
    values += [1, 100, 1.1, 0, 1.05, 1000]  # EMIN, ENEUT, EV, DEVDK, EFFK, POWER
    values += [0] * 13

    def write_record(file, payload: bytes) -> None:
        file.write(marker.pack(len(payload)))
        file.write(payload)
        file.write(marker.pack(len(payload)))

    with path.open("wb") as file:
        write_record(file, b"VARFLM".ljust(28, b" "))
        write_record(file, b"test case".ljust(136, b" "))
        write_record(file, np.asarray(controls, dtype=i4).tobytes())
        write_record(file, np.asarray(moments + counts + row_sets, dtype=i4).tobytes())
        write_record(file, np.asarray(values, dtype=real).tobytes())
        for g in range(3):
            for j, s in enumerate(row_sets):
                n = counts[s - 1]
                scalar = [100 * (g + 1) + 10 * (j + 1) + i + 1 for i in range(n)]
                data = scalar + [9999] * (n * (moments[g] - 1))
                write_record(file, np.asarray(data, dtype=real).tobytes())
            write_record(file, np.full(2 * (3 + counts[-1]), -5, dtype=real).tobytes())


@pytest.mark.parametrize("endian,marker_bytes,real_bytes", [
    ("<", 4, 4), (">", 4, 4), ("<", 8, 4), (">", 8, 8),
])
def test_read_variable_mesh_and_responses(tmp_path, endian, marker_bytes, real_bytes):
    path = tmp_path / "dortflux.bin"
    make_varflm(path, endian=endian, marker_bytes=marker_bytes,
                real_bytes=real_bytes)
    reader = DortFluxReader(path)
    m = reader.metadata
    assert m.shape == (3, 3, 3)
    assert (m.neutron_groups, m.photon_groups) == (2, 1)
    assert (m.byte_order, m.record_marker_bytes, m.real_bytes) == (
        endian, marker_bytes, real_bytes)
    assert m.power_watts == 1000
    assert m.effective_multiplication_factor == pytest.approx(1.05)
    assert not m.regular_radial_mesh
    np.testing.assert_array_equal(m.radial_edges(1), [0, 1, 2, 4])
    flux = reader.read_scalar_flux(groups=[2, 0])
    np.testing.assert_array_equal(flux[:, 1, :], [[321, 322, 323], [121, 122, 123]])
    assert np.isnan(flux[0, 0, 2])
    np.testing.assert_array_equal(reader.read_scalar_flux(slice(1, 2))[0, 2, :2],
                                  [231, 232])
    sums = reader.integrated_flux()
    assert sums.neutron[1, 0] == pytest.approx(121 + 221)
    assert sums.photon[1, 0] == pytest.approx(321)
    assert sums.total[1, 0] == pytest.approx(121 + 221 + 321)
    assert np.isnan(sums.total[0, 2])
    dose = reader.dose_rate([0.1, 0.2], [0.3], scale=2.0)
    assert dose.neutron[0, 0] == pytest.approx(2 * (111 * .1 + 211 * .2))
    assert dose.photon[0, 0] == pytest.approx(2 * 311 * .3)
    assert dose.total[0, 0] == pytest.approx(dose.neutron[0, 0] + dose.photon[0, 0])
    np.testing.assert_allclose(reader.weighted_sums([0, 1, 0])[1, :], [221, 222, 223])


def test_regular_mesh_plot_and_group_factors(tmp_path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    path = tmp_path / "flux.bin"
    make_varflm(path, variable_mesh=False)
    reader = DortFluxReader(path)
    assert reader.metadata.regular_radial_mesh
    factors = tmp_path / "factors.txt"
    factors.write_text("0.1\n0.2\n", encoding="utf-8")
    np.testing.assert_allclose(load_group_factors(factors, 2), [0.1, 0.2])
    field = reader.integrated_flux().total
    fig, ax = reader.plot_field(field, label="Flux", log=True)
    assert ax.get_xlabel() == "R"
    assert len(fig.axes) == 2  # field and one colorbar
    plt.close(fig)
    with pytest.raises(ValueError, match="Expected exactly"):
        load_group_factors(factors, 3)


def test_variable_mesh_plot(tmp_path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    path = tmp_path / "flux.bin"
    make_varflm(path)
    reader = DortFluxReader(path)
    fig, ax = reader.plot_field(reader.integrated_flux().total, log=True)
    assert len(ax.collections) == 1
    plt.close(fig)


def test_rz_csv_uses_each_axial_rows_active_radial_cells(tmp_path):
    path = tmp_path / "flux.bin"
    make_varflm(path)
    reader = DortFluxReader(path)
    field = reader.read_scalar_flux(groups=[0])[0]
    csv_path = tmp_path / "group_1.csv"
    assert reader.write_rz_csv(field, csv_path) == csv_path
    with csv_path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.reader(stream))
    assert rows[0] == ["R", "Z", "Value"]
    assert np.asarray(rows[1:], dtype=float).tolist() == [
        [0.5, 5, 111], [2.5, 5, 112],
        [0.5, 15, 121], [1.5, 15, 122], [3, 15, 123],
        [0.5, 25, 131], [2.5, 25, 132],
    ]
    assert write_rz_csv(reader.metadata, field, tmp_path / "again.csv").exists()
    with pytest.raises(ValueError, match="shape"):
        reader.write_rz_csv(field[:, :2], tmp_path / "wrong.csv")


def test_rejects_corrupt_records_and_invalid_coefficients(tmp_path):
    path = tmp_path / "flux.bin"
    make_varflm(path)
    reader = DortFluxReader(path)
    with pytest.raises(ValueError, match="Expected 2 neutron"):
        reader.dose_rate([1], [1])
    with pytest.raises(ValueError, match="zero-based"):
        reader.read_scalar_flux([-1])
    with pytest.raises(ValueError, match="Repeated"):
        reader.read_scalar_flux([0, 0])
    with pytest.raises(ValueError, match="3 groups"):
        reader.weighted_sums([1, 2])
    data = path.read_bytes()
    path.write_bytes(data[:-5])
    with pytest.raises(DortFluxFormatError, match="truncated"):
        reader.integrated_flux()
    path.write_bytes(data[:-1] + b"X")
    with pytest.raises(DortFluxFormatError, match="trailer"):
        reader.integrated_flux()


def test_rejects_invalid_header(tmp_path):
    path = tmp_path / "not-varflm.bin"
    path.write_bytes(b"not a Fortran record")
    with pytest.raises(DortFluxFormatError, match="Not a supported VARFLM"):
        DortFluxReader(path)
