"""SkyOps Feast — materialize offline → online (P6-A · 2026-04-15).

Pushes the latest rows from offline parquet sources into the online
Redis store. Should be called:
  - after every retraining batch (nightly)
  - after seed_* produces new parquet files

Run:
    python -m feature_store.materialize
    python -m feature_store.materialize --lookback-days 30
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lookback-days", type=int, default=7,
                        help="Materialize rows from N days ago (default 7)")
    parser.add_argument("--end", type=str, default=None,
                        help="ISO end timestamp (default: now UTC)")
    args = parser.parse_args()

    try:
        from feast import FeatureStore
    except ImportError:
        print("❌ feast 미설치. `pip install -e \".[feast]\"` 실행 후 재시도")
        return 1

    fs = FeatureStore(repo_path=str(REPO_DIR))

    end = (datetime.fromisoformat(args.end.replace("Z", "+00:00"))
           if args.end else datetime.now(timezone.utc))
    start = end - timedelta(days=args.lookback_days)

    print("=" * 65)
    print(f"  Feast materialize  {start.isoformat()}  →  {end.isoformat()}")
    print("=" * 65)

    # materialize_incremental은 feature_view별 last-materialized 타임스탬프 이후부터.
    # 명시적 window는 materialize() 사용.
    fs.materialize(start_date=start, end_date=end)

    print("\n✅ Online store populated (Redis db=1)")
    print("   Verify:  redis-cli -n 1 keys 'skyops_intelligence*' | head")
    return 0


if __name__ == "__main__":
    sys.exit(main())
