"""JSON REST API for ACEest Fitness & Gym."""

import csv
import io

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
