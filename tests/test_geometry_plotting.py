"""Check displayed material boundaries and labels against final cell assignments."""

import csv
import tempfile
import unittest
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.collections import QuadMesh

from dort_input import DORTModel
from dort_input.plotting import (
    plot_material_region_union, plot_materials, plot_regions, save_material_plot,
    save_material_region_union_plot, save_region_plot, write_outline_csv,
)


def strip_model():
    model = DORTModel("strips")
    model.add_material("Air")
    model.add_material("Steel")
    model.mesh.r.add_segment(0, 4, step=1)
    model.mesh.z.add_segment(0, 3, step=1)
    model.set_background("Air")
    model.add_region("left", material="Steel", r=(0, 1), z=(0, 3))
    model.add_region("right", material="Steel", r=(3, 4), z=(0, 3))
    model.build()
    return model


def adjacent_region_model():
    model = DORTModel("adjacent regions")
    model.add_material("Air")
    model.add_material("Steel")
    model.mesh.r.add_segment(0, 3, step=1)
    model.mesh.z.add_segment(0, 2, step=1)
    model.set_background("Air")
    model.add_region("left", material="Steel", r=(0, 1), z=(0, 2))
    model.add_region("right", material="Steel", r=(1, 2), z=(0, 2))
    model.build()
    return model


