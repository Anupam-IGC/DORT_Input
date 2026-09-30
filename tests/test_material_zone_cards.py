"""Keep 8$$, 9$$ and the 62$$ zone count consistent with the chosen policy."""

import unittest

import numpy as np

from dort_input import DORTModel, DORTWriter


def repeated_material_model():
    model = DORTModel("repeated")
    for name, mat in (("A", 1), ("B", 2), ("C", 3)):
        model.add_mixture(name, {mat: 0.01}, legendre_order=5)
    model.mesh.r.add_segment(0, 5, step=1)
    model.mesh.z.add_segment(0, 1, step=1)
    model.set_background("A")
    model.add_region("B-zone", material="B", r=(1, 2), z=(0, 1))
    model.add_region("C-zone", material="C", r=(2, 3), z=(0, 1))
    model.add_region("second-A-zone", material="A", r=(3, 4), z=(0, 1))
    model.build()
    return model


class MaterialZoneCardsTest(unittest.TestCase):
    def test_default_has_one_9_entry_per_used_mixture(self):
        model = repeated_material_model()
        writer = DORTWriter(model)
        self.assertEqual(writer.zone_policy, "material")
        self.assertEqual(writer.izm, 3)
        self.assertEqual(writer.array9(), "9$$ -1 -7 -13 t")
        np.testing.assert_array_equal(writer.zone_map, model.material_id_map)
        np.testing.assert_array_equal(writer.ijzn_stream(), [1, 2, 3, 1, 1])
        run = writer.create_run_control(
            "eigenvalue_first", energy_groups=217,
            quadrature_directions=160, neutron_groups=175,
        )
        self.assertEqual(run.controls62["IZM"], 3)
        self.assertEqual(run.controls62["MTP"], 3)
        self.assertEqual(run.controls62["MTM"], 3)
        self.assertEqual(int(run.array62().split()[3]), 3)

    def test_explicit_region_policy_repeats_only_when_requested(self):
        writer = DORTWriter(repeated_material_model(), zone_policy="region")
        self.assertEqual(writer.izm, 4)
        self.assertEqual(writer.array9(), "9$$ -1 -1 -7 -13 t")
        self.assertEqual(writer.create_run_control(
            "eigenvalue_first", energy_groups=217, quadrature_directions=160,
        ).controls62["IZM"], 4)


if __name__ == "__main__":
    unittest.main()
