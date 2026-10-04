"""Unit tests for the validation helpers."""

import pytest

from validators import (ValidationError, optional_date, optional_number,
                        optional_text, require_number, require_text, to_number)


class TestToNumber:
    @pytest.mark.parametrize("value, expected", [(70, 70.0), (72.5, 72.5), ("80", 80.0)])
    def test_accepts_numbers_and_numeric_strings(self, value, expected):
        assert to_number(value, "weight") == expected

    @pytest.mark.parametrize("value", [None, True, "abc", [], {}, "nan", "inf"])
    def test_rejects_non_numbers(self, value):
        with pytest.raises(ValidationError):
            to_number(value, "weight")

    def test_integer_mode_returns_int(self):
        result = to_number("25", "age", integer=True)
        assert result == 25 and isinstance(result, int)

    def test_integer_mode_rejects_fractions(self):
        with pytest.raises(ValidationError, match="whole number"):
            to_number(25.5, "age", integer=True)

    @pytest.mark.parametrize("value", [0, -1])
    def test_positive_rejects_zero_and_negative(self, value):
        with pytest.raises(ValidationError, match="greater than 0"):
            to_number(value, "weight", positive=True)

    def test_bounds(self):
        assert to_number(100, "adherence", minimum=0, maximum=100) == 100
        with pytest.raises(ValidationError, match="at most 100"):
            to_number(101, "adherence", maximum=100)
        with pytest.raises(ValidationError, match="at least 0"):
            to_number(-5, "adherence", minimum=0)


class TestFieldHelpers:
    def test_require_number_missing(self):
        with pytest.raises(ValidationError, match="'weight' is required"):
            require_number({}, "weight")

    def test_optional_number_absent_or_blank(self):
        assert optional_number({}, "age") is None
        assert optional_number({"age": ""}, "age") is None
        assert optional_number({"age": 30}, "age", integer=True) == 30

    def test_require_text_strips_whitespace(self):
        assert require_text({"name": "  Arjun "}, "name") == "Arjun"

    @pytest.mark.parametrize("data", [{}, {"name": ""}, {"name": "   "}, {"name": 5}])
    def test_require_text_rejects_missing_or_invalid(self, data):
        with pytest.raises(ValidationError):
            require_text(data, "name")

    def test_require_text_max_length(self):
        with pytest.raises(ValidationError, match="at most 3"):
            require_text({"name": "abcd"}, "name", max_length=3)

    def test_optional_text(self):
        assert optional_text({}, "notes") is None
        assert optional_text({"notes": " good "}, "notes") == "good"
        with pytest.raises(ValidationError, match="must be a string"):
            optional_text({"notes": 12}, "notes")

    def test_optional_date(self):
        assert optional_date({}, "date") is None
        assert optional_date({"date": "2026-03-04"}, "date") == "2026-03-04"

    @pytest.mark.parametrize("value", ["04-03-2026", "2026-13-01", "tomorrow", 20260304])
    def test_optional_date_rejects_bad_formats(self, value):
        with pytest.raises(ValidationError, match="YYYY-MM-DD"):
            optional_date({"date": value}, "date")
