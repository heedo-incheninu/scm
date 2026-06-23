"""GSCPI 기반 공급망 위기 시나리오 추천."""

from __future__ import annotations

import os
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import pandas as pd

GSCPI_URL = (
    "https://www.newyorkfed.org/medialibrary/research/interactives/gscpi/downloads/"
    "gscpi_data.xlsx"
)
DEFAULT_CACHE_PATH = Path("data/gscpi_data.xlsx")


@dataclass(frozen=True)
class GscpiRecommendation:
    """GSCPI 최신값과 추천 시나리오."""

    value: float | None
    period: str | None
    status: str
    scenario: str
    multiplier: float
    source: str
    warning: str | None = None


def recommend_scenario(value: float) -> tuple[str, str, float]:
    """GSCPI 값에 따라 상태, 내부 시나리오 키, 위기배수를 추천한다."""

    if value < 0.5:
        return "Normal", "normal", 1.0
    if value < 2.0:
        return "Warning", "moderate", 1.18
    if value < 4.0:
        return "Crisis", "high", 1.8
    return "Extreme", "extreme", 2.2


def _normalise_gscpi_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """New York Fed XLSX의 날짜·값 컬럼명을 표준화한다."""

    if frame.empty:
        raise ValueError("GSCPI 데이터가 비어 있습니다.")

    lower_columns = {str(column).lower().strip(): column for column in frame.columns}
    date_column = next(
        (
            lower_columns[name]
            for name in lower_columns
            if "date" in name or "month" in name or "period" in name
        ),
        frame.columns[0],
    )
    value_column = next(
        (
            column
            for column in frame.columns
            if column != date_column and pd.api.types.is_numeric_dtype(frame[column])
        ),
        None,
    )
    if value_column is None:
        numeric = frame.apply(pd.to_numeric, errors="coerce")
        numeric_columns = [column for column in numeric.columns if column != date_column]
        if not numeric_columns:
            raise ValueError("GSCPI 값 컬럼을 찾을 수 없습니다.")
        value_column = numeric_columns[0]
        frame[value_column] = numeric[value_column]

    result = frame[[date_column, value_column]].rename(
        columns={date_column: "period", value_column: "value"}
    )
    result["value"] = pd.to_numeric(result["value"], errors="coerce")
    result = result.dropna(subset=["value"]).reset_index(drop=True)
    if result.empty:
        raise ValueError("GSCPI 값이 모두 비어 있습니다.")
    return result


def read_gscpi_excel(content: bytes) -> pd.DataFrame:
    """XLSX 바이트에서 GSCPI 시계열을 읽는다."""

    workbook = pd.read_excel(BytesIO(content), sheet_name=None)
    frames = []
    for frame in workbook.values():
        try:
            frames.append(_normalise_gscpi_frame(frame))
        except ValueError:
            continue
    if not frames:
        raise ValueError("GSCPI 시트를 찾을 수 없습니다.")
    return max(frames, key=len)


def fetch_gscpi_data(
    *,
    url: str = GSCPI_URL,
    cache_path: Path = DEFAULT_CACHE_PATH,
    timeout: float = 8.0,
) -> pd.DataFrame:
    """GSCPI XLSX를 다운로드하고 실패 시 캐시를 읽는다."""

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urlopen(url, timeout=timeout) as response:
            content = response.read()
        cache_path.write_bytes(content)
    except (OSError, URLError, TimeoutError):
        if not cache_path.exists():
            raise
        content = cache_path.read_bytes()
    return read_gscpi_excel(content)


def latest_gscpi_recommendation(frame: pd.DataFrame) -> GscpiRecommendation:
    """GSCPI 시계열에서 최신값을 추출해 추천 시나리오를 반환한다."""

    normalised = _normalise_gscpi_frame(frame)
    latest = normalised.iloc[-1]
    value = float(latest["value"])
    status, scenario, multiplier = recommend_scenario(value)
    period = str(latest["period"])[:10]
    return GscpiRecommendation(
        value=value,
        period=period,
        status=status,
        scenario=scenario,
        multiplier=multiplier,
        source=GSCPI_URL,
    )


def load_gscpi_recommendation() -> GscpiRecommendation:
    """앱에서 사용할 GSCPI 추천을 로드한다.

    조회 실패 시에도 앱 흐름이 끊기지 않도록 수동 시나리오 선택 상태를 반환한다.
    """

    if os.getenv("SCM_SKIP_GSCPI") == "1":
        return GscpiRecommendation(
            value=None,
            period=None,
            status="수동 선택",
            scenario="moderate",
            multiplier=1.18,
            source=GSCPI_URL,
            warning="환경변수 SCM_SKIP_GSCPI=1로 자동 조회를 건너뛰었습니다.",
        )
    try:
        frame = fetch_gscpi_data()
        return latest_gscpi_recommendation(frame)
    except Exception as exc:
        return GscpiRecommendation(
            value=None,
            period=None,
            status="수동 선택",
            scenario="moderate",
            multiplier=1.18,
            source=GSCPI_URL,
            warning=f"GSCPI 자동 조회 실패: {exc}",
        )
