// Release pipeline. A merged PR that changes VERSION ships that version as a 10% canary;
// live Prometheus metrics decide promote or rollback. No manual step.
// Needs on the Jenkins controller: docker, kubectl (+ kind locally), python with selenium, chromium.
// Env from the controller: INGRESS_URL (required), REGISTRY (empty = local kind cluster).
pipeline {
  agent any
  triggers { pollSCM('* * * * *') }
  options { disableConcurrentBuilds() }

  stages {
    stage('Build') {
      steps {
        script {
          env.VERSION = readFile('VERSION').trim()
          env.IMAGE = (env.REGISTRY ? "${env.REGISTRY}/" : '') + "tickets-api:${env.VERSION}"
          def stable = sh(returnStdout: true, script: "kubectl get deploy tickets-stable -o jsonpath='{.spec.template.spec.containers[0].image}' 2>/dev/null || true").trim()
          // bootstrap: nothing runs yet, so this version becomes stable directly.
          // skip: this version is already stable (e.g. a README-only commit).
          env.MODE = !stable ? 'bootstrap' : (stable == env.IMAGE ? 'skip' : 'canary')
          echo "Release ${env.IMAGE}, stable is '${stable}', mode ${env.MODE}"
        }
        sh 'docker build --target base -t tickets-base .'
      }
    }

    stage('Unit tests') {
      steps { sh 'docker build --target test .' }
    }

    stage('Train') {
      steps {
        sh '''
          docker build --target train -t tickets-train:$VERSION .
          mkdir -p out
          docker run --rm tickets-train:$VERSION cat model/metrics.json > out/metrics.json
          cat out/metrics.json
        '''
      }
    }

    stage('Accuracy gate') {
      steps {
        // Baseline = metrics.json inside the running stable image; 0 on the very first release.
        sh '''
          kubectl exec deploy/tickets-stable -- cat model/metrics.json > out/stable_metrics.json 2>/dev/null \
            || echo '{"accuracy": 0}' > out/stable_metrics.json
          python ml/gate.py out/metrics.json out/stable_metrics.json
        '''
      }
    }

    stage('Push image') {
      steps {
        sh '''
          # Reuses the cached train stage, so the shipped model is the one the gate just checked.
          # --provenance=false keeps a plain single-platform image, which `kind load` handles reliably.
          docker build --provenance=false -t "$IMAGE" .
          if [ -n "$REGISTRY" ]; then docker push "$IMAGE"; else kind load docker-image "$IMAGE" --name canary-demo; fi
        '''
      }
    }

    stage('Deploy canary') {
      when { expression { env.MODE != 'skip' } }
      steps {
        script {
          def track = env.MODE == 'bootstrap' ? 'stable' : 'canary'
          sh "sed 's|__IMAGE__|${env.IMAGE}|' k8s/${track}.yaml | kubectl apply -f -"
          sh "kubectl rollout status deploy/tickets-${track} --timeout=180s"
        }
      }
    }

    stage('Selenium smoke') {
      when { expression { env.MODE == 'canary' } }
      steps { sh 'BASE_URL="$INGRESS_URL" python tests/smoke_selenium.py' }
    }

    stage('Canary analysis') {
      when { expression { env.MODE == 'canary' } }
      steps {
        sh '''
          kubectl port-forward svc/prometheus 9090:9090 >/dev/null 2>&1 &
          trap "kill $!" EXIT
          sleep 3
          python scripts/canary_check.py http://localhost:9090
        '''
      }
    }

    stage('Promote') {
      when { expression { env.MODE == 'canary' } }
      steps {
        sh '''
          kubectl set image deploy/tickets-stable api="$IMAGE"
          kubectl rollout status deploy/tickets-stable --timeout=180s
          kubectl annotate ingress tickets-canary nginx.ingress.kubernetes.io/canary-weight=0 --overwrite
          kubectl scale deploy/tickets-canary --replicas=0
        '''
      }
    }
  }

  post {
    failure {
      // Rollback: stable was never touched, so taking the canary out of traffic is enough.
      sh '''
        kubectl annotate ingress tickets-canary nginx.ingress.kubernetes.io/canary-weight=0 --overwrite || true
        kubectl scale deploy/tickets-canary --replicas=0 || true
        echo "RELEASE STOPPED: $IMAGE gets no traffic, stable unchanged"
      '''
    }
  }
}
