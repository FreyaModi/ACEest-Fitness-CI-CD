"""Unit tests for the core fitness domain logic."""

from datetime import date

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


class TestProgressHelpers:
    def test_current_week_label_format(self):
        assert fitness.current_week_label(date(2026, 3, 4)) == "Week 09 - 2026"

    def test_current_week_label_defaults_to_today(self):
        assert fitness.current_week_label().endswith(str(date.today().year))

    def test_summarize_adherence(self):
        assert fitness.summarize_adherence([80, 90, 75]) == (3, 81.7)

    def test_summarize_adherence_empty(self):
        assert fitness.summarize_adherence([]) == (0, 0.0)


class TestBmi:
    @pytest.mark.parametrize("height, weight, bmi, category", [
        (175, 50, 16.3, "Underweight"),
        (175, 70, 22.9, "Normal"),
        (175, 85, 27.8, "Overweight"),
        (175, 100, 32.7, "Obese"),
    ])
    def test_categories(self, height, weight, bmi, category):
        result = fitness.calculate_bmi(height, weight)
        assert result["bmi"] == bmi
        assert result["category"] == category
        assert result["risk"]

    @pytest.mark.parametrize("height, weight, category", [
        (100, 18.5, "Normal"),      # BMI exactly 18.5
        (100, 25, "Overweight"),    # BMI exactly 25
        (100, 30, "Obese"),         # BMI exactly 30
    ])
    def test_category_boundaries(self, height, weight, category):
        assert fitness.calculate_bmi(height, weight)["category"] == category

    @pytest.mark.parametrize("height, weight", [(0, 70), (175, 0), ("x", 70), (175, None)])
    def test_invalid_input(self, height, weight):
        with pytest.raises(ValidationError):
            fitness.calculate_bmi(height, weight)
