"""Unit tests for the core fitness domain logic."""

import pytest

import fitness
from validators import ValidationError


class TestPrograms:
    def test_list_programs_returns_all_three(self):
        codes = [p["code"] for p in fitness.list_programs()]
        assert codes == ["BG", "FL", "MG"]

    @pytest.mark.parametrize("program", fitness.list_programs())
    def test_program_has_required_fields(self, program):
        for field in ("code", "name", "calorie_factor", "focus", "description",
                      "workout", "diet"):
            assert program[field]

    @pytest.mark.parametrize("identifier", ["FL", "fl", " Fl ", "Fat Loss (FL)", "fat loss (fl)"])
    def test_get_program_by_code_or_name(self, identifier):
        assert fitness.get_program(identifier)["code"] == "FL"

    @pytest.mark.parametrize("identifier", ["XX", "", None, 42])
    def test_get_program_unknown_returns_none(self, identifier):
        assert fitness.get_program(identifier) is None

    def test_get_program_returns_copy(self):
        fitness.get_program("FL")["workout"].append("tampered")
        assert "tampered" not in fitness.PROGRAMS["FL"]["workout"]

    def test_resolve_program_code_unknown_raises(self):
        with pytest.raises(ValidationError, match="Unknown program"):
            fitness.resolve_program_code("Yoga")


class TestCalories:
    @pytest.mark.parametrize("code, weight, expected", [
        ("FL", 70, 1540),   # 70 x 22
        ("MG", 80, 2800),   # 80 x 35
        ("BG", 60, 1560),   # 60 x 26
        ("FL", 72.5, 1595),  # int(72.5 x 22)
    ])
    def test_calculate_calories(self, code, weight, expected):
        assert fitness.calculate_calories(weight, code) == expected

    def test_calories_accepts_program_name(self):
        assert fitness.calculate_calories(70, "Muscle Gain (MG)") == 2450

    @pytest.mark.parametrize("weight", [0, -10, "heavy", None])
    def test_calories_invalid_weight(self, weight):
        with pytest.raises(ValidationError):
            fitness.calculate_calories(weight, "FL")

    def test_calories_unknown_program(self):
        with pytest.raises(ValidationError):
            fitness.calculate_calories(70, "ZZ")
