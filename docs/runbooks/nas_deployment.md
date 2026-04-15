# Runbook — Synology ARM64 + Cloudflare Tunnel 배포 (P8-NAS · 2026-04-16)

> 사용자 환경: Synology ARM64 + Docker Compose 설치됨 + Cloudflare Tunnel + scp/OpenSSH

## 🎯 배포 전략 (최단 경로)

```
  GitHub Actions (release.yml)  →  ghcr.io/biz-doublej/skyops-*:v2.1.1  (arm64 포함 multi-arch)
                                                │
                                                ▼
  NAS (Synology ARM64) ──── docker pull ────▶ 컨테이너 기동
                                                │
                                                ▼
  Cloudflare Tunnel ────────────────────▶ https://skyops.<your-domain>
```

**핵심**: GHCR 에서 이미지 pull → NAS 에서 직접 빌드 불필요 (ARM 에서 빌드는 30분+).

---

## STEP-by-STEP

### ① 로컬 (PowerShell) · Git push + Release 태그

```powershell
cd "C:\Users\jaewo\Desktop\SkyOps Intelligence"

# P0~P8 전체 push
git push origin dev

# Release 태그 → GHA release.yml 이 멀티아키(amd64+arm64) 이미지 + 서명 + SBOM 자동 생성
git tag -a v2.1.1 -m "SkyOps Intelligence P0~P8 enterprise platform"
git push origin v2.1.1

# GitHub Actions 진행 확인
gh run list --workflow=release.yml --limit 3
# 또는 브라우저: https://github.com/biz-doublej/SkyOps-Intelligence/actions
```

→ 약 **8~12분** 후 `ghcr.io/biz-doublej/skyops-api:v2.1.1` + `skyops-dashboard:v2.1.1` 둘 다 준비됨.

### ② Cloudflare Zero Trust 설정 (브라우저, 약 3분)

1. https://one.dash.cloudflare.com/ 로그인
2. 좌측 **Networks** → **Tunnels** → **Create a tunnel**
3. Tunnel name: `skyops-nas` → **Save**
4. 환경 선택: **Docker** → `docker run cloudflared ... --token eyJ...` 명령어의 **token 값**만 복사
5. **Public Hostnames** 탭 → **Add a public hostname**:
   - Subdomain: `skyops` (또는 원하는 이름)
   - Domain: 본인 소유 도메인
   - Type: `HTTP`
   - URL: `dashboard:3000`
   - **Save hostname**
6. (선택) API도 노출하려면 추가 public hostname:
   - Subdomain: `api-skyops`
   - URL: `api:8000`
   - **Additional application settings → Access** → 본인 이메일만 허용하는 Access policy 추가 (권장)

### ③ 로컬 (PowerShell) · `.env.nas` 준비

```powershell
cd "C:\Users\jaewo\Desktop\SkyOps Intelligence"

# 템플릿 복사
Copy-Item .env.nas.example .env.nas

# 편집 — 최소 2개 값만 채우면 됨
notepad .env.nas
# CLOUDFLARE_TUNNEL_TOKEN=eyJ...  (위에서 복사한 값)
# GRAFANA_ADMIN_PASSWORD=your-strong-password
```

### ④ 로컬 → NAS · 파일 전송 (scp, 10~15분)

NAS 에 먼저 디렉토리 생성:

```powershell
# NAS IP / USER 환경변수화 — 한 번만 설정
$env:NAS_HOST = "192.168.0.100"     # ← 본인 NAS IP 로 치환
$env:NAS_USER = "jaewo"             # ← SSH 계정명

# 디렉토리 생성
ssh ${env:NAS_USER}@${env:NAS_HOST} "mkdir -p /volume1/docker/skyops/{data/models,data/vectordb,data/icao,monitoring}"
```

필수 파일 전송 (PowerShell):