class GeometryPlottingTest(unittest.TestCase):
    def test_long_material_name_wraps_inside_thin_region(self):
        model = DORTModel("thin region")
        model.add_material("Air")
        model.add_material("Carbon Steel")
        model.mesh.r.add_segment(0, 10, step=1)
        model.mesh.z.add_segment(0, 4, step=1)
        model.set_background("Air")
        model.add_region("vessel", material="Carbon Steel", r=(4, 5), z=(0, 4))
        model.build()
        fig, ax = plot_material_region_union(model)
        try:
            steel = next(label for label in ax.texts if "Carbon" in label.get_text())
            self.assertIn("\n", steel.get_text())
            box = steel.get_window_extent(fig.canvas.get_renderer())
            left = ax.transData.transform((4, 2))[0]
            right = ax.transData.transform((5, 2))[0]
            self.assertGreaterEqual(box.x0, left - 3)
            self.assertLessEqual(box.x1, right + 3)
        finally:
            plt.close(fig)

    def test_union_plot_and_three_outline_series(self):
        model = adjacent_region_model()
        fig, ax = plot_material_region_union(model)
        try:
            lines = [artist for artist in ax.collections
                     if isinstance(artist, LineCollection)]
            self.assertEqual(len(lines), 1)
            plotted = lines[0].get_segments()
            self.assertTrue(any(np.allclose(s, [(1, 0), (1, 2)]) for s in plotted))
            self.assertTrue(any(np.allclose(s, [(2, 0), (2, 2)]) for s in plotted))
            self.assertEqual(sorted(t.get_text() for t in ax.texts),
                             ["Air", "Steel", "Steel"])
            self.assertIsNotNone(ax.get_legend())

            with tempfile.TemporaryDirectory() as directory:
                csv_path = Path(directory) / "outlines.csv"
                self.assertEqual(write_outline_csv(model, csv_path), csv_path)
                with csv_path.open(newline="", encoding="utf-8") as stream:
                    rows = list(csv.DictReader(stream))

                def segments(prefix):
                    r_key, z_key = f"{prefix}_R", f"{prefix}_Z"
                    result, pair = [], []
                    for row in rows:
                        if row[r_key] and row[z_key]:
                            pair.append((float(row[r_key]), float(row[z_key])))
                        else:
                            if pair:
                                self.assertEqual(len(pair), 2)
                                result.append(pair)
                                pair = []
                    self.assertFalse(pair)
                    return result

                material, region, union = (segments(name) for name in
                                            ("Material", "Region", "Union"))
                shared_edge = [(1.0, 0.0), (1.0, 2.0)]
                self.assertNotIn(shared_edge, material)
                self.assertIn(shared_edge, region)
                self.assertIn(shared_edge, union)
                self.assertEqual(len(union), len(plotted))
                for csv_segment, plot_segment in zip(union, plotted):
                    np.testing.assert_allclose(csv_segment, plot_segment)
                self.assertTrue(any(not row["Material_R"] and row["Union_R"]
                                    for row in rows))

                image_path = Path(directory) / "union.png"
                save_material_region_union_plot(model, image_path)
                self.assertGreater(image_path.stat().st_size, 0)
        finally:
            plt.close(fig)

    def test_material_edges_and_one_id_per_visible_area(self):
        model = strip_model()
        fig, ax = plot_materials(
            model, r_extent=(0.25, 3.75), z_extent=(0.25, 2.75),
            show_material_boundaries=True, show_material_ids=True,
        )
        try:
            self.assertEqual(ax.get_xlim(), (0.25, 3.75))
            self.assertEqual(ax.get_ylim(), (0.25, 2.75))
            lines = [artist for artist in ax.collections
                     if isinstance(artist, LineCollection)]
            self.assertEqual(len(lines), 1)
            segments = lines[0].get_segments()
            self.assertEqual(len(segments), 6)  # four outer sides, two interfaces
            self.assertTrue(any(np.allclose(segment, [(1, 0), (1, 3)])
                                for segment in segments))
            self.assertTrue(any(np.allclose(segment, [(3, 0), (3, 3)])
                                for segment in segments))
            labels = sorted((t.get_text(), *t.get_position()) for t in ax.texts)
            self.assertEqual([entry[0] for entry in labels], ["1", "2", "2"])
            np.testing.assert_allclose(
                sorted(t.get_position() for t in ax.texts),
                [(0.625, 1.5), (2, 1.5), (3.375, 1.5)],
            )
        finally:
            plt.close(fig)

    def test_centroid_in_a_hole_moves_label_inside_its_material(self):
        model = DORTModel("hole")
        model.add_material("outer")
        model.add_material("inner")
        model.mesh.r.add_segment(0, 3, step=1)
        model.mesh.z.add_segment(0, 3, step=1)
        model.set_background("outer")
        model.add_region("hole", material="inner", r=(1, 2), z=(1, 2))
        model.build()
        fig, ax = plot_materials(model, show_material_ids=True)
        try:
            self.assertEqual(len(ax.texts), 2)
            for label in ax.texts:
                r, z = label.get_position()
                i = int(np.searchsorted(model.mesh.r.edges, r, side="right") - 1)
                j = int(np.searchsorted(model.mesh.z.edges, z, side="right") - 1)
                self.assertEqual(int(label.get_text()), model.material_id_map[j, i])
        finally:
            plt.close(fig)

    def test_region_extent_save_helpers_and_validation(self):
        model = strip_model()
        window = dict(r_extent=(1.25, 2.75), z_extent=(0.4, 2.6))
        fig, ax = plot_regions(model, **window)
        try:
            self.assertEqual(ax.get_xlim(), window["r_extent"])
            self.assertEqual(ax.get_ylim(), window["z_extent"])
        finally:
            plt.close(fig)
        fig, ax = plot_materials(model, show_material_ids=True, **window)
        try:
            self.assertEqual([label.get_text() for label in ax.texts], ["1"])
        finally:
            plt.close(fig)

        for bad in ((2, 1), (0, np.inf), (0, 1, 2)):
            with self.subTest(extent=bad):
                with self.assertRaises(ValueError):
                    plot_materials(model, r_extent=bad)
                with self.assertRaises(ValueError):
                    plot_regions(model, z_extent=bad)

        with tempfile.TemporaryDirectory() as directory:
            materials = Path(directory) / "materials.png"
            regions = Path(directory) / "regions.png"
            save_material_plot(
                model, materials, **window,
                show_material_boundaries=True, show_material_ids=True,
            )
            save_region_plot(model, regions, **window)
            self.assertGreater(materials.stat().st_size, 0)
            self.assertGreater(regions.stat().st_size, 0)

    def test_outline_and_id_name_legend(self):
        model = strip_model()
        fig, ax = plot_materials(model, color_fill=False)
        try:
            self.assertEqual(ax.get_aspect(), "auto")
            self.assertFalse(any(isinstance(item, QuadMesh) for item in ax.collections))
            self.assertTrue(any(isinstance(item, LineCollection) for item in ax.collections))
            self.assertEqual([item.get_text() for item in ax.get_legend().get_texts()],
                             ["1: Air", "2: Steel"])
            self.assertEqual(sorted(item.get_text() for item in ax.texts if item.get_text()),
                             ["1", "2", "2"])
        finally:
            plt.close(fig)

    def test_background_priority_is_base_level_and_unfilled_is_none(self):
        model = strip_model()
        self.assertEqual(model.cell_assignment(1, 2)["priority"], 0)
        self.assertEqual(model.cell_assignment(1, 2)["region"], "background")
        other = DORTModel("unfilled")
        other.add_material("A")
        other.mesh.r.add_segment(0, 2, step=1)
        other.mesh.z.add_segment(0, 1, step=1)
        other.add_region("left", material="A", r=(0, 1), z=(0, 1), priority=12)
        other.build(allow_unfilled=True)
        self.assertEqual(other.cell_assignment(0, 0)["priority"], 12)
        self.assertIsNone(other.cell_assignment(0, 1)["priority"])

    def test_dense_material_ids_do_not_overlap(self):
        model = DORTModel("dense")
        for i in range(12):
            model.add_material(f"Material {i + 1}")
        model.mesh.r.add_segment(0, 12, step=1)
        model.mesh.z.add_segment(0, 10, step=1)
        model.set_background("Material 1")
        for i in range(1, 12):
            model.add_region(
                f"strip {i}", material=f"Material {i + 1}",
                r=(i, i + 1), z=(0, 10),
            )
        model.build()
        fig, ax = plot_materials(model, show_material_ids=True, figsize=(4, 3))
        try:
            renderer = fig.canvas.get_renderer()
            labels = [item for item in ax.texts if item.get_text()]
            self.assertEqual(len(labels), 12)
            for i, first in enumerate(labels):
                for second in labels[i + 1:]:
                    self.assertFalse(
                        first.get_window_extent(renderer).padded(2).overlaps(
                            second.get_window_extent(renderer).padded(2)
                        )
                    )
        finally:
            plt.close(fig)


if __name__ == "__main__":
    unittest.main()
