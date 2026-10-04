# Jenkins controller image for the ACEest CI server.
# Adds Python (for lint/unit tests), the Docker CLI (talks to the docker:dind
# sidecar) and pre-installed plugins. Configuration comes from casc.yaml (JCasC).
FROM jenkins/jenkins:2.580.1-lts-jdk21

USER root
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-venv \
 && rm -rf /var/lib/apt/lists/*

# Docker CLI with the buildx plugin, copied from the official image.
COPY --from=docker:29.8.2-cli /usr/local/bin/docker /usr/local/bin/docker
COPY --from=docker:29.8.2-cli /usr/local/libexec/docker/cli-plugins/docker-buildx \
     /usr/local/libexec/docker/cli-plugins/docker-buildx

USER jenkins

COPY --chown=jenkins:jenkins plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt

# Skip the interactive setup wizard; JCasC creates the admin user and the job.
ENV JAVA_OPTS="-Djenkins.install.runSetupWizard=false" \
    CASC_JENKINS_CONFIG=/var/jenkins_conf/casc.yaml