```powershell
cd "C:\Users\jaewo\Desktop\SkyOps Intelligence"

# 1) Compose + env (가장 작음)
scp docker-compose.nas.yml .env.nas ${env:NAS_USER}@${env:NAS_HOST}:/volume1/docker/skyops/

# 2) Monitoring (Prometheus + Grafana 설정)
scp -r monitoring/prometheus monitoring/grafana monitoring/otel-collector-config.yaml ${env:NAS_USER}@${env:NAS_HOST}:/volume1/docker/skyops/monitoring/

# 3) 모델 파일 (수십 MB ~ 수백 MB)
scp data/models/*.pkl ${env:NAS_USER}@${env:NAS_HOST}:/volume1/docker/skyops/data/models/

# 4) ChromaDB (~50-200 MB)
scp -r data/vectordb/* ${env:NAS_USER}@${env:NAS_HOST}:/volume1/docker/skyops/data/vectordb/

# 5) ICAO corpus (RAG 용, 수 MB)
scp -r data/icao/corpus ${env:NAS_USER}@${env:NAS_HOST}:/volume1/docker/skyops/data/icao/
```

### ⑤ NAS (SSH) · docker-compose 수정 + pull + 기동

```bash
# NAS SSH 접속
ssh ${env:NAS_USER}@${env:NAS_HOST}   # (PowerShell 에서 그대로 실행 가능)
# 접속 후 — bash 쉘:

cd /volume1/docker/skyops

# GHCR 에서 이미지 pull (ARM64 자동 선택)
docker pull ghcr.io/biz-doublej/skyops-api:v2.1.1
docker pull ghcr.io/biz-doublej/skyops-dashboard:v2.1.1
# (pull 실패 시 → GHA release 아직 진행 중일 수 있음. gh run watch 로 확인)

# compose 의 image 참조를 GHCR 로 변경 (한 줄 sed)
sed -i 's|image: skyops/api:nas-2.1.1|image: ghcr.io/biz-doublej/skyops-api:v2.1.1|g' docker-compose.nas.yml
sed -i 's|image: skyops/dashboard:nas-2.1.1|image: ghcr.io/biz-doublej/skyops-dashboard:v2.1.1|g' docker-compose.nas.yml

# build 섹션 주석 처리 (NAS 에서 빌드 안 함)
# 수동 편집 또는 아래 한 줄:
sed -i '/build:/,/dockerfile: Dockerfile\./d' docker-compose.nas.yml

# 기동 (Cloudflare Tunnel 포함)
docker compose -f docker-compose.nas.yml --env-file .env.nas --profile public up -d

# 상태 확인
docker compose -f docker-compose.nas.yml ps
docker compose -f docker-compose.nas.yml logs -f --tail 50 api cloudflared
# Ctrl-C 로 로그 종료 (컨테이너는 실행 유지)
```

### ⑥ 동작 확인

```bash
# NAS 내부에서 직접
curl -s http://localhost:8000/health | head -c 300
# → {"status":"ok","version":"2.1.1",...}

curl -s http://localhost:3000/ | head -c 100
# → HTML 응답 (Next.js dashboard)

# Cloudflare Tunnel 연결 확인
docker logs skyops-cloudflared --tail 20 | grep "Registered tunnel connection"
# → 여러 개 나오면 성공
```

브라우저에서:
- **https://skyops.your-domain.com** → Dashboard 7 페이지
- **https://api-skyops.your-domain.com/docs** (설정했다면) → Swagger UI
- **http://<NAS-IP>:3001** (LAN 내부) → Grafana SLO 대시보드

### ⑦ 학습 + 모델 업데이트 사이클 (본인 PC)

```powershell
# 본인 GPU PC — 학습 (30분 이내)
cd "C:\Users\jaewo\Desktop\SkyOps Intelligence"

# XGBoost 재학습 (데이터 바뀌었을 때)
python tasks.py train-quick         # 5 trials ~1분
python tasks.py conformal           # 90% coverage interval

# Per-phase IF 재학습 (feedback 데이터 누적 시)
python tasks.py per-phase-if        # 7 phases × 3분 = ~20분

# NAS 로 새 모델 전송
scp data/models/xgboost_best.pkl ${env:NAS_USER}@${env:NAS_HOST}:/volume1/docker/skyops/data/models/
scp data/models/isolation_forest_*.pkl ${env:NAS_USER}@${env:NAS_HOST}:/volume1/docker/skyops/data/models/
scp data/models/conformal_calibrator.pkl ${env:NAS_USER}@${env:NAS_HOST}:/volume1/docker/skyops/data/models/

# NAS 에 reload signal (P6-C hot-reload)
ssh ${env:NAS_USER}@${env:NAS_HOST} "touch /volume1/docker/skyops/data/models/.reload_signal"
# → 다음 /predict/delay 요청 시 자동으로 새 모델 로드됨 (재시작 불필요)
```

