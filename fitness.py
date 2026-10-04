"""Core fitness domain logic for ACEest, independent of Flask.

Program data and calorie factors come from the ACEest desktop versions
(Aceestver-1.0 to Aceestver-1.1).
"""

import copy

from validators import ValidationError, to_number

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
