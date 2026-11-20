# Local Jenkins with everything the Jenkinsfile needs. Builds run on the controller itself (one-person demo).
# lts-jdk17 is left floating on purpose: the plugins below install at their latest versions, which need a current core.
FROM jenkins/jenkins:lts-jdk17
USER root
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-venv chromium chromium-driver \
 && rm -rf /var/lib/apt/lists/*
COPY --from=docker:27.3.1-cli /usr/local/bin/docker /usr/local/bin/docker
COPY --from=docker:27.3.1-cli /usr/local/libexec/docker/cli-plugins/docker-buildx /usr/local/libexec/docker/cli-plugins/docker-buildx
RUN curl -fsSLo /usr/local/bin/kubectl https://dl.k8s.io/release/v1.32.0/bin/linux/amd64/kubectl \
 && curl -fsSLo /usr/local/bin/kind https://kind.sigs.k8s.io/dl/v0.25.0/kind-linux-amd64 \
 && chmod +x /usr/local/bin/kubectl /usr/local/bin/kind
RUN python3 -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir selenium==4.27.1
RUN jenkins-plugin-cli --plugins workflow-aggregator git configuration-as-code job-dsl
COPY casc.yaml /usr/share/jenkins/ref/casc.yaml
ENV PATH=/opt/venv/bin:$PATH \
    CHROME_BIN=/usr/bin/chromium \
    CHROMEDRIVER=/usr/bin/chromedriver \
    CASC_JENKINS_CONFIG=/usr/share/jenkins/ref/casc.yaml \
    JAVA_OPTS=-Djenkins.install.runSetupWizard=false
