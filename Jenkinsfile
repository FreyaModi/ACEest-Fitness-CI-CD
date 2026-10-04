// Jenkins BUILD pipeline for ACEest Fitness & Gym.
// Pulls the latest code from GitHub and performs a clean build in a controlled
// environment: lint -> unit tests -> Docker image build -> containerised tests
// -> smoke test of the runtime image.
pipeline {
    agent any

    options {
        skipDefaultCheckout(true)
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '20'))
        disableConcurrentBuilds()
    }

    triggers {
        // GitHub webhooks cannot reach a local Jenkins, so poll for new commits.
        pollSCM('H/2 * * * *')
    }

    environment {
        IMAGE_NAME = 'aceest-fitness'
        IMAGE_TAG = "${env.BUILD_NUMBER}"
        SMOKE_CONTAINER = "aceest-smoke-${env.BUILD_NUMBER}"
    }

    stages {
        stage('Checkout') {
            steps {
                cleanWs()
                checkout scm
                sh 'git log -1 --pretty="Building commit %h: %s (%an)"'
            }
        }

        stage('Setup Environment') {
            steps {
                sh '''
                    python3 --version
                    python3 -m venv .venv
                    .venv/bin/pip install --quiet --upgrade pip
                    .venv/bin/pip install --quiet -r requirements-dev.txt
                '''
            }
        }

        stage('Lint') {
            steps {
                sh '''
                    .venv/bin/python -m compileall -q -x '/\\.(git|venv)/' .
                    .venv/bin/flake8 . --count --show-source --statistics
                '''
            }
        }

        stage('Unit Tests') {
            steps {
                sh '''
                    mkdir -p reports
                    .venv/bin/pytest -v --cov --cov-report=term-missing \
                        --cov-report=xml:reports/coverage.xml --junitxml=reports/junit.xml
                '''
            }
            post {
                always {
                    junit testResults: 'reports/junit.xml', allowEmptyResults: true
                }
            }
        }

        stage('Docker Build') {
            steps {
                sh '''
                    docker version --format 'Docker engine {{.Server.Version}}'
                    docker build --target test -t "$IMAGE_NAME:test-$IMAGE_TAG" .
                    docker build -t "$IMAGE_NAME:$IMAGE_TAG" -t "$IMAGE_NAME:latest" .
                    docker images "$IMAGE_NAME"
                '''
            }
        }

        stage('Container Tests') {
            steps {
                sh 'docker run --rm "$IMAGE_NAME:test-$IMAGE_TAG"'
            }
        }

        stage('Smoke Test') {
            steps {
                sh '''
                    docker run -d --name "$SMOKE_CONTAINER" "$IMAGE_NAME:$IMAGE_TAG"
                    status=starting
                    for i in $(seq 1 30); do
                        status=$(docker inspect -f '{{.State.Health.Status}}' "$SMOKE_CONTAINER")
                        [ "$status" = "healthy" ] && break
                        sleep 2
                    done
                    echo "Container health: $status"
                    test "$status" = "healthy"
                    docker exec "$SMOKE_CONTAINER" python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:5000/health').read().decode())"
                '''
            }
        }
    }

    post {
        always {
            sh '''
                mkdir -p reports
                docker logs "$SMOKE_CONTAINER" > reports/smoke-container.log 2>&1 || true
                docker rm -f "$SMOKE_CONTAINER" || true
                docker rmi "$IMAGE_NAME:test-$IMAGE_TAG" || true
            '''
            archiveArtifacts artifacts: 'reports/**', allowEmptyArchive: true
        }
        success {
            echo "BUILD SUCCESSFUL: image ${env.IMAGE_NAME}:${env.IMAGE_TAG} built and verified."
        }
        failure {
            echo 'BUILD FAILED: check the stage logs above.'
        }
        cleanup {
            cleanWs()
        }
    }
}