### ⑧ 일상 운영 명령어

```powershell
# 상태 확인 (PowerShell 에서 ssh로)
ssh ${env:NAS_USER}@${env:NAS_HOST} "cd /volume1/docker/skyops && docker compose -f docker-compose.nas.yml ps"

# 로그 보기
ssh ${env:NAS_USER}@${env:NAS_HOST} "cd /volume1/docker/skyops && docker compose -f docker-compose.nas.yml logs -f --tail 100 api"

# 재시작
ssh ${env:NAS_USER}@${env:NAS_HOST} "cd /volume1/docker/skyops && docker compose -f docker-compose.nas.yml restart api"

# 전체 다운
ssh ${env:NAS_USER}@${env:NAS_HOST} "cd /volume1/docker/skyops && docker compose -f docker-compose.nas.yml down"

# 리소스 확인 (NAS 성능 체크)
ssh ${env:NAS_USER}@${env:NAS_HOST} "docker stats --no-stream"

# 새 이미지 릴리스 후 업그레이드
ssh ${env:NAS_USER}@${env:NAS_HOST} @'
cd /volume1/docker/skyops
docker pull ghcr.io/biz-doublej/skyops-api:v2.1.2
docker pull ghcr.io/biz-doublej/skyops-dashboard:v2.1.2
sed -i 's/v2.1.1/v2.1.2/g' docker-compose.nas.yml
docker compose -f docker-compose.nas.yml up -d
'@
```

---

## ⚠️ ARM64 Synology 특이사항

| 이슈 | 해결 |
|------|------|
| RAM 2GB 이하 모델 (DS220j, DS418j) | `docker-compose.nas.yml` 에서 Prometheus + Grafana 블록 주석 처리 — ~1GB 절약 |
| Cloudflared 가 ARM 헤더 오류 | `cloudflare/cloudflared:latest` 는 ARM64 지원 (buildx manifest 자동). 구버전 태그 쓰지 말 것 |
| `sed -i` Synology 에 없는 경우 | `vim` 또는 File Station GUI 로 직접 수정 |
| Dockerfile 빌드 시 torch 설치 실패 | GHCR pull 사용 권장 — ARM 에서 sentence-transformers 네이티브 빌드는 1시간+ |
| Port 443 접근 불가 (공유기) | Cloudflare Tunnel 은 **outbound 443 만 쓰므로** 포트포워딩 불필요 |

## 🔒 보안 체크리스트

- [ ] `.env.nas` 가 NAS 에만 있고 Git 에 commit 안 됨 (`.gitignore` 에 포함됨)
- [ ] Cloudflare Tunnel Access policy 로 API endpoint 보호 (관리자 이메일만)
- [ ] NAS 포트포워딩 없이 Tunnel 만 사용 (공유기 80/443 닫힘)
- [ ] Grafana admin 비밀번호 `skyops` 아닌 강한 값
- [ ] SSH keypair 인증 (password 로그인 비활성화)
- [ ] `docker pull` 시 cosign 서명 검증 (선택):
  ```bash
  cosign verify --certificate-oidc-issuer=https://token.actions.githubusercontent.com \
    --certificate-identity-regexp="https://github.com/biz-doublej/SkyOps-Intelligence/.*" \
    ghcr.io/biz-doublej/skyops-api:v2.1.1
  ```

## 🎯 검증 체크리스트

배포 후 다음이 모두 ✅ 이어야 완료:

- [ ] `docker compose ps` → api/dashboard/redis/prometheus/grafana/cloudflared all `healthy`
- [ ] `curl http://localhost:8000/health` → status ok + version 2.1.1
- [ ] `docker logs skyops-cloudflared | grep "Registered tunnel"` → 4 connections
- [ ] 브라우저에서 https://skyops.<domain> → Dashboard 렌더링 정상
- [ ] Dashboard 에서 /notam 페이지 열람 (빈 리스트여도 UI 정상)
- [ ] Grafana http://NAS:3001 → SLO 대시보드 9개 패널 로드
- [ ] `docker stats` → total RAM < 2GB
