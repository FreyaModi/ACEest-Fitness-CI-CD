"""JSON REST API for ACEest Fitness & Gym."""

from flask import Blueprint, abort, jsonify, request

import fitness
from validators import ValidationError, require_number, require_text

bp = Blueprint("api", __name__, url_prefix="/api")


def get_payload():
    """Return the request body as a dict, or raise ValidationError."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError("Request body must be a JSON object")
    return data


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
