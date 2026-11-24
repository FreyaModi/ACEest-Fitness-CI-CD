# Assignment 2: ACEest Fitness CI/CD Implementation

## CI/CD architecture

The ACEest Fitness application is organized as a Flask application with a
separate API, fitness rules, data access, database setup, and input validation.
The original Assignment 1 scripts are retained in `versions/assignment-1/` as
the source history for the incremental feature set. The web application and its
Pytest suite are the maintained implementation.

The build workflow is:

```text
Git change → Jenkins checkout → compile and lint → Pytest + coverage
           → SonarQube analysis and quality gate (when configured)
           → Docker test/runtime images → container tests → health smoke test
```

The supplied Jenkinsfile polls SCM, checks out the configured branch, installs
development dependencies, runs Flake8 and Pytest, publishes JUnit results,
builds test and runtime images, runs the tests in the test image, and checks the
runtime health endpoint. SonarQube analysis and quality gate enforcement are
wired into the pipeline and activated after configuring the Jenkins server and
scanner. GitHub Actions configuration is included as an additional CI option.

The Dockerfile uses a multi-stage build. The test image contains test tools and
tests; the runtime image contains only application dependencies and source,
runs as an unprivileged user, and exposes a health check. Kubernetes templates
cover a rolling update, blue/green service switch, NGINX canary, header-based
A/B routing, and shadow traffic mirroring. These are examples to apply to a
configured cluster, not evidence of a live deployment.

Jenkins polls the configured source branch every two minutes because a local
Jenkins instance is not normally reachable by a GitHub webhook. Each build gets
a unique image tag based on its job and build number. This makes it possible to
identify the artifact created by a specific CI run. JUnit XML is published to
Jenkins and coverage XML is produced for SonarQube. Container smoke testing
waits for the image health check before calling `/health`.

The deployment examples implement separate traffic controls: rolling update
keeps the Service in place while Kubernetes replaces pods; blue/green keeps a
stable and candidate Deployment and switches the Service selector; canary sends
a configured share of eligible requests to a candidate; A/B routes requests
with an experiment header to variant B; and shadow mirrors requests to a
candidate while returning stable responses to callers. Rollback is performed
by undoing a Deployment revision, restoring the blue/green Service selector,
or disabling and removing the candidate ingress. These mechanisms depend on a
cluster ingress controller for the NGINX-specific patterns.

## Challenges and mitigation

The Assignment 1 code is a collection of versioned Python programs, while the
CI/CD starter is a modular Flask web application. The source scripts are
preserved in the repository and the implemented application groups the
features into maintainable modules. Pytest tests are kept separate from
production dependencies and are configured to run in an isolated container
stage.

The application currently persists to SQLite. SQLite files are local to a
container and are not a safe shared database for blue/green, canary, shadow, or
multi-replica traffic. The Kubernetes files are explicitly marked as strategy
demonstrations; even a one-replica rolling Deployment briefly overlaps old and
new pods. A shared database migration is required before production
multi-version traffic or horizontal scaling. This avoids presenting
independent pod databases as a reliable deployment.

Jenkins needs a configured SCM repository, Docker-capable agent, and (for the
quality gate) a SonarQube server, scanner installation, and webhook. The
repository contains pipeline configuration, but credentials and remote service
configuration are environment-specific and are not embedded in source. GitHub
access is confirmed and the existing public ACEest repository is available.
The Assignment 2 changes are being prepared on a separate branch. Docker Hub
publishing and a running Minikube/cloud endpoint remain pending external setup.
The Prayogshala account
and its DevOps lab are accessible; the lab session has not been launched.

## Automation outcomes and current status

The project includes application code, unit-test sources, Docker test and
runtime stages, Jenkins CI configuration, a GitHub Actions workflow, SonarQube
project configuration, and Kubernetes deployment strategy templates. The
pipeline is designed to stop on lint, test, container, or configured quality
gate failure. Readiness checks support safe traffic switching and Kubernetes
rollout history supports rollback.

The local project artifacts are prepared. The Python launcher could not start
and the Docker daemon is unavailable in this workspace, so Pytest and image
builds could not be run here. A kubectl manifest dry-run could not contact a
cluster API. No new Jenkins, GitHub Actions, SonarQube, or Kubernetes workflow
run has been performed, so this report does not claim successful external build
results, a SonarQube report, a published image, or a running cluster endpoint.
Those evidence items can be added after the corresponding services are
configured and run.
