"""Block ordering and terminators from the accepted local DORT input."""

import re
from tempfile import TemporaryDirectory
from pathlib import Path
import unittest

import numpy as np

from dort_input import DORTModel, DORTWriter, generate_legacy_quadrature


def _writer_and_quadrature():
    model = DORTModel("combined test")
    model.add_mixture("A", {1001: 0.01}, legendre_order=5)
    model.add_mixture("B", {1002: 0.02}, legendre_order=5)
    model.mesh.r.add_segment(0, 2, step=1)
    model.mesh.z.add_segment(0, 2, step=1)
    model.set_background("A")
    model.add_region("b", material="B", r=(1, 2), z=(0, 2))
    model.build()
    return DORTWriter(model), generate_legacy_quadrature(order=16, symmetry="half")


class CompleteInputTest(unittest.TestCase):
    def test_first_run_blocks_match_accepted_card_order(self):
        writer, quadrature = _writer_and_quadrature()
        run = writer.create_run_control(
            "eigenvalue_first", energy_groups=4,
            quadrature_directions=quadrature.direction_count,
        )
        deck = writer.complete_input_text(
            run_control=run, quadrature=quadrature,
            array1="1** 0.5 0.5 F0.0", title="Case 1",
        )
        lines = deck.splitlines()
        cards = [(index, match.group()) for index, line in enumerate(lines)
                 if (match := re.match(r"\d{1,2}(?:\*\*|\$\$)", line))]
        self.assertEqual([card for _, card in cards], [
            "61$$", "62$$", "63**", "82**", "83**", "81**", "84$$",
            "1**", "2**", "4**", "8$$", "9$$", "93**", "94**", "95**",
        ])
        self.assertEqual(lines[0], "Case 1")
        self.assertEqual(lines[cards[2][0] + 1:cards[3][0]], ["t", "t", ""])
        self.assertEqual(lines[cards[6][0]].split()[-1], "t")
        self.assertEqual(lines[cards[7][0]:cards[8][0]], ["1** 0.5 0.5 F0.0"])
        self.assertEqual(lines[cards[11][0]].split()[-1], "t")
        self.assertEqual(lines[cards[12][0]:cards[14][0]], [
            "93** F 1.0 t", "94** F 1.0 t",
        ])
        self.assertEqual(lines[-2:], ["95** F 1.0 t", "t"])
        self.assertTrue(run.validate_deck_text(deck, strict_controls=True).valid)

    def test_numeric_group_data_restart_and_file_output(self):
        writer, quadrature = _writer_and_quadrature()
        run = writer.create_run_control(
            "eigenvalue_rerun", energy_groups=3,
            quadrature_directions=quadrature.direction_count,
        )
        with TemporaryDirectory() as directory:
            path = Path(directory) / "dortinp"
            written = writer.write_complete_input(
                path, run_control=run, quadrature=quadrature,
                array1=np.array([0.25, 0.75, 0.0]),
            )
            deck = written.read_text(encoding="ascii")
        self.assertIn("1** 0.25 0.75 0.0", deck)
        self.assertNotIn("93**", deck)
        self.assertTrue(deck.endswith("9$$ -1 -7 t\nt\n"))

    def test_fixed_source_cards_follow_geometry(self):
        writer, quadrature = _writer_and_quadrature()
        source = writer.create_source()
        source.by_material("B", strength=1.0)
        source.set_energy_spectrum([1.0, 2.0, 3.0])
        run = writer.create_run_control(
            "fixed_source", energy_groups=3,
            quadrature_directions=quadrature.direction_count,
            starting_flux="zero",
        )
        run.attach_source(source)
        deck = writer.complete_input_text(
            run_control=run, quadrature=quadrature, array1=[0.0] * 3
        )
        self.assertLess(deck.index("9$$"), deck.index("96**"))
        self.assertLess(deck.index("96**"), deck.index("98**"))
        self.assertNotIn("93**", deck)
        self.assertTrue(deck.endswith(" t\nt\n"))

    def test_rejects_wrong_direction_and_group_counts(self):
        writer, quadrature = _writer_and_quadrature()
        run = writer.create_run_control(
            "eigenvalue_first", energy_groups=4, quadrature_directions=48,
        )
        with self.assertRaisesRegex(ValueError, "MM"):
            writer.complete_input_text(
                run_control=run, quadrature=quadrature, array1=[1, 0, 0, 0]
            )
        run.controls62["MM"] = quadrature.direction_count
        with self.assertRaisesRegex(ValueError, "IGM"):
            writer.complete_input_text(
                run_control=run, quadrature=quadrature, array1=[1, 0]
            )
        with self.assertRaisesRegex(ValueError, "terminate 1"):
            writer.complete_input_text(
                run_control=run, quadrature=quadrature, array1="1** F0.0 t"
            )


if __name__ == "__main__":
    unittest.main()
