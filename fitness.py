"""Core fitness domain logic for ACEest, independent of Flask.

Program data and calorie factors come from the ACEest desktop versions
(Aceestver-1.0 to Aceestver-1.1); progress tracking from Aceestver-2.x;
workouts, body metrics and BMI from Aceestver-2.2.4/3.0.1.
"""

import copy
from datetime import date

from validators import ValidationError, to_number

WORKOUT_TYPES = ("Strength", "Hypertrophy", "Conditioning", "Cardio", "Mixed", "Mobility")

PROGRAMS = {
    "FL": {
        "code": "FL",
        "name": "Fat Loss (FL)",
        "calorie_factor": 22,
        "focus": "Conditioning",
        "color": "#e74c3c",
        "description": "Conditioning-led programme to drive fat loss.",
        "workout": [
            "Mon: Back Squat 5x5 + Core",
            "Tue: EMOM 20min Assault Bike",
            "Wed: Bench Press + 21-15-9",
            "Thu: Deadlift + Box Jumps",
            "Fri: Zone 2 Cardio 30min",
        ],
        "diet": [
            "Breakfast: Egg Whites + Oats",
            "Lunch: Grilled Chicken + Brown Rice",
            "Dinner: Fish Curry + Millet Roti",
            "Target: ~2000 kcal",
        ],
    },
    "MG": {
        "code": "MG",
        "name": "Muscle Gain (MG)",
        "calorie_factor": 35,
        "focus": "Hypertrophy",
        "color": "#2ecc71",
        "description": "High-volume strength and hypertrophy split.",
        "workout": [
            "Mon: Squat 5x5",
            "Tue: Bench 5x5",
            "Wed: Deadlift 4x6",
            "Thu: Front Squat 4x8",
            "Fri: Incline Press 4x10",
            "Sat: Barbell Rows 4x10",
        ],
        "diet": [
            "Breakfast: Eggs + Peanut Butter Oats",
            "Lunch: Chicken Biryani",
            "Dinner: Mutton Curry + Rice",
            "Target: ~3200 kcal",
        ],
    },
    "BG": {
        "code": "BG",
        "name": "Beginner (BG)",
        "calorie_factor": 26,
        "focus": "Full Body",
        "color": "#3498db",
        "description": "Simple full-body circuit focused on technique.",
        "workout": [
            "Full Body Circuit:",
            "- Air Squats",
            "- Ring Rows",
            "- Push-ups",
            "Focus: Technique & Consistency",
        ],
        "diet": [
            "Balanced Tamil Meals",
            "Idli / Dosa / Rice + Dal",
            "Protein Target: 120g/day",
        ],
    },
}


def list_programs():
    """Return copies of all programs, ordered by code."""
    return [copy.deepcopy(PROGRAMS[code]) for code in sorted(PROGRAMS)]


def get_program(identifier):
    """Look up a program by code ("FL") or full name ("Fat Loss (FL)").

    Matching is case-insensitive. Returns a copy, or ``None`` if unknown.
    """
    if not isinstance(identifier, str):
        return None
    key = identifier.strip().upper()
    for program in PROGRAMS.values():
        if key in (program["code"], program["name"].upper()):
            return copy.deepcopy(program)
    return None


def resolve_program_code(identifier):
    """Return the canonical program code, raising if it is unknown."""
    program = get_program(identifier)
    if program is None:
        valid = ", ".join(sorted(PROGRAMS))
        raise ValidationError(
            f"Unknown program '{identifier}'. Valid codes: {valid}")
    return program["code"]


def calculate_calories(weight_kg, program):
    """Estimate daily calories as body weight x the program's factor."""
    weight = to_number(weight_kg, "weight", positive=True, maximum=500)
    code = resolve_program_code(program)
    return int(weight * PROGRAMS[code]["calorie_factor"])


def current_week_label(today=None):
    """Return the week label used for progress logs, e.g. "Week 09 - 2026"."""
    today = today or date.today()
    return today.strftime("Week %U - %Y")


def summarize_adherence(values):
    """Return (weeks_logged, average_adherence rounded to 1 decimal)."""
    values = list(values)
    if not values:
        return 0, 0.0
    return len(values), round(sum(values) / len(values), 1)


def calculate_bmi(height_cm, weight_kg):
    """Return BMI (1 decimal) with its WHO category and a coaching risk note."""
    height = to_number(height_cm, "height", positive=True, maximum=300)
    weight = to_number(weight_kg, "weight", positive=True, maximum=500)
    height_m = height / 100.0
    bmi = round(weight / (height_m * height_m), 1)

    if bmi < 18.5:
        category, risk = "Underweight", "Potential nutrient deficiency, low energy."
    elif bmi < 25:
        category, risk = "Normal", "Low risk if active and strong."
    elif bmi < 30:
        category, risk = ("Overweight",
                          "Moderate risk; focus on adherence and progressive activity.")
    else:
        category, risk = ("Obese",
                          "Higher risk; prioritize fat loss, consistency, and supervision.")
    return {"bmi": bmi, "category": category, "risk": risk}
