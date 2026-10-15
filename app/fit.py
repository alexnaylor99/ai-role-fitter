"""Deterministic role-fit calculation (SPEC §5.5). The LLM never computes the fit."""

from __future__ import annotations

import json
import math
from pathlib import Path

from pydantic import ValidationError

from app.contracts import (
    DIMENSION_IDS,
    Assessment,
    ConfigError,
    DimensionFit,
    FitBand,
    RoleFit,
    RoleProfile,
)


def band_for(fit_percent: int) -> FitBand:
    if fit_percent >= 85:
        return "Strong fit"
    if fit_percent >= 70:
        return "Good fit"
    if fit_percent >= 50:
        return "Developing fit"
    return "Early stage"


def compute_role_fit(assessment: Assessment, role: RoleProfile) -> RoleFit:
    dims: list[DimensionFit] = []
    for req in role.requirements:
        score = assessment.score_for(req.dimension_id).score
        gap = max(req.target - score, 0)
        dims.append(
            DimensionFit(
                dimension_id=req.dimension_id,
                score=score,
                target=req.target,
                weight=req.weight,
                fit=min(score / req.target, 1.0),
                gap=gap,
                priority=req.weight * gap,
            )
        )

    total_weight = sum(d.weight for d in dims)
    raw = 100 * sum(d.weight * d.fit for d in dims) / total_weight
    fit_percent = math.floor(raw + 0.5)  # round half up, not banker's rounding

    # Highest priority first; ties broken by weight, then by the rubric's dimension order.
    def order(d: DimensionFit) -> tuple[int, int, int]:
        return (-d.priority, -d.weight, DIMENSION_IDS.index(d.dimension_id))

    dims.sort(key=order)
    return RoleFit(
        role_id=role.id,
        role_title=role.title,
        fit_percent=fit_percent,
        band=band_for(fit_percent),
        dimensions=dims,
        meets=[d.dimension_id for d in dims if d.gap == 0],
        gaps=[d.dimension_id for d in dims if d.gap > 0],
    )


def load_role(path: Path) -> RoleProfile:
    try:
        return RoleProfile.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except FileNotFoundError as exc:
        raise ConfigError("role_profile_missing", f"Role profile not found: {path.name}") from exc
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ConfigError(
            "role_profile_invalid", f"Role profile {path.name} is not valid: {exc}"
        ) from exc
