# Runbook — Supply Chain Security (P8-G · 2026-04-15)

## 🎯 목표

SkyOps가 배포하는 모든 컨테이너 이미지는 다음을 만족한다:
1. **서명 (signed)** — Sigstore cosign keyless via GitHub OIDC
2. **SBOM 첨부** — SPDX-JSON + CycloneDX (cosign attestation)
3. **취약점 없음** — Trivy CRITICAL/HIGH 0 findings
4. **검증 가능** — 배포 파드는 서명 미달성 시 거부 (Kyverno/Gatekeeper)

## 🔨 로컬 빌드 + 서명 (릴리스 시뮬레이션)

```bash
# 1. 빌드
docker build -f Dockerfile.api -t ghcr.io/biz-doublej/skyops-api:v2.1.1 .

# 2. SBOM 생성 (syft)
syft ghcr.io/biz-doublej/skyops-api:v2.1.1 \
  -o spdx-json=sbom-api.spdx.json \
  -o cyclonedx-json=sbom-api.cdx.json

# 3. Trivy 스캔
trivy image --severity CRITICAL,HIGH --exit-code 1 --ignore-unfixed \
  ghcr.io/biz-doublej/skyops-api:v2.1.1

# 4. 푸시 (GHCR 인증 선행)
docker push ghcr.io/biz-doublej/skyops-api:v2.1.1

# 5. Sigstore 서명 (OIDC, key 파일 불필요)
COSIGN_EXPERIMENTAL=1 cosign sign --yes \
  ghcr.io/biz-doublej/skyops-api:v2.1.1

# 6. SBOM attestation 첨부
COSIGN_EXPERIMENTAL=1 cosign attest --yes \
  --predicate sbom-api.spdx.json \
  --type spdxjson \
  ghcr.io/biz-doublej/skyops-api:v2.1.1
```

## ✅ 배포 전 검증 (CI/CD gate)

```bash
# 서명 검증
COSIGN_EXPERIMENTAL=1 cosign verify \
  --certificate-oidc-issuer=https://token.actions.githubusercontent.com \
  --certificate-identity-regexp="https://github.com/biz-doublej/SkyOps-Intelligence/.*" \
  ghcr.io/biz-doublej/skyops-api:v2.1.1

# SBOM attestation 다운로드 + 검증
cosign download attestation \
  ghcr.io/biz-doublej/skyops-api:v2.1.1 \
  | jq -r '.payload' | base64 -d | jq '.predicate' > downloaded-sbom.json
```

## 🛡️ Kyverno 정책 (배포 gate)

```yaml
# k8s/security/kyverno-verify-images.yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-signed-images-skyops
spec:
  validationFailureAction: Enforce
  background: false
  webhookTimeoutSeconds: 30
  rules:
    - name: verify-skyops-images-signed
      match:
        any:
          - resources:
              kinds: [Pod]
              namespaces: [skyops]
      verifyImages:
        - imageReferences:
            - "ghcr.io/biz-doublej/skyops-*:*"
          mutateDigest: true
          verifyDigest: true
          attestors:
            - entries:
                - keyless:
                    subject: "https://github.com/biz-doublej/SkyOps-Intelligence/*"
                    issuer: "https://token.actions.githubusercontent.com"
```

적용:
```bash
kubectl apply -f k8s/security/kyverno-verify-images.yaml
# 이후 서명 없는 이미지 사용 시 파드 생성 거부됨
```

## 📋 SBOM 활용

### 취약점 재스캔
새 CVE 가 공개되면 SBOM 으로 영향 이미지 빠르게 찾기:
```bash
# 전 릴리스 SBOM을 grype 로 재검사
grype sbom:sbom-api.spdx.json
```

### 라이선스 감사
```bash
syft ghcr.io/biz-doublej/skyops-api:v2.1.1 -o json \
  | jq -r '.artifacts[] | [.name, .version, (.licenses[0] // "")] | @tsv'
# → 패키지 · 버전 · 라이선스 (GPL 등 금기 라이선스 검출)
```

## 🚨 유출 이미지 대응

누군가 내부 이미지를 외부 registry 에 pull 했을 때:
1. 원본 tag destroy (GHCR → package → delete)
2. Kyverno 정책 업데이트 — 유출 태그 denylist 추가
3. `kubectl rollout restart` — 클러스터가 pull 재시도 시 차단됨
4. FAA / KAC 파트너 통지 (NDA 조건상)

## 🔑 keyless 장점

- 비밀 키 관리 불필요 (OIDC 토큰 exchange)
- GitHub Actions 워크플로우 identity 가 signature 에 박힘
- Rekor transparency log 에 자동 기록 → 부인 방지

## 📅 정기 감사

- 월 1회 — 모든 활성 tag 재검증 (서명 + Trivy 재스캔)
- 분기 1회 — SBOM 기반 라이선스 준수 감사
- 반기 1회 — Kyverno 정책 테스트 (negative case)
