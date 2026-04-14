"""Singleton model loader for SkyOps serving layer.

ADR-001 Migration Phase 1 — extracted from serving/api.py (2026-04-14 P3).

Thread-safety note: FastAPI + Uvicorn single-worker mode에서는 문제 없음.
Multi-worker/multiprocess 운영 시 각 워커가 독립 인스턴스를 가짐 (의도됨).
"""

from __future__ import annotations

import importlib.util
import pickle
import sys
from pathlib import Path

from .constants import (
    CONFORMAL_PATH,
    IF_MODEL_PATH,
    PROJECT_ROOT,
    XGB_MODEL_PATH,
)


class ModelStore:
    """Lazy-loading singleton for all serving models.

    기존 `_ModelStore` (api.py) 와 API 호환. 앞 언더스코어 제거해 퍼블릭 API.
    """

    _xgb = None
    _if = None
    _rag = None
    _conformal = None

    @classmethod
    def xgb(cls):
        if cls._xgb is None:
            if not XGB_MODEL_PATH.exists():
                raise RuntimeError(f"XGBoost 모델 없음: {XGB_MODEL_PATH}")
            with open(XGB_MODEL_PATH, "rb") as f:
                cls._xgb = pickle.load(f)
        return cls._xgb

    @classmethod
    def isolation_forest(cls):
        if cls._if is None:
            if not IF_MODEL_PATH.exists():
                raise RuntimeError(f"Isolation Forest 모델 없음: {IF_MODEL_PATH}")
            with open(IF_MODEL_PATH, "rb") as f:
                cls._if = pickle.load(f)
        return cls._if

    @classmethod
    def conformal(cls):
        """MAPIE SplitConformalRegressor calibrator (P1 · 2026-04-14).

        analysis/conformal_calibration.py에서 생성. 없으면 None 반환(fallback).
        """
        if cls._conformal is None and CONFORMAL_PATH.exists():
            try:
                with open(CONFORMAL_PATH, "rb") as f:
                    cls._conformal = pickle.load(f)
            except Exception as e:
                print(f"⚠️  Conformal calibrator 로드 실패 ({e}) → fallback to point estimate")
                cls._conformal = None
        return cls._conformal

    @classmethod
    def rag(cls):
        """Lazy-load RAG chain from serving/05_rag_chain.py.

        [2026-04-14 P3] 절대경로 사용 — router에서 호출해도 경로 안정.
        """
        if cls._rag is None:
            serving_dir = str(PROJECT_ROOT / "serving")
            if serving_dir not in sys.path:
                sys.path.insert(0, serving_dir)
            project_dir = str(PROJECT_ROOT)
            if project_dir not in sys.path:
                sys.path.insert(0, project_dir)

            rag_path = PROJECT_ROOT / "serving" / "05_rag_chain.py"
            spec = importlib.util.spec_from_file_location(
                "rag_chain_module", rag_path
            )
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            cls._rag = mod.rag_chain
        return cls._rag
