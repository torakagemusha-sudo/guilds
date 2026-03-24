import argparse
import sys
import types

import pytest

from core import guilds_cli


class PhaseCapture(RuntimeError):
    def __init__(self, phase: str):
        super().__init__(phase)
        self.phase = phase


def test_phase_to_const_maps_human_phase_names():
    assert guilds_cli._phase_to_const("idle", default="idle") == guilds_cli.PHASE_IDLE
    assert guilds_cli._phase_to_const("execute", default="execute") == guilds_cli.PHASE_EXECUTE


def test_cmd_compile_uses_phase_constant_for_idle(tmp_path, monkeypatch):
    spec_path = tmp_path / "spec.guilds"
    spec_path.write_text("claim X {}", encoding="utf-8")

    pyinstaller_module = types.ModuleType("PyInstaller")
    pyinstaller_main = types.ModuleType("PyInstaller.__main__")
    pyinstaller_main.run = lambda _args: None
    pyinstaller_module.__main__ = pyinstaller_main
    monkeypatch.setitem(sys.modules, "PyInstaller", pyinstaller_module)
    monkeypatch.setitem(sys.modules, "PyInstaller.__main__", pyinstaller_main)

    monkeypatch.setattr(guilds_cli, "parse_source", lambda _src, _name: (object(), []))

    class RaisingEvaluator:
        def __init__(self, _program, ctx):
            raise PhaseCapture(ctx.phase)

    monkeypatch.setattr(guilds_cli, "Evaluator", RaisingEvaluator)

    args = argparse.Namespace(
        spec=str(spec_path),
        output=None,
        backend="pyside6",
        name=None,
        onefile=False,
        console=False,
        icon=None,
    )

    with pytest.raises(PhaseCapture) as exc:
        guilds_cli.cmd_compile(args)

    assert exc.value.phase == guilds_cli.PHASE_IDLE
