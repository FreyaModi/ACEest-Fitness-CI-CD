# Kubernetes deployment examples

These manifests are templates. Replace `DOCKERHUB_USERNAME` and each `VERSION`
placeholder with a published image and tag. Install `ingress-nginx` for canary,
A/B, or shadow traffic handling. `kubectl` access and a running cluster are
needed to apply them.

## Basic rolling update

```sh
kubectl apply -f k8s/base.yaml
kubectl -n aceest set image deployment/aceest-fitness app=DOCKERHUB_USERNAME/aceest-fitness:3.1.0
kubectl -n aceest rollout status deployment/aceest-fitness
kubectl -n aceest rollout undo deployment/aceest-fitness
```

The base Deployment uses Kubernetes RollingUpdate, readiness and liveness
probes, resource bounds, and revision history. `maxUnavailable: 0` keeps the
old pod available while a candidate becomes ready.

## Blue/green

Update image placeholders in `blue-green.yaml`, apply it, and verify the green
deployment using a temporary port-forward or a dedicated test Service. When
ready, switch live traffic and roll back by restoring the selector:

```sh
kubectl apply -f k8s/blue-green.yaml
kubectl -n aceest patch service aceest-fitness --type merge -p '{"spec":{"selector":{"app":"aceest-fitness","slot":"green"}}}'
# Roll back to blue:
kubectl -n aceest patch service aceest-fitness --type merge -p '{"spec":{"selector":{"app":"aceest-fitness","slot":"blue"}}}'
```

## Canary and A/B

Canary routing requires an existing stable ingress for `aceest.local` and the
NGINX Ingress Controller. Apply `canary.yaml` to send 10% of eligible traffic to
the candidate. Increase the weight gradually; rollback by deleting the canary
Ingress and Deployment. For an A/B test, apply `ab-testing.yaml`; requests with
`X-Aceest-Experiment: variant-b` go to variant B. Remove its Ingress to end the
experiment.

## Shadow

Apply `shadow.yaml`, then add the documented mirror annotations to the stable
NGINX Ingress path. User responses continue to come from stable; mirrored
requests reach the shadow Service. Disable mirroring by removing the annotations
and delete the shadow Deployment and Service after analysis.

## Database constraint

The supplied app uses local SQLite. These manifests are strategy examples, not
production data handling. During a rolling update Kubernetes may briefly run
old and new pods together, and each has its own local database. Blue/green,
canary, shadow, and even the rolling-update window must not serve shared
customer writes this way. Before any production rollout or multi-replica
traffic, migrate to a shared database and configure the application to use it.
Do not attach one SQLite file to multiple pods.
