"""JSON REST API for ACEest Fitness & Gym."""

import csv
import io
from datetime import date

from flask import Blueprint, Response, abort, jsonify, request

import fitness
import models
from validators import (ValidationError, optional_date, optional_number,
                        optional_text, require_number, require_text)

bp = Blueprint("api", __name__, url_prefix="/api")

MEMBERSHIP_STATUSES = ("Active", "Inactive")

# Validation rules for the optional numeric client fields.
CLIENT_NUMBER_RULES = {
    "age": {"integer": True, "minimum": 1, "maximum": 120},
    "height": {"positive": True, "maximum": 300},
    "weight": {"positive": True, "maximum": 500},
    "target_weight": {"positive": True, "maximum": 500},
    "target_adherence": {"integer": True, "minimum": 0, "maximum": 100},
}


def get_payload():
    """Return the request body as a dict, or raise ValidationError."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError("Request body must be a JSON object")
    return data


def parse_client_fields(data):
    """Validate the client profile fields present in ``data``."""
    fields = {}
    for field, rules in CLIENT_NUMBER_RULES.items():
        if field in data:
            fields[field] = optional_number(data, field, **rules)
    if "program" in data:
        program = data["program"]
        blank = program is None or (isinstance(program, str) and not program.strip())
        fields["program"] = None if blank else fitness.resolve_program_code(program)
    if "membership_status" in data:
        status = data["membership_status"]
        matches = [s for s in MEMBERSHIP_STATUSES
                   if isinstance(status, str) and s.lower() == status.strip().lower()]
        if not matches:
            raise ValidationError(
                "'membership_status' must be one of: " + ", ".join(MEMBERSHIP_STATUSES))
        fields["membership_status"] = matches[0]
    if "membership_end" in data:
        fields["membership_end"] = optional_date(data, "membership_end")
    return fields


def compute_calories(weight, program):
    if weight is None or program is None:
        return None
    return fitness.calculate_calories(weight, program)


# ---------- PROGRAMS ----------

@bp.get("/programs")
def list_programs():
    return jsonify(fitness.list_programs())


@bp.get("/programs/<code>")
def get_program(code):
    program = fitness.get_program(code)
    if program is None:
        abort(404, description=f"Program '{code}' not found")
    return jsonify(program)


@bp.post("/calories")
def calories():
    data = get_payload()
    weight = require_number(data, "weight", positive=True, maximum=500)
    code = fitness.resolve_program_code(require_text(data, "program"))
    return jsonify(program=code, weight=weight,
                   calories=fitness.calculate_calories(weight, code))


# ---------- CLIENTS ----------

@bp.get("/clients")
def list_clients():
    return jsonify(models.list_clients())


@bp.post("/clients")
def create_client():
    data = get_payload()
    fields = {"name": require_text(data, "name"), **parse_client_fields(data)}
    fields["calories"] = compute_calories(fields.get("weight"), fields.get("program"))
    return jsonify(models.create_client(fields)), 201


@bp.get("/clients/<name>")
def get_client(name):
    return jsonify(models.get_client(name))


@bp.patch("/clients/<name>")
def update_client(name):
    data = get_payload()
    client = models.get_client(name)
    if "name" in data and str(data["name"]).strip().lower() != client["name"].lower():
        raise ValidationError("Client name cannot be changed")
    fields = parse_client_fields(data)
    merged = {**client, **fields}
    fields["calories"] = compute_calories(merged["weight"], merged["program"])
    return jsonify(models.update_client(client["name"], fields))


@bp.delete("/clients/<name>")
def delete_client(name):
    models.delete_client(name)
    return "", 204


@bp.get("/export/clients.csv")
def export_clients_csv():
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=models.CLIENT_COLUMNS,
                            extrasaction="ignore")
    writer.writeheader()
    writer.writerows(models.list_clients())
    return Response(buffer.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=clients.csv"})


# ---------- WEEKLY PROGRESS ----------

@bp.post("/clients/<name>/progress")
def add_progress(name):
    client = models.get_client(name)
    data = get_payload()
    adherence = require_number(data, "adherence", integer=True, minimum=0, maximum=100)
    week = optional_text(data, "week", max_length=30) or fitness.current_week_label()
    return jsonify(models.add_progress(client["id"], week, adherence)), 201


@bp.get("/clients/<name>/progress")
def get_progress(name):
    client = models.get_client(name)
    entries = models.list_progress(client["id"])
    weeks, average = fitness.summarize_adherence(e["adherence"] for e in entries)
    return jsonify(client=client["name"], weeks_logged=weeks,
                   average_adherence=average, entries=entries)


# ---------- BMI ----------

@bp.post("/bmi")
def bmi():
    data = get_payload()
    return jsonify(fitness.calculate_bmi(require_number(data, "height"),
                                         require_number(data, "weight")))


@bp.get("/clients/<name>/bmi")
def client_bmi(name):
    client = models.get_client(name)
    if not client["height"] or not client["weight"]:
        raise ValidationError(f"Client '{client['name']}' needs height and weight for BMI")
    return jsonify(client=client["name"],
                   **fitness.calculate_bmi(client["height"], client["weight"]))


# ---------- WORKOUTS ----------

def parse_exercises(raw):
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValidationError("'exercises' must be a list")
    exercises = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValidationError(f"exercises[{index}] must be an object")
        try:
            exercises.append({
                "name": require_text(item, "name"),
                "sets": require_number(item, "sets", integer=True, minimum=1, maximum=20),
                "reps": require_number(item, "reps", integer=True, minimum=1, maximum=100),
                "weight": optional_number(item, "weight", minimum=0, maximum=1000) or 0.0,
            })
        except ValidationError as error:
            raise ValidationError(f"exercises[{index}]: {error}") from None
    return exercises


@bp.post("/clients/<name>/workouts")
def add_workout(name):
    client = models.get_client(name)
    data = get_payload()
    workout_type = require_text(data, "workout_type")
    matches = [t for t in fitness.WORKOUT_TYPES if t.lower() == workout_type.lower()]
    if not matches:
        raise ValidationError(
            "'workout_type' must be one of: " + ", ".join(fitness.WORKOUT_TYPES))
    workout = {
        "date": optional_date(data, "date") or date.today().isoformat(),
        "workout_type": matches[0],
        "duration_min": optional_number(data, "duration_min", integer=True,
                                        minimum=1, maximum=600) or 60,
        "notes": optional_text(data, "notes"),
    }
    exercises = parse_exercises(data.get("exercises"))
    return jsonify(models.add_workout(client["id"], workout, exercises)), 201


@bp.get("/clients/<name>/workouts")
def list_workouts(name):
    client = models.get_client(name)
    return jsonify(client=client["name"], workouts=models.list_workouts(client["id"]))


# ---------- BODY METRICS ----------

@bp.post("/clients/<name>/metrics")
def add_metric(name):
    client = models.get_client(name)
    data = get_payload()
    metric = {
        "date": optional_date(data, "date") or date.today().isoformat(),
        "weight": optional_number(data, "weight", positive=True, maximum=500),
        "waist": optional_number(data, "waist", positive=True, maximum=300),
        "bodyfat": optional_number(data, "bodyfat", minimum=1, maximum=75),
    }
    if all(metric[key] is None for key in ("weight", "waist", "bodyfat")):
        raise ValidationError("Provide at least one of 'weight', 'waist' or 'bodyfat'")
    entry = models.add_metric(client["id"], metric)
    if metric["weight"] is not None:
        # Keep the profile weight (and calorie target) in line with the latest weigh-in.
        models.update_client(client["name"], {
            "weight": metric["weight"],
            "calories": compute_calories(metric["weight"], client["program"]),
        })
    return jsonify(entry), 201


@bp.get("/clients/<name>/metrics")
def list_metrics(name):
    client = models.get_client(name)
    return jsonify(client=client["name"], metrics=models.list_metrics(client["id"]))


# ---------- CLIENT SUMMARY ----------

@bp.get("/clients/<name>/summary")
def client_summary(name):
    client = models.get_client(name)
    program = fitness.get_program(client["program"]) if client["program"] else None
    weeks, average = fitness.summarize_adherence(
        e["adherence"] for e in models.list_progress(client["id"]))
    metrics = models.list_metrics(client["id"])

    bmi = None
    if client["height"] and client["weight"]:
        bmi = fitness.calculate_bmi(client["height"], client["weight"])

    weight_to_target = None
    if client["weight"] and client["target_weight"]:
        weight_to_target = round(client["weight"] - client["target_weight"], 1)

    adherence_on_track = None
    if client["target_adherence"] is not None and weeks:
        adherence_on_track = average >= client["target_adherence"]

    return jsonify(
        profile=client,
        program=None if program is None else {
            key: program[key] for key in ("code", "name", "focus", "description")},
        goals={"target_weight": client["target_weight"],
               "target_adherence": client["target_adherence"],
               "weight_to_target": weight_to_target,
               "adherence_on_track": adherence_on_track},
        progress={"weeks_logged": weeks, "average_adherence": average},
        workouts_logged=len(models.list_workouts(client["id"])),
        last_metrics=metrics[-1] if metrics else None,
        bmi=bmi,
    )


# ---------- PROGRAM GENERATOR ----------

def parse_seed(data):
    return optional_number(data, "seed", integer=True)


@bp.post("/programs/generate")
def generate_program():
    data = get_payload()
    return jsonify(fitness.generate_program(data.get("experience"),
                                            program=data.get("program"),
                                            seed=parse_seed(data)))


@bp.post("/clients/<name>/generate-program")
def generate_client_program(name):
    client = models.get_client(name)
    data = get_payload()
    plan = fitness.generate_program(data.get("experience"), program=client["program"],
                                    seed=parse_seed(data))
    return jsonify(client=client["name"], **plan)


# ---------- MEMBERSHIP ----------

@bp.get("/clients/<name>/membership")
def membership(name):
    client = models.get_client(name)
    return jsonify(client=client["name"],
                   **fitness.membership_info(client["membership_status"],
                                             client["membership_end"]))


@bp.post("/clients/<name>/membership/renew")
def renew_membership(name):
    client = models.get_client(name)
    data = get_payload()
    new_end = fitness.renew_membership(client["membership_end"], data.get("months"))
    client = models.update_client(client["name"], {"membership_status": "Active",
                                                   "membership_end": new_end})
    return jsonify(client=client["name"],
                   **fitness.membership_info(client["membership_status"],
                                             client["membership_end"]))
