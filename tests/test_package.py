from dort_input import DORTModel, DORTWriter, __version__


def test_public_api_builds_minimal_model() -> None:
    model = DORTModel("smoke_test")
    model.add_material("Sodium")
    model.mesh.r.add_segment(0.0, 20.0, step=5.0)
    model.mesh.z.add_segment(-10.0, 10.0, step=5.0)
    model.set_background("Sodium")

    summary = model.build()
    writer = DORTWriter(model)

    assert __version__ == "0.4.1"
    assert summary.shape == (4, 4)
    assert writer.im == 4
    assert writer.jm == 4
    assert writer.array9().startswith("9$$")
    assert writer.array61().startswith("61$$")
