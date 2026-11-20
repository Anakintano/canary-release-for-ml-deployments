# Safer ML releases, one canary at a time

**What happens when a new model looks good in testing but breaks after deployment?**

This project explores that problem with a support-ticket classifier and a canary release: send a small share of traffic to a new version, compare it with the stable version, and decide whether to promote it or roll it back.

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?style=flat-square&logo=scikitlearn&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white)
![Jenkins](https://img.shields.io/badge/Jenkins-D24939?style=flat-square&logo=jenkins&logoColor=white)
![Kubernetes](https://img.shields.io/badge/Kubernetes-326CE5?style=flat-square&logo=kubernetes&logoColor=white)
![Prometheus](https://img.shields.io/badge/Prometheus-E6522C?style=flat-square&logo=prometheus&logoColor=white)
![Grafana](https://img.shields.io/badge/Grafana-F46800?style=flat-square&logo=grafana&logoColor=white)

## Follow the release

**1. Start with a working experience.** A user submits a ticket and gets a category and confidence score. The demo uses synthetic ticket data.

![A support ticket classified as billing](pictures/demo-page.png)

**2. Establish the baseline.** Before comparing a new release, the dashboard shows the stable version's traffic, errors, latency and confidence.

![Stable version dashboard](pictures/grafana-stable-only.png)

**3. Try a healthy canary.** The new version receives a small share of test traffic. Its error rate and confidence remain close to the stable version.

![Healthy canary compared with stable](pictures/grafana-healthy-canary.png)

**4. Introduce a fault.** An intentionally broken tokenizer causes errors and lower confidence in the canary while the stable version stays healthy.

![Faulty canary showing rising errors and falling confidence](pictures/grafana-bad-canary.png)

**5. See the user impact.** A ticket containing a currency symbol exposes the faulty version's error.

![The faulty canary returning an error](pictures/demo-page-canary-error.png)

## What was tested

In a local, native test on 15 November 2026:

- **6 unit tests passed.** A normally trained model reached **93.4%** accuracy on a synthetic held-out set; an intentionally degraded model scored **16.3%** and failed the accuracy gate.
- The canary checker returned **PROMOTE** for the healthy version after an 80-second shortened watch, and **ROLLBACK** for the faulty version after 60 seconds. The stable API was healthy after the faulty local canary was removed.

These are local test results, not production outcomes. The screenshots show the native demonstration; the full Jenkins-to-Kubernetes deployment, traffic routing, and automatic rollback have **not yet been verified end to end**. The data is synthetic, so the accuracy is not a claim about real customer tickets.

## How it works

A Jenkins pipeline is designed to test and build a model, deploy a canary alongside the stable version, and use Prometheus metrics-errors, latency and confidence-to decide whether to promote or roll back. Grafana makes those signals visible.

The documented local setup uses Docker Desktop, kind and kubectl. A public GitHub repository URL is needed for the Jenkins job.

```bash
bash start.sh
```

**[Explore the complete setup, architecture and test plan ->](SETUP.md)**

Have an idea for making the release safer or the demo easier to use? Open an issue or start a discussion.
