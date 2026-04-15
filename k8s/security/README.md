# SkyOps k8s Security Bundle (P7-F · 2026-04-15)

Strategic Review #8 follow-through. Production-grade k8s hardening
that complements the Argo Rollouts canary in `k8s/rollouts/`.

## 📂 Files

| File | Effect |
|------|--------|
| `namespace-psa.yaml` | Promotes `skyops` namespace to **Pod Security: restricted** |
| `network-policies.yaml` | Default-deny + explicit allow rules per pod |

## 🔒 Pod Security Standards

`restricted` profile enforces:
- `runAsNonRoot: true`
- `allowPrivilegeEscalation: false`
- Drop ALL capabilities
- `seccompProfile.type: RuntimeDefault`
- No `hostNetwork` / `hostPID` / `hostIPC`
- No host paths

The Rollout in `k8s/rollouts/api-rollout.yaml` already complies. Apply
the namespace label to enforce cluster-wide.

## 🌐 NetworkPolicy

Zero-trust within the namespace:
- Default deny all (ingress + egress)
- API: ingress from Traefik + dashboard + Prometheus; egress to Redis + vLLM + OTel + DNS
- Dashboard: ingress from Traefik; egress to API + DNS only
- Redis: ingress from API only; egress to DNS only

This requires a CNI that supports NetworkPolicy (Calico, Cilium, Weave —
NOT plain flannel). For Docker Desktop k8s, Calico install:

```bash
curl https://raw.githubusercontent.com/projectcalico/calico/v3.27.0/manifests/tigera-operator.yaml -O
kubectl apply -f tigera-operator.yaml
```

## 🚀 Apply

```bash
kubectl apply -f k8s/security/namespace-psa.yaml
kubectl apply -f k8s/security/network-policies.yaml
kubectl apply -f k8s/rollouts/    # Argo Rollouts canary
```

## 🧪 Verify

```bash
kubectl describe namespace skyops | grep pod-security
kubectl get netpol -n skyops
kubectl auth can-i create pods --as=system:serviceaccount:skyops:default -n skyops
# Try to schedule a privileged pod — should be REJECTED:
kubectl run nginx --image=nginx --privileged -n skyops
# Error from server: pods "nginx" is forbidden: violates PodSecurity "restricted:latest"
```

## 🧨 Image Scanning (CI gate)

Add to `.github/workflows/ci.yml`:

```yaml
- name: Trivy image scan
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: skyops/api:${{ github.sha }}
    severity: CRITICAL,HIGH
    exit-code: 1
    ignore-unfixed: true
```
