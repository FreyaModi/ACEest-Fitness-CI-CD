# Assignment 1 source versions

The scripts in `assignment-1/` are preserved unchanged from the supplied
Assignment 1 folder. They represent the incremental desktop application
versions. The Assignment 2 Flask implementation is in the project root:

- `fitness.py` contains training program, calorie, BMI, plan generation, and
  membership rules.
- `api.py` exposes those capabilities through the REST API.
- `models.py`, `database.py`, and `schema.sql` provide SQLite persistence.
- `app.py` and `templates/` provide the Flask application and dashboard.

The source scripts are retained for traceability; use the Flask modules and
tests for the CI/CD pipeline.
