import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location("prepare", Path(__file__).resolve().parents[1] / "scripts/prepare_data.py")
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


@pytest.mark.parametrize("tags,forward,reverse", [
    ({"highway": "residential"}, 7, 7),
    ({"highway": "residential", "oneway": "yes"}, 7, 2),
    ({"highway": "residential", "oneway": "-1"}, 2, 7),
    ({"highway": "residential", "oneway": "yes", "oneway:bicycle": "no"}, 7, 6),
    ({"highway": "motorway"}, 1, 0),
    ({"highway": "steps"}, 2, 2),
    ({"highway": "residential", "access": "private"}, 0, 0),
    ({"highway": "residential", "access": "no", "foot": "yes"}, 2, 2),
    ({"highway": "construction"}, 0, 0),
    ({"highway": "residential", "motor_vehicle": "no"}, 6, 6),
    ({"highway": "residential", "junction": "roundabout"}, 7, 2),
    ({"leisure": "park", "foot": "yes"}, 0, 0),
])
def test_access_and_direction(tags, forward, reverse):
    assert prepare.permissions(tags) == (forward, reverse)


def test_speed_limit_and_mph():
    assert prepare.speeds({"highway": "primary", "maxspeed": "20"})[0] == 20
    assert prepare.speeds({"highway": "primary", "maxspeed": "10 mph"})[0] == pytest.approx(16.09344)
    assert prepare.speeds({"highway": "residential", "maxspeed": "signals"})[0] == 25
    assert prepare.speeds({"highway": "steps"})[1] == 3
