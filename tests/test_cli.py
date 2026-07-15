'''
 Copyright (c) 2026, UChicago Argonne, LLC
 See LICENSE file.
'''
import json

from rsMap3D import cli


def test_no_subcommand_launches_gui(monkeypatch):
    calls = []
    monkeypatch.setattr("rsMap3D.rsmEdit.main", lambda: calls.append("gui"))
    cli.main([])
    assert calls == ["gui"]


def test_gui_subcommand_launches_gui(monkeypatch):
    calls = []
    monkeypatch.setattr("rsMap3D.rsmEdit.main", lambda: calls.append("gui"))
    cli.main(["gui"])
    assert calls == ["gui"]


def test_map_angle_scan_dispatches_with_parsed_config(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr("rsMap3D.workflows.angle_scan.run", lambda config: calls.append(config))
    config_path = tmp_path / "cfg.json"
    config_path.write_text(json.dumps({"project_dir": "/tmp/x"}))
    cli.main(["map-angle-scan", str(config_path)])
    assert calls == [{"project_dir": "/tmp/x"}]


def test_map_parametric_scan_dispatches_with_parsed_config(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr("rsMap3D.workflows.parametric_scan.run", lambda config: calls.append(config))
    config_path = tmp_path / "cfg.json"
    config_path.write_text(json.dumps({"scan_list": ["1"]}))
    cli.main(["map-parametric-scan", str(config_path)])
    assert calls == [{"scan_list": ["1"]}]


def test_powder_scan_dispatches_with_parsed_config(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr("rsMap3D.workflows.powder_scan.run", lambda config: calls.append(config))
    config_path = tmp_path / "cfg.json"
    config_path.write_text(json.dumps({"datasets": []}))
    cli.main(["powder-scan", str(config_path)])
    assert calls == [{"datasets": []}]
