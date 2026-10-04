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


class TestProgramGenerator:
    @pytest.mark.parametrize("experience, days, per_day, sets, reps", [
        ("beginner", 3, 3, (2, 3), (8, 12)),
        ("intermediate", 4, 4, (3, 4), (8, 15)),
        ("advanced", 5, 4, (4, 5), (6, 15)),
    ])
    def test_plan_respects_experience_rules(self, experience, days, per_day, sets, reps):
        result = fitness.generate_program(experience, seed=1)
        assert result["days_per_week"] == days
        assert len(result["plan"]) == days * per_day
        assert len({item["day"] for item in result["plan"]}) == days
        for item in result["plan"]:
            assert sets[0] <= item["sets"] <= sets[1]
            assert reps[0] <= item["reps"] <= reps[1]

    @pytest.mark.parametrize("program, focus", [
        ("FL", "Conditioning"), ("MG", "Hypertrophy"), ("BG", "Full Body"), (None, "Full Body"),
    ])
    def test_focus_follows_program(self, program, focus):
        result = fitness.generate_program("beginner", program=program, seed=3)
        assert result["focus"] == focus
        pool = fitness.EXERCISE_POOL[focus]
        assert all(item["exercise"] in pool for item in result["plan"])

    def test_no_duplicate_exercise_within_a_day(self):
        plan = fitness.generate_program("advanced", seed=7)["plan"]
        for day in {item["day"] for item in plan}:
            exercises = [i["exercise"] for i in plan if i["day"] == day]
            assert len(exercises) == len(set(exercises))

    def test_seed_makes_plan_repeatable(self):
        assert (fitness.generate_program("Intermediate", "MG", seed=42)
                == fitness.generate_program("intermediate", "MG", seed=42))

    @pytest.mark.parametrize("experience", ["expert", "", None, 3])
    def test_invalid_experience(self, experience):
        with pytest.raises(ValidationError, match="experience"):
            fitness.generate_program(experience)

    def test_invalid_program(self):
        with pytest.raises(ValidationError, match="Unknown program"):
            fitness.generate_program("beginner", program="Yoga")


class TestMembership:
    TODAY = date(2026, 3, 4)

    @pytest.mark.parametrize("start, months, expected", [
        (date(2026, 1, 31), 1, date(2026, 2, 28)),   # clamp to shorter month
        (date(2028, 1, 31), 1, date(2028, 2, 29)),   # leap year
        (date(2026, 11, 15), 3, date(2027, 2, 15)),  # crosses year end
        (date(2026, 3, 4), 12, date(2027, 3, 4)),
    ])
    def test_add_months(self, start, months, expected):
        assert fitness.add_months(start, months) == expected

    def test_active_with_future_end(self):
        info = fitness.membership_info("Active", "2026-06-30", today=self.TODAY)
        assert info["effective_status"] == "Active" and info["is_active"]
        assert info["days_remaining"] == 118
        assert info["renewal_due"] is False

    def test_active_within_renewal_window(self):
        info = fitness.membership_info("Active", "2026-03-10", today=self.TODAY)
        assert info["is_active"] and info["renewal_due"]

    def test_expires_today_is_still_active(self):
        info = fitness.membership_info("Active", "2026-03-04", today=self.TODAY)
        assert info["is_active"] and info["days_remaining"] == 0

    def test_expired(self):
        info = fitness.membership_info("Active", "2026-03-01", today=self.TODAY)
        assert info["effective_status"] == "Expired"
        assert not info["is_active"] and info["renewal_due"]
        assert info["days_remaining"] == -3

    def test_open_ended(self):
        info = fitness.membership_info("Active", None, today=self.TODAY)
        assert info["is_active"] and info["days_remaining"] is None
        assert info["renewal_due"] is False

    def test_inactive(self):
        info = fitness.membership_info("Inactive", "2026-12-31", today=self.TODAY)
        assert info["effective_status"] == "Inactive"
        assert not info["is_active"] and not info["renewal_due"]

    def test_membership_info_defaults_to_today(self):
        assert fitness.membership_info("Active", None)["is_active"]

    def test_renew_extends_from_future_end_date(self):
        assert fitness.renew_membership("2026-04-30", 1, today=self.TODAY) == "2026-05-30"

    @pytest.mark.parametrize("end", [None, "2026-01-15"])
    def test_renew_starts_today_when_missing_or_expired(self, end):
        assert fitness.renew_membership(end, 3, today=self.TODAY) == "2026-06-04"

    def test_renew_defaults_to_today(self):
        expected = fitness.add_months(date.today(), 1).isoformat()
        assert fitness.renew_membership(None, 1) == expected

    @pytest.mark.parametrize("months", [0, 25, 1.5, "one", None])
    def test_renew_invalid_months(self, months):
        with pytest.raises(ValidationError, match="months"):
            fitness.renew_membership(None, months, today=self.TODAY)
