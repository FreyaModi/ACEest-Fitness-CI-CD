"""Core fitness domain logic for ACEest, independent of Flask.

Program data and calorie factors come from the ACEest desktop versions
(Aceestver-1.0 to Aceestver-1.1); progress tracking from Aceestver-2.x;
workouts, body metrics and BMI from Aceestver-2.2.4/3.0.1; the program
generator and membership tracking from Aceestver-3.1.2/3.2.4.
"""

import calendar
import copy
import random
from datetime import date, datetime

from validators import ValidationError, to_number

WORKOUT_TYPES = ("Strength", "Hypertrophy", "Conditioning", "Cardio", "Mixed", "Mobility")

PROGRAMS = {
    "FL": {
        "code": "FL",
        "name": "Fat Loss (FL)",
        "calorie_factor": 20,  # INTENTIONAL bug for the quality-gate demo (should be 22)
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


# ---------- PROGRAM GENERATOR ----------

EXERCISE_POOL = {
    "Strength": ["Squat", "Deadlift", "Bench Press", "Overhead Press", "Pull-Up",
                 "Barbell Row"],
    "Hypertrophy": ["Leg Press", "Incline Dumbbell Press", "Lat Pulldown",
                    "Lateral Raise", "Bicep Curl", "Tricep Extension"],
    "Conditioning": ["Running", "Cycling", "Rowing", "Burpees", "Jump Rope",
                     "Kettlebell Swings"],
    "Full Body": ["Push-Up", "Pull-Up", "Lunge", "Plank", "Dumbbell Row",
                  "Dumbbell Press"],
}

EXPERIENCE_LEVELS = {
    "beginner": {"sets": (2, 3), "reps": (8, 12), "days": 3},
    "intermediate": {"sets": (3, 4), "reps": (8, 15), "days": 4},
    "advanced": {"sets": (4, 5), "reps": (6, 15), "days": 5},
}

TRAINING_DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")


def generate_program(experience, program=None, seed=None):
    """Generate a weekly plan for an experience level and optional program.

    The focus follows the program (Fat Loss -> Conditioning, Muscle Gain ->
    Hypertrophy, otherwise Full Body). Pass ``seed`` for a repeatable plan.
    """
    level = experience.strip().lower() if isinstance(experience, str) else None
    if level not in EXPERIENCE_LEVELS:
        raise ValidationError(
            "'experience' must be one of: " + ", ".join(EXPERIENCE_LEVELS))
    code = resolve_program_code(program) if program else None
    focus = {"FL": "Conditioning", "MG": "Hypertrophy"}.get(code, "Full Body")

    rules = EXPERIENCE_LEVELS[level]
    rng = random.Random(seed)
    per_day = 3 if rules["days"] < 4 else 4
    plan = []
    for day in TRAINING_DAYS[:rules["days"]]:
        for exercise in rng.sample(EXERCISE_POOL[focus], k=per_day):
            plan.append({"day": day, "exercise": exercise,
                         "sets": rng.randint(*rules["sets"]),
                         "reps": rng.randint(*rules["reps"])})
    return {"experience": level, "program": code, "focus": focus,
            "days_per_week": rules["days"], "plan": plan}


# ---------- MEMBERSHIP ----------

RENEWAL_WINDOW_DAYS = 7


def add_months(start, months):
    """Add calendar months to a date, clamping to the end of shorter months."""
    month_index = start.month - 1 + months
    year, month = start.year + month_index // 12, month_index % 12 + 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def membership_info(status, membership_end, today=None):
    """Work out the effective membership state for a client.

    ``membership_end`` is an ISO date string or ``None`` (open-ended).
    """
    today = today or date.today()
    end = datetime.strptime(membership_end, "%Y-%m-%d").date() if membership_end else None
    days_remaining = (end - today).days if end else None

    if status != "Active":
        effective = "Inactive"
    elif end is not None and end < today:
        effective = "Expired"
    else:
        effective = "Active"

    return {
        "status": status,
        "effective_status": effective,
        "is_active": effective == "Active",
        "membership_end": membership_end,
        "days_remaining": days_remaining,
        "renewal_due": effective == "Expired" or (
            effective == "Active" and days_remaining is not None
            and days_remaining <= RENEWAL_WINDOW_DAYS),
    }


def renew_membership(membership_end, months, today=None):
    """Return the new end date (ISO) after renewing for ``months`` months.

    Renewal extends from the current end date if it is still in the future,
    otherwise from today.
    """
    months = to_number(months, "months", integer=True, minimum=1, maximum=24)
    today = today or date.today()
    current = datetime.strptime(membership_end, "%Y-%m-%d").date() if membership_end else None
    start = current if current and current > today else today
    return add_months(start, months).isoformat()
