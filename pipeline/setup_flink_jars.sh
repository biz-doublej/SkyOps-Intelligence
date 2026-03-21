#!/usr/bin/env bash
# =============================================================
# SkyOps Intelligence — PyFlink Kafka 커넥터 JAR 다운로드
# =============================================================
# 사용법:
#   chmod +x pipeline/setup_flink_jars.sh
#   ./pipeline/setup_flink_jars.sh
#
# 다운로드 후 FLINK_HOME/lib/ 에 자동 배치됩니다.
# PyFlink 설치 위치는 `python -c "import pyflink; print(pyflink.__file__)"` 로 확인.
# =============================================================

set -e

FLINK_VERSION="1.18.1"
SCALA_VERSION="2.12"

# PyFlink 설치 경로 자동 탐색
PYFLINK_LIB=$(python -c "import pyflink; import os; print(os.path.join(os.path.dirname(pyflink.__file__), 'lib'))" 2>/dev/null || echo "")

if [ -z "$PYFLINK_LIB" ]; then
    echo "[ERROR] PyFlink가 설치되지 않았습니다. 먼저 실행하세요:"
    echo "  pip install apache-flink==${FLINK_VERSION}"
    exit 1
fi

echo "[INFO] PyFlink lib 경로: $PYFLINK_LIB"

# JAR 목록 (Flink Kafka 커넥터 + 의존성)
JARS=(
    "https://repo1.maven.org/maven2/org/apache/flink/flink-sql-connector-kafka/${FLINK_VERSION}/flink-sql-connector-kafka-${FLINK_VERSION}.jar"
)

echo "[INFO] JAR 다운로드 시작..."
for url in "${JARS[@]}"; do
    filename=$(basename "$url")
    dest="$PYFLINK_LIB/$filename"
    if [ -f "$dest" ]; then
        echo "[SKIP] 이미 존재: $filename"
    else
        echo "[DOWN] $filename"
        curl -fsSL -o "$dest" "$url"
        echo "[OK]   저장 완료: $dest"
    fi
done

echo ""
echo "=================================================="
echo "✅ JAR 설정 완료!"
echo "   이제 flink_processor.py 를 실행할 수 있습니다."
echo "=================================================="
