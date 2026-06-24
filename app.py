"""비전문가도 사용할 수 있는 해상물류 SCM 리스크 진단 Streamlit 앱."""

from __future__ import annotations

import io
import os
from html import escape
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from scm.analysis import AnalysisResult, analyze_inventory
from scm.comparison import compare_strategies
from scm.constants import SCENARIOS
from scm.copilot import (
    CopilotBrief,
    StrategyEffects,
    build_copilot_brief,
    calculate_strategy_effects,
)
from scm.csv_import import CSV_COLUMNS, load_inventory_csv
from scm.database import initialize_database, load_data
from scm.diagnosis import generate_diagnosis
from scm.gscpi import GscpiRecommendation, load_gscpi_recommendation
from scm.route_risk import RouteRiskResult, calculate_route_concentration
from scm.service_level_allocation import (
    DEFAULT_CARRYING_COST_RATE,
    allocate_service_levels,
    calculate_unprotected_losses,
    service_level_full_budget,
    summarize_service_level_allocation,
)
from scm.whatif import simulate_what_if

DATABASE_PATH = Path("data/scm.db")
CSV_DIRECTORY = Path("csv")
DEFAULT_MODEL = "gpt-5.5"
NAV_ITEMS = [
    ("overview", "🏠", "한눈에 보기", "재고 현황판과 우선 조치"),
    ("data", "🗂️", "데이터 확인", "분석 데이터와 한계"),
    ("scenario", "🌊", "위험 시나리오", "GSCPI와 물류 가정"),
    ("importance", "🎯", "품목 중요도", "매출·수요 변동 3D 분석"),
    ("stock", "📦", "필요 재고", "안전재고와 부족 금액"),
    ("budget", "💸", "예산 추천", "서비스수준별 보호 배분"),
    ("abandoned", "⚠️", "포기 SKU", "미보호 품목과 예상손실"),
    ("compare", "📈", "전략 비교", "What-if 위기 시뮬레이션"),
    ("ai", "🤖", "AI 조언", "재고 의사결정 코파일럿"),
    ("help", "❔", "도움말", "CSV·산식·데이터 한계"),
]
NAV_LABELS = {key: label for key, _icon, label, _description in NAV_ITEMS}

st.set_page_config(
    page_title="해상물류 재고 의사결정 도우미",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    :root {
      --navy: #0f172a;
      --blue: #2563eb;
      --cyan: #06b6d4;
      --amber: #f59e0b;
      --slate: #475569;
      --card: rgba(255, 255, 255, 0.92);
      --line: #dbe7f3;
    }
    .stApp {
      background:
        radial-gradient(circle at 12% 8%, rgba(59, 130, 246, 0.16), transparent 28rem),
        radial-gradient(circle at 86% 14%, rgba(14, 165, 233, 0.14), transparent 26rem),
        linear-gradient(180deg, #f8fbff 0%, #eef5fb 100%);
    }
    .block-container {
      padding-top: 1.2rem;
      padding-bottom: 3rem;
      max-width: 1480px;
    }
    section[data-testid="stSidebar"] {
      background: linear-gradient(180deg, #0f172a 0%, #172554 100%);
      border-right: 1px solid rgba(148, 163, 184, 0.22);
    }
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] .stCaptionContainer {
      color: #e2e8f0 !important;
    }
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] a {
      text-decoration: none;
    }
    [data-testid="stSidebarCollapseButton"] button,
    [data-testid="stSidebarCollapseButton"] svg,
    section[data-testid="stSidebar"] button svg,
    section[data-testid="stSidebar"] button [data-testid="stIconMaterial"] {
      color: #ffffff !important;
      fill: #ffffff !important;
      stroke: #ffffff !important;
    }
    .nav-card {
      display: block;
      padding: .78rem .86rem;
      margin: .42rem 0;
      border-radius: 1rem;
      border: 1px solid rgba(148, 163, 184, 0.24);
      background: rgba(255, 255, 255, 0.06);
      color: #e5eefb !important;
      transition: all .16s ease;
      box-shadow: inset 0 1px 0 rgba(255, 255, 255, .05);
    }
    .nav-card:hover {
      transform: translateY(-1px);
      background: rgba(255, 255, 255, 0.11);
      border-color: rgba(125, 211, 252, 0.7);
    }
    .nav-card.active {
      background: linear-gradient(135deg, rgba(37, 99, 235, .9), rgba(6, 182, 212, .72));
      border-color: rgba(186, 230, 253, .95);
      box-shadow: 0 .75rem 1.7rem rgba(14, 165, 233, .23);
    }
    .nav-title {
      display: block;
      font-weight: 800;
      font-size: .98rem;
      letter-spacing: -.01em;
    }
    .nav-desc {
      display: block;
      margin-top: .18rem;
      color: rgba(226, 232, 240, .78);
      font-size: .78rem;
      line-height: 1.25rem;
    }
    [data-testid="stMetric"] {
      background: var(--card);
      border: 1px solid var(--line);
      padding: 1rem;
      border-radius: 1rem;
      box-shadow: 0 1rem 2rem rgba(15, 23, 42, 0.05);
    }
    .hero {
      position: relative;
      overflow: hidden;
      padding: 1.35rem 1.55rem;
      border-radius: 1.25rem;
      background:
        linear-gradient(120deg, rgba(15, 23, 42, .94), rgba(30, 64, 175, .82)),
        linear-gradient(120deg, #eaf7fb 0%, #f4f8ff 100%);
      border: 1px solid rgba(191, 219, 254, .65);
      margin-bottom: 1rem;
      box-shadow: 0 1.25rem 2.5rem rgba(15, 23, 42, .12);
    }
    .hero:after {
      content: "";
      position: absolute;
      right: -3rem;
      top: -4rem;
      width: 13rem;
      height: 13rem;
      border-radius: 50%;
      background: rgba(34, 211, 238, .22);
    }
    .hero h2 {margin: 0 0 .35rem 0; color: #ffffff; letter-spacing: -.02em;}
    .hero p {margin: 0; color: #cbd5e1;}
    .step-card,
    .insight-card {
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 1rem;
      padding: 1rem;
      min-height: 112px;
      box-shadow: 0 .9rem 1.8rem rgba(15, 23, 42, 0.045);
    }
    .step-card b,
    .insight-card b {color: #0369a1; font-size: 1.05rem;}
    .plain-box {
      background: #fff7ed;
      border: 1px solid #fed7aa;
      border-left: 5px solid var(--amber);
      padding: .9rem 1rem;
      border-radius: .75rem;
      margin: .5rem 0 1rem;
      color: #7c2d12;
    }
    .source-box {
      background: rgba(241, 245, 249, .92);
      border: 1px solid #dbe7f3;
      padding: .9rem 1rem;
      border-radius: .85rem;
      color: #334155;
      font-size: .92rem;
    }
    .chart-note {
      color: #64748b;
      font-size: .9rem;
      margin: -.25rem 0 .65rem;
    }
    .dashboard-header {
      display: flex;
      justify-content: space-between;
      gap: 1rem;
      align-items: flex-start;
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 1.2rem;
      padding: 1.15rem 1.25rem;
      margin: 0 0 1rem;
      box-shadow: 0 1rem 2rem rgba(15, 23, 42, .055);
    }
    .dashboard-header h2 {
      margin: 0 0 .3rem;
      color: #0f172a;
      letter-spacing: -.02em;
    }
    .dashboard-header p {
      margin: 0;
      color: #64748b;
    }
    .header-chip-row {
      display: flex;
      flex-wrap: wrap;
      gap: .45rem;
      justify-content: flex-end;
      max-width: 620px;
    }
    .header-chip {
      background: #eff6ff;
      border: 1px solid #bfdbfe;
      color: #1e40af;
      padding: .45rem .62rem;
      border-radius: 999px;
      font-size: .82rem;
      font-weight: 700;
      white-space: nowrap;
    }
    .panel-card {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 1.1rem;
      padding: 1rem;
      min-height: 100%;
      box-shadow: 0 .85rem 1.75rem rgba(15, 23, 42, .045);
    }
    .panel-card h4 {
      color: #0f172a;
      margin: 0 0 .25rem;
    }
    .panel-card p {
      color: #64748b;
      margin: 0 0 .75rem;
      font-size: .9rem;
    }
    .action-item {
      border: 1px solid #e2e8f0;
      border-radius: .9rem;
      padding: .75rem .8rem;
      margin: .6rem 0;
      background: #f8fafc;
    }
    .action-item b {
      color: #0f172a;
    }
    .status-badge {
      display: inline-block;
      border-radius: 999px;
      padding: .16rem .48rem;
      font-size: .75rem;
      font-weight: 800;
      margin-right: .35rem;
    }
    .status-risk {background: #fee2e2; color: #991b1b;}
    .status-watch {background: #fef3c7; color: #92400e;}
    .status-safe {background: #dcfce7; color: #166534;}
    .strategy-mini-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: .75rem;
      margin: .6rem 0 1rem;
    }
    .strategy-mini-card {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: .95rem;
      padding: .8rem;
      box-shadow: 0 .55rem 1.15rem rgba(15, 23, 42, .035);
    }
    .strategy-mini-card span {
      color: #64748b;
      font-size: .78rem;
      font-weight: 700;
    }
    .strategy-mini-card strong {
      display: block;
      color: #0f172a;
      font-size: 1.35rem;
      margin-top: .16rem;
    }
    .grade-grid {
      display: grid;
      grid-template-columns: repeat(9, minmax(0, 1fr));
      gap: .45rem;
      margin: .35rem 0 1rem;
    }
    .grade-card {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: .8rem;
      padding: .65rem .5rem;
      text-align: center;
      box-shadow: 0 .5rem 1rem rgba(15, 23, 42, .035);
    }
    .grade-card b {
      display: block;
      color: #0f172a;
      font-size: .94rem;
    }
    .grade-card span {
      color: #64748b;
      font-size: .8rem;
    }
    .copilot-card {
      background:
        radial-gradient(circle at 95% 8%, rgba(34, 211, 238, .28), transparent 11rem),
        linear-gradient(135deg, #0f172a 0%, #1d4ed8 100%);
      border: 1px solid rgba(191, 219, 254, .55);
      color: #e2e8f0;
      border-radius: 1.15rem;
      padding: 1.05rem 1.15rem;
      box-shadow: 0 1.2rem 2.4rem rgba(15, 23, 42, .18);
      margin: .7rem 0 1rem;
    }
    .copilot-card h3,
    .copilot-card h4 {
      color: #ffffff;
      margin: 0 0 .38rem;
    }
    .copilot-card p {
      margin: .35rem 0;
      color: #dbeafe;
    }
    .copilot-list {
      margin: .55rem 0 0;
      padding-left: 1.15rem;
    }
    .copilot-list li {
      margin: .32rem 0;
      color: #eef6ff;
    }
    .effect-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: .75rem;
      margin: .45rem 0 1rem;
    }
    .effect-card {
      background: #ffffff;
      border: 1px solid #dbeafe;
      border-radius: .95rem;
      padding: .9rem;
      box-shadow: 0 .65rem 1.25rem rgba(15, 23, 42, .04);
    }
    .effect-card span {
      color: #64748b;
      font-weight: 800;
      font-size: .78rem;
    }
    .effect-card strong {
      display: block;
      color: #1d4ed8;
      font-size: 1.45rem;
      margin-top: .2rem;
    }
    .whatif-note {
      background: #eef6ff;
      border: 1px solid #bfdbfe;
      color: #1e3a8a;
      border-radius: .8rem;
      padding: .8rem .95rem;
      margin: .4rem 0 1rem;
    }
    @media (max-width: 900px) {
      .dashboard-header {display: block;}
      .header-chip-row {justify-content: flex-start; margin-top: .8rem;}
      .strategy-mini-grid {grid-template-columns: 1fr;}
      .grade-grid {grid-template-columns: repeat(3, minmax(0, 1fr));}
      .effect-grid {grid-template-columns: 1fr;}
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def ensure_database() -> Path:
    return initialize_database(DATABASE_PATH)


@st.cache_data
def get_database_data(database_path: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    return load_data(database_path)


@st.cache_data
def get_csv_data(content: bytes) -> tuple[pd.DataFrame, pd.DataFrame]:
    return load_inventory_csv(io.BytesIO(content))


@st.cache_data
def run_analysis(
    products: pd.DataFrame,
    sales: pd.DataFrame,
    scenario: str,
    budget_ratio: float,
) -> AnalysisResult:
    return analyze_inventory(products, sales, scenario, budget_ratio)


@st.cache_data
def run_what_if(products: pd.DataFrame, sales: pd.DataFrame, selected_ratio: float) -> pd.DataFrame:
    ratios = sorted({0.1, 0.2, 0.3, 0.5, 0.75, 1.0, float(selected_ratio)})
    return simulate_what_if(products, sales, budget_ratios=ratios)


@st.cache_data
def run_service_level_allocation(
    safety: pd.DataFrame,
    budget_ratio: float,
    carrying_cost_rate: float,
) -> tuple[pd.DataFrame, dict[str, float], float]:
    full_budget = service_level_full_budget(
        safety,
        carrying_cost_rate=carrying_cost_rate,
    )
    budget = full_budget * budget_ratio
    allocation = allocate_service_levels(
        safety,
        budget,
        carrying_cost_rate=carrying_cost_rate,
    )
    allocation = calculate_unprotected_losses(allocation)
    summary = summarize_service_level_allocation(allocation, budget)
    return allocation, summary, full_budget


@st.cache_data(ttl=60 * 60)
def get_gscpi_recommendation() -> GscpiRecommendation:
    return load_gscpi_recommendation()


def render_hero(title: str, description: str) -> None:
    st.markdown(
        f'<div class="hero"><h2>{title}</h2><p>{description}</p></div>',
        unsafe_allow_html=True,
    )


def render_steps() -> None:
    columns = st.columns(4)
    steps = [
        ("1. 데이터 확인", "SKU·판매·리드타임 데이터의 범위와 한계를 봅니다."),
        ("2. 위험 선택", "GSCPI 참고값과 물류 시나리오를 확인합니다."),
        ("3. 보호 수준 결정", "중요 SKU를 90·95·99% 중 어느 수준까지 보호할지 봅니다."),
        ("4. 포기 위험 확인", "미보호 SKU와 예상손실액을 확인합니다."),
    ]
    for column, (title, body) in zip(columns, steps, strict=True):
        column.markdown(
            f'<div class="step-card"><b>{title}</b><p>{body}</p></div>',
            unsafe_allow_html=True,
        )


def render_flow_note(step: str, purpose: str) -> None:
    st.info(f"**{step}** · {purpose}")


def current_page_key() -> str:
    raw_page = st.query_params.get("page", "overview")
    if isinstance(raw_page, list):
        raw_page = raw_page[0] if raw_page else "overview"
    return str(raw_page) if str(raw_page) in NAV_LABELS else "overview"


def render_sidebar_navigation(page_key: str) -> str:
    st.sidebar.markdown("### 메뉴")
    for key, icon, label, description in NAV_ITEMS:
        active = " active" if key == page_key else ""
        st.sidebar.markdown(
            f"""
            <a class="nav-card{active}" href="?page={key}" target="_self">
              <span class="nav-title">{icon} {label}</span>
              <span class="nav-desc">{description}</span>
            </a>
            """,
            unsafe_allow_html=True,
        )
    return NAV_LABELS[page_key]


def format_currency(value: float) -> str:
    return f"₩{value:,.0f}"


def format_percent(value: float) -> str:
    return f"{value:.1%}"


def format_percent_whole(value: float) -> str:
    return f"{value:.0%}"


def get_config_value(key: str, default: str = "") -> str:
    """환경변수 또는 Streamlit Cloud Secrets에서 설정값을 안전하게 읽는다."""

    if os.getenv(key):
        return str(os.getenv(key))
    try:
        if key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        return default
    return default


def prepare_inventory_dashboard(allocation: pd.DataFrame) -> pd.DataFrame:
    """홈 화면용 재고 상태와 미충족 금액을 계산한다."""

    frame = allocation.copy()
    frame["unmet_budget"] = frame["unmet_quantity"] * frame["unit_cost"]
    frame["inventory_status"] = "안정"
    watch_mask = frame["unmet_quantity"] > 0
    risk_mask = watch_mask & (
        (frame["priority_weight"] >= 6) | (frame["fulfillment_rate"] < 0.5)
    )
    frame.loc[watch_mask, "inventory_status"] = "주의"
    frame.loc[risk_mask, "inventory_status"] = "위험"
    status_order = {"위험": 0, "주의": 1, "안정": 2}
    frame["status_order"] = frame["inventory_status"].map(status_order).astype(int)
    return frame


def render_dashboard_header(
    *,
    data_source_label: str,
    scenario: str,
    budget_percent: int,
    product_count: int,
    month_count: int,
) -> None:
    selected = SCENARIOS[scenario]
    analyzed_at = pd.Timestamp.now(tz="Asia/Seoul").strftime("%Y-%m-%d %H:%M")
    st.markdown(
        f"""
        <div class="dashboard-header">
          <div>
            <h2>재고 현황 요약</h2>
            <p>부족 위험 SKU, 예산 보호 수준, 우선 조치 품목을 한 화면에서 확인합니다.</p>
          </div>
          <div class="header-chip-row">
            <span class="header-chip">데이터: {escape(data_source_label)}</span>
            <span class="header-chip">{product_count:,}개 SKU · {month_count}개월</span>
            <span class="header-chip">시나리오: {escape(str(selected["label"]))}</span>
            <span class="header-chip">예산: {budget_percent}%</span>
            <span class="header-chip">분석: {analyzed_at}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def make_current_strategy_figure(current_comparison: pd.DataFrame) -> go.Figure:
    strategy_order = ["균등 배분", "비례 배분", "우선순위 배분", "서비스수준 배분"]
    colors = {
        "균등 배분": "#94a3b8",
        "비례 배분": "#2563eb",
        "우선순위 배분": "#06b6d4",
        "서비스수준 배분": "#16a34a",
    }
    frame = (
        current_comparison.set_index("strategy_label")
        .reindex(strategy_order)
        .dropna(subset=["weighted_fulfillment"])
        .reset_index()
    )
    fulfillment = frame["weighted_fulfillment"].astype(float)
    fully_funded = frame["fully_funded_skus"].astype(int)
    labels = [
        f"{format_percent_whole(value)}<br>완전 확보 {count}개"
        for value, count in zip(fulfillment, fully_funded, strict=True)
    ]
    axis_max = min(1.0, max(0.3, float(fulfillment.max()) * 1.35))

    fig = go.Figure(
        data=[
            go.Bar(
                x=frame["strategy_label"],
                y=fulfillment,
                marker={
                    "color": [colors[label] for label in frame["strategy_label"]],
                    "line": {"color": "rgba(255,255,255,0.9)", "width": 1},
                },
                customdata=fully_funded,
                text=labels,
                textposition="outside",
                cliponaxis=False,
                hovertemplate=(
                    "%{x}<br>중요 품목 보호 수준: %{y:.1%}"
                    "<br>완전 확보: %{customdata}개 SKU<extra></extra>"
                ),
            )
        ]
    )
    fig.update_layout(
        template="plotly_white",
        height=360,
        margin={"l": 10, "r": 10, "b": 45, "t": 25},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(248,250,252,0.55)",
        showlegend=False,
        bargap=0.3,
        xaxis={
            "title": None,
            "categoryorder": "array",
            "categoryarray": strategy_order,
            "tickfont": {"size": 12, "color": "#334155"},
        },
        yaxis={
            "title": "중요 품목 보호 수준",
            "tickformat": ".0%",
            "range": [0, axis_max],
            "gridcolor": "#e2e8f0",
            "zeroline": False,
        },
        font={"family": "Arial, sans-serif", "color": "#0f172a"},
    )
    return fig


def render_action_cards(inventory: pd.DataFrame) -> None:
    st.markdown(
        """
        <div class="panel-card">
          <h4>즉시 조치</h4>
          <p>위험도가 높고 아직 부족이 남은 SKU부터 확인하세요.</p>
        """,
        unsafe_allow_html=True,
    )
    actions = (
        inventory[inventory["unmet_quantity"] > 0]
        .sort_values(
            ["status_order", "priority_weight", "unmet_budget"],
            ascending=[True, False, False],
        )
        .head(3)
    )
    if actions.empty:
        st.markdown(
            """
            <div class="action-item">
              <span class="status-badge status-safe">안정</span>
              <b>현재 예산으로 부족 SKU가 없습니다.</b><br>
              <span>시나리오가 악화될 경우 전략 비교 탭에서 여유 예산을 점검하세요.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        badge_class = {"위험": "status-risk", "주의": "status-watch", "안정": "status-safe"}
        for row in actions.itertuples():
            status = str(row.inventory_status)
            unmet_budget_text = format_currency(float(row.unmet_budget))
            st.markdown(
                f"""
                <div class="action-item">
                  <span class="status-badge {badge_class[status]}">{status}</span>
                  <b>{escape(str(row.name))}</b><br>
                  <span>{escape(str(row.sku_id))} · {escape(str(row.abc_xyz))} ·
                  부족 {int(row.unmet_quantity):,}개 · 미충족 {unmet_budget_text}</span><br>
                  <span>현재 확보율 {format_percent(float(row.fulfillment_rate))}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
    st.markdown("</div>", unsafe_allow_html=True)


def render_grade_count_cards(classified: pd.DataFrame) -> None:
    grade_order = ["AZ", "AX", "AY", "BZ", "BX", "BY", "CZ", "CX", "CY"]
    grade_colors = {
        "AZ": "red",
        "AX": "orange",
        "AY": "orange",
        "BZ": "violet",
        "BX": "blue",
        "BY": "blue",
        "CZ": "blue",
        "CX": "green",
        "CY": "green",
    }
    for start in range(0, len(grade_order), 3):
        columns = st.columns(3, gap="small")
        for column, grade in zip(columns, grade_order[start : start + 3], strict=True):
            names = (
                classified.loc[classified["abc_xyz"] == grade, "name"]
                .sort_values()
                .astype(str)
                .tolist()
            )
            with column:
                with st.container(border=True):
                    st.markdown(f":{grade_colors[grade]}[**{grade}**]")
                    if names:
                        st.caption("\n".join(f"• {name}" for name in names))
                    else:
                        st.caption("해당 품목 없음")


def render_effect_cards(effects: StrategyEffects) -> None:
    st.markdown(
        f"""
        <div class="effect-grid">
          <div class="effect-card">
            <span>비례 배분 대비</span>
            <strong>{effects.proportional_delta_pp:+.1f}%p</strong>
          </div>
          <div class="effect-card">
            <span>균등 배분 대비</span>
            <strong>{effects.equal_delta_pp:+.1f}%p</strong>
          </div>
          <div class="effect-card">
            <span>완전 확보 SKU 차이</span>
            <strong>{effects.extra_full_vs_proportional:+d}개</strong>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_copilot_brief(brief: CopilotBrief, *, title: str = "AI 의사결정 코파일럿") -> None:
    actions = "".join(f"<li>{escape(action)}</li>" for action in brief.actions)
    evidence = "".join(f"<li>{escape(item)}</li>" for item in brief.evidence)
    st.markdown(
        f"""
        <div class="copilot-card">
          <h3>🤖 {escape(title)}</h3>
          <p><b>{escape(brief.headline)}</b></p>
          <p>{escape(brief.risk_summary)}</p>
          <h4>추천 조치</h4>
          <ul class="copilot-list">{actions}</ul>
          <h4>추천 근거</h4>
          <ul class="copilot-list">{evidence}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_gscpi_summary(recommendation: GscpiRecommendation, selected_scenario: str) -> None:
    selected_label = str(SCENARIOS[selected_scenario]["label"])
    if recommendation.value is None:
        st.warning(
            "GSCPI 자동 조회를 완료하지 못했습니다. 현재는 사용자가 선택한 물류 시나리오를 "
            f"기준으로 계산합니다. ({recommendation.warning})"
        )
        return
    recommended_label = str(SCENARIOS[recommendation.scenario]["label"])
    st.markdown(
        f"""
        <div class="source-box">
        <b>GSCPI 참고값</b>: {recommendation.value:.2f}
        · 기준월 {escape(str(recommendation.period))}<br>
        <b>추천 상태</b>: {escape(recommendation.status)}
        · 추천 시나리오 {escape(recommended_label)}
        · 배수 {recommendation.multiplier:.2f}배<br>
        <b>현재 적용</b>: 사용자가 선택한 {escape(selected_label)} 시나리오<br>
        <b>주의</b>: GSCPI는 월별 공급망 압력 참고 지표이며 자동 적용값이 아닙니다.
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_service_level_cards(
    service_allocation: pd.DataFrame,
    service_summary: dict[str, float],
) -> None:
    counts = service_allocation["service_level_label"].value_counts()
    columns = st.columns(5, gap="small")
    columns[0].metric("99% 보호", f"{int(counts.get('99%', 0)):,}개")
    columns[1].metric("95% 보호", f"{int(counts.get('95%', 0)):,}개")
    columns[2].metric("90% 보호", f"{int(counts.get('90%', 0)):,}개")
    columns[3].metric("미보호", f"{int(counts.get('미선택', 0)):,}개")
    columns[4].metric("예상손실", format_currency(float(service_summary["expected_loss"])))


def make_route_concentration_figure(route_risk: RouteRiskResult) -> go.Figure:
    """항로별 보호 예산 비중을 가로 막대그래프로 표시한다."""

    frame = route_risk.by_route.sort_values("budget_share", ascending=True)
    colors = [
        "#ef4444" if share > 0.50 else "#f59e0b" if share > 0.25 else "#2563eb"
        for share in frame["budget_share"]
    ]
    fig = go.Figure(
        data=[
            go.Bar(
                x=frame["budget_share"],
                y=frame["route"],
                orientation="h",
                marker={"color": colors},
                text=frame["budget_share"].map(lambda value: f"{value:.0%}"),
                textposition="outside",
                cliponaxis=False,
                customdata=frame["allocated_budget"],
                hovertemplate=(
                    "%{y}<br>예산 비중: %{x:.1%}"
                    "<br>보호 예산: ₩%{customdata:,.0f}<extra></extra>"
                ),
            )
        ]
    )
    fig.update_layout(
        title={"text": "항로별 보호 예산 비중", "x": 0.02, "font": {"size": 18}},
        template="plotly_white",
        height=max(320, 75 + len(frame) * 42),
        margin={"l": 10, "r": 35, "b": 35, "t": 55},
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        xaxis={
            "title": "확인 가능한 항로 예산 내 비중",
            "tickformat": ".0%",
            "range": [0, min(1.0, max(0.35, float(frame["budget_share"].max()) * 1.18))],
            "gridcolor": "#e2e8f0",
        },
        yaxis={"title": None},
    )
    return fig


def render_route_risk_panel(route_risk: RouteRiskResult) -> None:
    """항로 집중도 KPI, 경고와 예산 분포를 한 패널에 표시한다."""

    st.subheader("항로 기반 동시위험 집중도")
    st.caption(
        "같은 항로를 공유하는 SKU는 운하 차단·항만 적체·기상 충격에 동시에 영향을 받을 수 "
        "있습니다. 이 지표는 안전재고를 바꾸지 않고 보호 예산의 항로 집중만 경고합니다."
    )
    if route_risk.hhi is None:
        st.info(route_risk.message)
        return

    columns = st.columns(4, gap="small")
    columns[0].metric("항로 HHI", f"{route_risk.hhi:.3f}")
    columns[1].metric("집중 상태", route_risk.status)
    columns[2].metric("확인 항로", f"{route_risk.route_count:,}개")
    columns[3].metric("항로 정보 확인율", f"{route_risk.coverage_ratio:.0%}")

    if route_risk.status == "위험":
        st.error(f"단일 항로 집중 위험이 큽니다. {route_risk.message}")
    elif route_risk.status == "주의":
        st.warning(f"항로 집중도를 확인해야 합니다. {route_risk.message}")
    else:
        st.success(f"보호 예산이 비교적 분산되어 있습니다. {route_risk.message}")

    st.plotly_chart(
        make_route_concentration_figure(route_risk),
        width="stretch",
        config={"displayModeBar": False},
    )
    st.caption(
        "초기 경고 기준: HHI 0.25 이하 양호, 0.25 초과~0.50 이하 주의, 0.50 초과 위험. "
        "이 기준은 비교용 가정이며 공급사·항만·대체 항로 정보와 함께 판단해야 합니다."
    )


def make_service_level_distribution_figure(service_allocation: pd.DataFrame) -> go.Figure:
    order = ["99%", "95%", "90%", "미선택"]
    counts = service_allocation["service_level_label"].value_counts().reindex(order, fill_value=0)
    colors = ["#16a34a", "#2563eb", "#f59e0b", "#ef4444"]
    fig = go.Figure(
        data=[
            go.Bar(
                x=counts.index,
                y=counts.values,
                marker={"color": colors},
                text=[f"{value}개" for value in counts.values],
                textposition="outside",
                hovertemplate="%{x}: %{y}개 SKU<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        title={"text": "서비스수준별 SKU 수", "x": 0.02},
        template="plotly_white",
        height=330,
        margin={"l": 10, "r": 20, "b": 35, "t": 55},
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis={"title": "추천 보호 수준"},
        yaxis={"title": "SKU 수", "gridcolor": "#e2e8f0"},
    )
    return fig


def make_unprotected_loss_figure(service_allocation: pd.DataFrame) -> go.Figure:
    frame = (
        service_allocation[service_allocation["expected_loss"] > 0]
        .sort_values("expected_loss", ascending=False)
        .head(10)
        .sort_values("expected_loss", ascending=True)
    )
    fig = go.Figure()
    if frame.empty:
        fig.add_annotation(
            text="현재 예산에서 미보호 SKU가 없습니다.",
            x=0.5,
            y=0.5,
            showarrow=False,
            font={"size": 16, "color": "#475569"},
        )
    else:
        fig.add_trace(
            go.Bar(
                x=frame["expected_loss"],
                y=frame["name"],
                orientation="h",
                marker={"color": "#ef4444"},
                hovertemplate="%{y}<br>예상손실: ₩%{x:,.0f}<extra></extra>",
            )
        )
    fig.update_layout(
        title={"text": "미보호 SKU 예상손실 Top 10", "x": 0.02},
        template="plotly_white",
        height=390,
        margin={"l": 10, "r": 20, "b": 35, "t": 55},
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis={"title": "예상손실액", "gridcolor": "#e2e8f0"},
        yaxis={"title": None},
    )
    return fig


GRADE_COLORS = {
    "AZ": "#dc2626",
    "AY": "#ea580c",
    "AX": "#f59e0b",
    "BZ": "#9333ea",
    "BY": "#7c3aed",
    "BX": "#2563eb",
    "CZ": "#0891b2",
    "CY": "#0d9488",
    "CX": "#16a34a",
}


def scaled_marker_size(values: pd.Series, *, minimum: int = 6, maximum: int = 24) -> pd.Series:
    numeric = values.astype(float).fillna(0)
    span = float(numeric.max() - numeric.min())
    if span <= 0:
        return pd.Series([minimum + 4] * len(numeric), index=numeric.index)
    return minimum + (numeric - numeric.min()) / span * (maximum - minimum)


def make_stock_status_figure(inventory: pd.DataFrame) -> go.Figure:
    status_order = ["위험", "주의", "안정"]
    counts = inventory["inventory_status"].value_counts().reindex(status_order, fill_value=0)
    colors = {"위험": "#ef4444", "주의": "#f59e0b", "안정": "#16a34a"}
    fig = go.Figure(
        data=[
            go.Pie(
                labels=counts.index,
                values=counts.values,
                hole=0.58,
                marker={"colors": [colors[label] for label in counts.index]},
                textinfo="label+value",
                hovertemplate="%{label}: %{value}개 SKU<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        title={"text": "재고 상태 분포", "x": 0.04, "font": {"size": 18}},
        template="plotly_white",
        height=315,
        margin={"l": 0, "r": 0, "b": 0, "t": 48},
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        annotations=[
            {
                "text": f"{len(inventory):,}<br>SKU",
                "x": 0.5,
                "y": 0.5,
                "font": {"size": 18, "color": "#0f172a"},
                "showarrow": False,
            }
        ],
    )
    return fig


def make_budget_overview_figure(inventory: pd.DataFrame) -> go.Figure:
    allocated = float(inventory["allocated_budget"].sum())
    unmet = float(inventory["unmet_budget"].sum())
    total = allocated + unmet
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=["필요 금액"],
            x=[allocated],
            name="배정 완료",
            orientation="h",
            marker={"color": "#2563eb"},
            hovertemplate="배정 완료: ₩%{x:,.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            y=["필요 금액"],
            x=[unmet],
            name="미충족 필요",
            orientation="h",
            marker={"color": "#ef4444"},
            hovertemplate="미충족 필요: ₩%{x:,.0f}<extra></extra>",
        )
    )
    fig.update_layout(
        title={"text": "예산 배정 현황", "x": 0.04, "font": {"size": 18}},
        template="plotly_white",
        barmode="stack",
        height=315,
        margin={"l": 10, "r": 18, "b": 18, "t": 48},
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis={"title": "금액", "gridcolor": "#e2e8f0"},
        yaxis={"title": None},
        legend={"orientation": "h", "y": 1.05, "x": 0},
        annotations=[
            {
                "text": f"총 필요 {format_currency(total)}",
                "x": 0.99,
                "y": 1.19,
                "xref": "paper",
                "yref": "paper",
                "showarrow": False,
                "font": {"color": "#475569", "size": 12},
            }
        ],
    )
    return fig


def make_category_need_figure(safety: pd.DataFrame) -> go.Figure:
    category = (
        safety.groupby("category", as_index=False)["required_budget"]
        .sum()
        .sort_values("required_budget", ascending=True)
        .tail(8)
    )
    fig = go.Figure(
        data=[
            go.Bar(
                x=category["required_budget"],
                y=category["category"],
                orientation="h",
                marker={"color": "#06b6d4"},
                hovertemplate="%{y}<br>추가 필요 금액: ₩%{x:,.0f}<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        title={"text": "카테고리별 필요 금액", "x": 0.02, "font": {"size": 18}},
        template="plotly_white",
        height=360,
        margin={"l": 10, "r": 20, "b": 35, "t": 48},
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis={"title": "추가 필요 금액", "gridcolor": "#e2e8f0"},
        yaxis={"title": None},
    )
    return fig


def make_stock_gap_figure(safety: pd.DataFrame) -> go.Figure:
    frame = (
        safety.sort_values("required_budget", ascending=False)
        .head(12)
        .sort_values("required_budget", ascending=True)
    )
    fig = go.Figure()
    for column, label, color in [
        ("current_stock", "현재고", "#94a3b8"),
        ("recommended_stock", "권장 안전재고", "#2563eb"),
        ("required_quantity", "추가 필요 수량", "#ef4444"),
    ]:
        fig.add_trace(
            go.Bar(
                x=frame[column],
                y=frame["name"],
                orientation="h",
                name=label,
                marker={"color": color},
                hovertemplate=f"{label}: %{{x:,.0f}}개<extra>%{{y}}</extra>",
            )
        )
    fig.update_layout(
        title={"text": "주요 SKU 재고 격차", "x": 0.02, "font": {"size": 18}},
        template="plotly_white",
        barmode="group",
        height=470,
        margin={"l": 10, "r": 20, "b": 35, "t": 50},
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis={"title": "수량", "gridcolor": "#e2e8f0"},
        yaxis={"title": None},
        legend={"orientation": "h", "y": 1.04, "x": 0},
    )
    return fig


def apply_3d_layout(
    fig: go.Figure,
    *,
    title: str,
    x_title: str,
    y_title: str,
    z_title: str,
) -> go.Figure:
    fig.update_layout(
        title={"text": title, "x": 0.02, "font": {"size": 20, "color": "#0f172a"}},
        template="plotly_white",
        height=560,
        margin={"l": 0, "r": 0, "b": 0, "t": 52},
        paper_bgcolor="rgba(0,0,0,0)",
        legend={"orientation": "h", "y": 1.02, "x": 0, "bgcolor": "rgba(255,255,255,.65)"},
        scene={
            "xaxis": {"title": x_title, "backgroundcolor": "#f8fafc", "gridcolor": "#dbeafe"},
            "yaxis": {"title": y_title, "backgroundcolor": "#f8fafc", "gridcolor": "#dbeafe"},
            "zaxis": {"title": z_title, "backgroundcolor": "#f8fafc", "gridcolor": "#dbeafe"},
            "camera": {"eye": {"x": 1.55, "y": 1.55, "z": 1.05}},
        },
    )
    return fig


def add_grade_traces(
    fig: go.Figure,
    frame: pd.DataFrame,
    *,
    x: str,
    y: str,
    z: str,
    marker_size: str,
    hovertemplate: str,
) -> None:
    for grade, subset in frame.groupby("abc_xyz", sort=False):
        fig.add_trace(
            go.Scatter3d(
                x=subset[x],
                y=subset[y],
                z=subset[z],
                mode="markers",
                name=str(grade),
                marker={
                    "size": subset[marker_size],
                    "color": GRADE_COLORS.get(str(grade), "#64748b"),
                    "opacity": 0.86,
                    "line": {"width": 1, "color": "rgba(15, 23, 42, .35)"},
                },
                customdata=subset[
                    ["sku_id", "name", "abc_xyz", "priority_weight", "required_budget"]
                ].to_numpy(),
                hovertemplate=hovertemplate,
            )
        )


def make_importance_figure(classified: pd.DataFrame) -> go.Figure:
    frame = classified.sort_values("priority_weight", ascending=False).copy()
    frame["revenue_share_percent"] = frame["revenue_share"] * 100
    frame["marker_size"] = scaled_marker_size(frame["revenue"])
    fig = go.Figure()
    add_grade_traces(
        fig,
        frame,
        x="revenue_share_percent",
        y="coefficient_of_variation",
        z="priority_weight",
        marker_size="marker_size",
        hovertemplate=(
            "<b>%{customdata[1]}</b><br>"
            "SKU: %{customdata[0]}<br>"
            "등급: %{customdata[2]} / 점수: %{customdata[3]}<br>"
            "매출 비중: %{x:.1f}%<br>"
            "수요 변동계수: %{y:.2f}<br>"
            "추가 필요 금액: ₩%{customdata[4]:,.0f}<extra></extra>"
        ),
    )
    return apply_3d_layout(
        fig,
        title="SKU 중요도 3D 맵",
        x_title="매출 비중(%)",
        y_title="수요 변동계수",
        z_title="우선순위 점수",
    )


def make_stock_figure(safety: pd.DataFrame) -> go.Figure:
    frame = safety.sort_values("required_budget", ascending=False).copy()
    frame["effective_lead_time_days"] = frame["lead_time_months"] * 30
    frame["marker_size"] = scaled_marker_size(frame["required_quantity"])
    fig = go.Figure()
    add_grade_traces(
        fig,
        frame,
        x="demand_mean",
        y="effective_lead_time_days",
        z="required_budget",
        marker_size="marker_size",
        hovertemplate=(
            "<b>%{customdata[1]}</b><br>"
            "SKU: %{customdata[0]}<br>"
            "등급: %{customdata[2]} / 점수: %{customdata[3]}<br>"
            "월평균 판매: %{x:.1f}<br>"
            "시나리오 리드타임: %{y:.1f}일<br>"
            "추가 필요 금액: ₩%{z:,.0f}<extra></extra>"
        ),
    )
    return apply_3d_layout(
        fig,
        title="필요 재고 3D 맵",
        x_title="월평균 판매량",
        y_title="시나리오 리드타임(일)",
        z_title="추가 필요 금액(원)",
    )


def make_budget_figure(allocation: pd.DataFrame) -> go.Figure:
    frame = allocation.sort_values("priority_weight", ascending=False).copy()
    frame["marker_size"] = scaled_marker_size(frame["priority_weight"], minimum=8, maximum=26)
    fig = go.Figure(
        data=[
            go.Scatter3d(
                x=frame["required_budget"],
                y=frame["allocated_budget"],
                z=frame["unmet_quantity"],
                mode="markers",
                marker={
                    "size": frame["marker_size"],
                    "color": frame["fulfillment_rate"],
                    "colorscale": [
                        [0, "#ef4444"],
                        [0.5, "#f59e0b"],
                        [1, "#16a34a"],
                    ],
                    "cmin": 0,
                    "cmax": 1,
                    "colorbar": {"title": "확보율", "tickformat": ".0%"},
                    "opacity": 0.88,
                    "line": {"width": 1, "color": "rgba(15, 23, 42, .35)"},
                },
                customdata=frame[["sku_id", "name", "abc_xyz", "priority_weight"]].to_numpy(),
                hovertemplate=(
                    "<b>%{customdata[1]}</b><br>"
                    "SKU: %{customdata[0]}<br>"
                    "등급: %{customdata[2]} / 점수: %{customdata[3]}<br>"
                    "필요 금액: ₩%{x:,.0f}<br>"
                    "배정 금액: ₩%{y:,.0f}<br>"
                    "부족 수량: %{z:,.0f}<extra></extra>"
                ),
            )
        ]
    )
    return apply_3d_layout(
        fig,
        title="예산 배정 3D 맵",
        x_title="필요 금액(원)",
        y_title="배정 금액(원)",
        z_title="부족 수량",
    )


def make_strategy_comparison_figure(comparison: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    strategy_order = ["균등 배분", "비례 배분", "우선순위 배분", "서비스수준 배분"]
    colors = {
        "균등 배분": "#94a3b8",
        "비례 배분": "#2563eb",
        "우선순위 배분": "#06b6d4",
        "서비스수준 배분": "#16a34a",
    }
    for label in strategy_order:
        subset = comparison[comparison["strategy_label"] == label].sort_values("budget_ratio")
        if subset.empty:
            continue
        fig.add_trace(
            go.Scatter(
                x=subset["budget_ratio"],
                y=subset["weighted_fulfillment"],
                mode="lines+markers",
                name=label,
                line={"width": 4, "color": colors[label]},
                marker={"size": 9},
                hovertemplate="예산 %{x:.0%}<br>보호 수준 %{y:.1%}<extra>%{fullData.name}</extra>",
            )
        )
    fig.update_layout(
        title={"text": "예산별 중요 품목 보호 수준", "x": 0.02},
        template="plotly_white",
        height=430,
        margin={"l": 10, "r": 20, "b": 20, "t": 55},
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis={
            "title": "예산 비율",
            "range": [0, 1],
            "tickformat": ".0%",
            "tickvals": sorted(comparison["budget_ratio"].unique()),
            "gridcolor": "#dbeafe",
        },
        yaxis={
            "title": "위험가중 충족률",
            "range": [0, 1.05],
            "tickformat": ".0%",
            "gridcolor": "#dbeafe",
        },
        legend={"orientation": "h", "y": 1.1, "x": 0},
    )
    return fig


def make_what_if_heatmap(what_if: pd.DataFrame) -> go.Figure:
    ordered = what_if.sort_values(["scenario_order", "budget_ratio"])
    pivot = ordered.pivot(
        index="scenario_label",
        columns="budget_ratio",
        values="priority_weighted_fulfillment",
    )
    scenario_order = (
        ordered[["scenario_label", "scenario_order"]]
        .drop_duplicates()
        .sort_values("scenario_order")["scenario_label"]
        .tolist()
    )
    pivot = pivot.reindex(scenario_order)
    x_values = list(pivot.columns)
    fig = go.Figure(
        data=[
            go.Heatmap(
                z=pivot.values,
                x=x_values,
                y=pivot.index,
                colorscale=[
                    [0, "#fee2e2"],
                    [0.45, "#fef3c7"],
                    [0.75, "#bfdbfe"],
                    [1, "#16a34a"],
                ],
                zmin=0,
                zmax=1,
                colorbar={"title": "보호 수준", "tickformat": ".0%"},
                text=[[f"{value:.0%}" for value in row] for row in pivot.values],
                texttemplate="%{text}",
                hovertemplate="시나리오 %{y}<br>예산 %{x:.0%}<br>보호 수준 %{z:.1%}<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        title={"text": "What-if: 시나리오·예산별 중요 품목 보호 수준", "x": 0.02},
        template="plotly_white",
        height=430,
        margin={"l": 10, "r": 20, "b": 35, "t": 55},
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis={"title": "평상시 필요 예산 대비", "tickformat": ".0%", "tickvals": x_values},
        yaxis={"title": "물류 시나리오"},
    )
    return fig


def make_what_if_risk_figure(what_if: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    colors = ["#16a34a", "#2563eb", "#f59e0b", "#ef4444"]
    for color, (label, subset) in zip(
        colors,
        what_if.sort_values("scenario_order").groupby("scenario_label", sort=False),
        strict=False,
    ):
        subset = subset.sort_values("budget_ratio")
        fig.add_trace(
            go.Scatter(
                x=subset["budget_ratio"],
                y=subset["high_risk_skus"],
                mode="lines+markers",
                name=str(label),
                line={"width": 3, "color": color},
                marker={"size": 8},
                hovertemplate="예산 %{x:.0%}<br>고위험 SKU %{y}개<extra>%{fullData.name}</extra>",
            )
        )
    fig.update_layout(
        title={"text": "예산별 고위험 SKU 감소", "x": 0.02},
        template="plotly_white",
        height=380,
        margin={"l": 10, "r": 20, "b": 35, "t": 55},
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis={
            "title": "평상시 필요 예산 대비",
            "tickformat": ".0%",
            "tickvals": sorted(what_if["budget_ratio"].unique()),
            "range": [0, 1],
            "gridcolor": "#e2e8f0",
        },
        yaxis={"title": "고위험 SKU 수", "gridcolor": "#e2e8f0"},
        legend={"orientation": "h", "y": 1.14, "x": 0},
    )
    return fig


def render_scenario_evidence(scenario: str) -> None:
    selected = SCENARIOS[scenario]
    source = str(selected["source"])
    source_url = str(selected["source_url"])
    source_text = (
        f'<a href="{source_url}" target="_blank" rel="noopener noreferrer">{source}</a>'
        if source_url
        else source
    )
    st.markdown(
        f"""
        <div class="source-box">
        <b>현재 가정</b>: {selected['description']}<br>
        <b>리드타임 배수</b>: {selected['multiplier']}배<br>
        <b>적용 방식</b>: 평균 리드타임에만 적용하며 리드타임 표준편차에는 중복 적용하지 않음<br>
        <b>근거</b>: {source_text}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_limitations() -> None:
    st.warning(
        "이 결과는 가상 판매 데이터와 공개 물류 사례를 사용한 PoC입니다. "
        "실제 발주 전에는 최소주문수량, 운송 중 재고, 공급사 생산능력과 현금흐름을 "
        "반드시 함께 확인하세요."
    )


def load_selected_data() -> tuple[pd.DataFrame, pd.DataFrame, str]:
    source_type = st.sidebar.selectbox(
        "분석할 데이터",
        ["기본 예제 데이터", "제공된 CSV 예제", "내 CSV 업로드"],
        help="처음이라면 기본 예제 데이터를 사용하세요.",
    )
    if source_type == "기본 예제 데이터":
        database = ensure_database()
        products, sales = get_database_data(str(database))
        return products, sales, "기본 가상 데이터"

    if source_type == "제공된 CSV 예제":
        sample_paths = sorted(CSV_DIRECTORY.glob("*.csv"))
        if not sample_paths:
            st.sidebar.error("csv 폴더에 예제 파일이 없습니다.")
            st.stop()
        selected_path = st.sidebar.selectbox(
            "가상 기업 선택",
            sample_paths,
            format_func=lambda path: path.stem.replace("_", " "),
        )
        products, sales = get_csv_data(selected_path.read_bytes())
        return products, sales, selected_path.name

    uploaded_file = st.sidebar.file_uploader(
        "재고·판매 CSV 선택",
        type=["csv"],
        help="필수 열과 예제는 도움말에서 확인할 수 있습니다.",
    )
    if uploaded_file is None:
        st.info("왼쪽에서 CSV 파일을 선택하면 분석을 시작합니다.")
        st.stop()
    try:
        products, sales = get_csv_data(uploaded_file.getvalue())
    except ValueError as exc:
        st.sidebar.error(f"CSV를 읽을 수 없습니다: {exc}")
        st.error("CSV 형식을 확인해 주세요. 도움말에 필수 열과 예제 파일이 있습니다.")
        st.stop()
    st.sidebar.success(f"{len(products)}개 품목을 불러왔습니다.")
    return products, sales, uploaded_file.name


st.sidebar.title("🚢 재고 의사결정 도우미")
page_key = current_page_key()
page = render_sidebar_navigation(page_key)
st.sidebar.divider()
products, sales, data_source_label = load_selected_data()

scenario = st.sidebar.selectbox(
    "물류 상황",
    options=list(SCENARIOS),
    format_func=lambda key: f"{SCENARIOS[key]['label']} · {SCENARIOS[key]['multiplier']}배",
    index=1,
    help="숫자가 클수록 운송 지연이 심한 상황입니다.",
)
budget_percent = st.sidebar.slider(
    "사용 가능한 예산",
    0,
    100,
    20,
    5,
    format="%d%%",
    help="권장 안전재고를 모두 확보하는 데 필요한 금액 중 사용할 수 있는 비율입니다.",
)
budget_ratio = budget_percent / 100
carrying_cost_percent = st.sidebar.slider(
    "재고보유비율",
    15,
    30,
    int(DEFAULT_CARRYING_COST_RATE * 100),
    1,
    format="%d%%",
    help="서비스수준 배분에서 추가 안전재고를 보유하는 비용 비율입니다.",
)
carrying_cost_rate = carrying_cost_percent / 100

with st.sidebar.expander("OpenAI 계정 연결", expanded=False):
    st.caption("ChatGPT 구독과 API 결제는 별도입니다. OpenAI API 키가 필요합니다.")
    entered_api_key = st.text_input(
        "OpenAI API 키",
        type="password",
        placeholder="sk-...",
        help="현재 앱 세션에서만 사용하며 파일이나 DB에 저장하지 않습니다.",
    )
    st.link_button("OpenAI API 키 발급", "https://platform.openai.com/api-keys")

api_key = entered_api_key or get_config_value("OPENAI_API_KEY")
openai_model = get_config_value("SCM_OPENAI_MODEL", DEFAULT_MODEL)
result = run_analysis(products, sales, scenario, budget_ratio)
service_allocation, service_summary, service_full_budget = run_service_level_allocation(
    result.safety_stock,
    budget_ratio,
    carrying_cost_rate,
)
route_risk = calculate_route_concentration(service_allocation)
comparison = compare_strategies(result.safety_stock, carrying_cost_rate=carrying_cost_rate)
current_comparison = compare_strategies(
    result.safety_stock,
    [budget_ratio],
    carrying_cost_rate=carrying_cost_rate,
)
gscpi_recommendation = (
    get_gscpi_recommendation()
    if page == "위험 시나리오"
    else GscpiRecommendation(
        value=None,
        period=None,
        status="대기",
        scenario=scenario,
        multiplier=float(SCENARIOS[scenario]["multiplier"]),
        source="",
        warning="위험 시나리오 페이지에서 자동 조회합니다.",
    )
)
strategy_effects = calculate_strategy_effects(current_comparison)
copilot_brief = build_copilot_brief(
    result.allocation,
    strategy_effects,
    scenario_label=str(SCENARIOS[scenario]["label"]),
    budget_ratio=budget_ratio,
    service_allocation=service_allocation,
)

st.sidebar.divider()
st.sidebar.caption(f"데이터: {data_source_label}")
st.sidebar.caption(f"{len(products)}개 SKU · {sales['month'].nunique()}개월")
st.sidebar.caption(f"재고보유비율: {carrying_cost_percent}%")
if route_risk.hhi is None:
    st.sidebar.caption("항로 집중도: 정보 없음")
else:
    st.sidebar.caption(f"항로 집중도: {route_risk.status} · HHI {route_risk.hhi:.3f}")
st.sidebar.caption("⚠️ 가상 데이터 기반 의사결정 연습용")

if page == "한눈에 보기":
    summary = result.summary
    inventory = prepare_inventory_dashboard(result.allocation)
    shortage_count = int((result.safety_stock["required_quantity"] > 0).sum())
    render_dashboard_header(
        data_source_label=data_source_label,
        scenario=scenario,
        budget_percent=budget_percent,
        product_count=len(products),
        month_count=int(sales["month"].nunique()),
    )
    render_flow_note(
        "1 / 8단계: 전체 상황 파악",
        "데이터, 시나리오, 예산 조건에서 어떤 SKU를 어느 수준까지 보호할지 요약합니다.",
    )
    render_steps()

    columns = st.columns(6, gap="small")
    columns[0].metric("총 SKU 수", f"{len(products):,}개", help="분석 대상 품목 수")
    columns[1].metric(
        "부족 위험 SKU",
        f"{shortage_count:,}개",
        help="추가 안전재고가 필요한 SKU 수",
    )
    columns[2].metric(
        "안전재고 필요 금액",
        f"₩{result.safety_stock['required_budget'].sum():,.0f}",
        help="현재고를 제외하고 추가 확보해야 하는 총금액",
    )
    columns[3].metric(
        "사용 가능 예산",
        f"₩{summary['budget']:,.0f}",
        help="왼쪽에서 정한 예산 비율을 금액으로 환산한 값",
    )
    columns[4].metric(
        "중요 품목 보호 수준",
        f"{summary['priority_weighted_fulfillment']:.1%}",
        help="중요도와 부족 금액을 반영한 위험가중 충족률",
    )
    columns[5].metric(
        "미보호 예상손실",
        format_currency(float(service_summary["expected_loss"])),
        help="서비스수준 배분에서 미선택된 SKU의 추정 손실액",
    )

    st.markdown(
        '<div class="plain-box"><b>운영자가 먼저 볼 것</b><br>'
        "빨간 위험 SKU는 중요도가 높거나 예산 배정 후에도 확보율이 낮은 품목입니다. "
        "아래 우선 조치 SKU에서 발주 가능 여부, 공급사 납기, 대체재를 먼저 확인하세요.</div>",
        unsafe_allow_html=True,
    )
    render_copilot_brief(copilot_brief)

    st.subheader("서비스수준 기반 보호 요약")
    st.caption(
        "같은 예산 비율을 서비스수준 보호예산에 적용해 SKU별 90%·95%·99%·미보호를 선택합니다."
    )
    render_service_level_cards(service_allocation, service_summary)

    st.subheader("AI 추천 효과 Before/After")
    render_effect_cards(strategy_effects)
    st.caption(
        "우선순위 배분의 기존 Before/After와 서비스수준 배분의 미보호 위험을 함께 확인합니다."
    )

    dashboard_columns = st.columns(3, gap="small")
    with dashboard_columns[0]:
        st.plotly_chart(make_stock_status_figure(inventory), width="stretch")
    with dashboard_columns[1]:
        st.plotly_chart(make_budget_overview_figure(inventory), width="stretch")
    with dashboard_columns[2]:
        render_action_cards(inventory)

    lower_left, lower_right = st.columns(2, gap="small")
    with lower_left:
        st.plotly_chart(make_category_need_figure(result.safety_stock), width="stretch")
    with lower_right:
        with st.container(border=True):
            st.markdown("#### 예산 배분 시뮬레이션")
            st.caption("현재 예산 조건에서 네 가지 배분 방식의 중요 품목 보호 수준입니다.")
            st.plotly_chart(
                make_current_strategy_figure(current_comparison),
                width="stretch",
                config={"displayModeBar": False},
            )
            st.caption("상세 추세는 전략 비교 탭에서 10%~100% 예산 조건으로 확인합니다.")

    st.subheader("우선 조치 SKU")
    risks = inventory.sort_values(
        ["status_order", "priority_weight", "unmet_budget"],
        ascending=[True, False, False],
    ).head(12)
    st.dataframe(
        risks[
            [
                "inventory_status",
                "sku_id",
                "name",
                "abc_xyz",
                "current_stock",
                "recommended_stock",
                "required_quantity",
                "allocated_quantity",
                "unmet_quantity",
                "required_budget",
                "unmet_budget",
                "fulfillment_rate",
            ]
        ],
        width="stretch",
        hide_index=True,
        column_config={
            "inventory_status": "상태",
            "sku_id": "품목 코드",
            "name": "품목명",
            "abc_xyz": "관리 등급",
            "current_stock": "현재고",
            "recommended_stock": "권장재고",
            "required_quantity": "필요 수량",
            "allocated_quantity": "추천 확보 수량",
            "unmet_quantity": "부족 수량",
            "required_budget": st.column_config.NumberColumn("필요 금액", format="₩%.0f"),
            "unmet_budget": st.column_config.NumberColumn("미충족 금액", format="₩%.0f"),
            "fulfillment_rate": st.column_config.ProgressColumn(
                "확보율", min_value=0, max_value=1, format="percent"
            ),
        },
    )
    render_scenario_evidence(scenario)
    render_limitations()

elif page == "데이터 확인":
    render_hero(
        "지금 어떤 데이터를 보고 있나요?",
        "분석에 사용된 SKU, 판매 이력, 리드타임 컬럼을 먼저 확인합니다.",
    )
    render_flow_note(
        "2 / 8단계: 데이터 확인",
        "결과를 해석하기 전에 현재 데이터가 예제인지 업로드 파일인지, "
        "어떤 컬럼을 쓰는지 확인합니다.",
    )
    columns = st.columns(4, gap="small")
    columns[0].metric("데이터 출처", data_source_label)
    columns[1].metric("SKU 수", f"{len(products):,}개")
    columns[2].metric("판매 이력", f"{sales['month'].nunique():,}개월")
    columns[3].metric("판매 행 수", f"{len(sales):,}건")
    st.warning(
        "현재 데이터는 의사결정 구조를 검증하기 위한 합성 또는 업로드 데이터입니다. "
        "실제 발주 전에는 기업 내부 수요, 단가, 리드타임, 운송 중 재고를 다시 확인해야 합니다."
    )
    st.subheader("제품 데이터 미리보기")
    product_columns = [
        column
        for column in [
            "sku_id",
            "name",
            "category",
            "route",
            "unit_cost",
            "current_stock",
            "lead_time_days",
            "lead_time_std_days",
            "service_level",
        ]
        if column in products.columns
    ]
    st.dataframe(
        products[product_columns].head(20),
        width="stretch",
        hide_index=True,
        column_config={
            "sku_id": "품목 코드",
            "name": "품목명",
            "category": "카테고리",
            "route": "해상 항로",
            "unit_cost": st.column_config.NumberColumn("단가", format="₩%.0f"),
            "current_stock": "현재고",
            "lead_time_days": st.column_config.NumberColumn("평균 리드타임", format="%.1f일"),
            "lead_time_std_days": st.column_config.NumberColumn(
                "리드타임 표준편차",
                format="%.1f일",
            ),
            "service_level": st.column_config.NumberColumn("기본 서비스수준", format="percent"),
        },
    )
    st.subheader("판매 이력 요약")
    sales_summary = (
        sales.groupby("sku_id", as_index=False)
        .agg(
            monthly_mean=("quantity", "mean"),
            monthly_std=("quantity", "std"),
            total_quantity=("quantity", "sum"),
            periods=("quantity", "count"),
        )
        .merge(products[["sku_id", "name"]], on="sku_id", how="left")
        .sort_values("total_quantity", ascending=False)
    )
    st.dataframe(
        sales_summary[
            ["sku_id", "name", "monthly_mean", "monthly_std", "total_quantity", "periods"]
        ],
        width="stretch",
        hide_index=True,
        column_config={
            "sku_id": "품목 코드",
            "name": "품목명",
            "monthly_mean": st.column_config.NumberColumn("월평균 판매", format="%.1f"),
            "monthly_std": st.column_config.NumberColumn("월 판매 표준편차", format="%.1f"),
            "total_quantity": "누적 판매량",
            "periods": "개월 수",
        },
    )
    render_limitations()

elif page == "위험 시나리오":
    render_hero(
        "현재 공급망 위험은 어느 정도로 볼까요?",
        "GSCPI 참고값과 사용자가 선택한 물류 시나리오를 구분해서 확인합니다.",
    )
    render_flow_note(
        "3 / 8단계: 위험 시나리오 선택",
        "외부 지표는 추천만 제공하며, 최종 계산은 왼쪽에서 사용자가 선택한 시나리오로 수행합니다.",
    )
    render_gscpi_summary(gscpi_recommendation, scenario)
    st.subheader("시나리오 카드")
    scenario_columns = st.columns(4, gap="small")
    for column, (key, details) in zip(scenario_columns, SCENARIOS.items(), strict=True):
        with column:
            with st.container(border=True):
                label = str(details["label"])
                selected_mark = " · 현재 적용" if key == scenario else ""
                recommended_mark = (
                    " · GSCPI 추천" if gscpi_recommendation.scenario == key else ""
                )
                st.markdown(f"#### {label}{selected_mark}{recommended_mark}")
                st.metric("리드타임 배수", f"{float(details['multiplier']):.2f}배")
                st.caption(str(details["description"]))
    st.info(
        "위기배수는 정밀 예측값이 아니라 비교를 위한 시나리오 가정입니다. "
        "실제 의사결정에서는 공급사 납기, 운송 중 재고, 대체 운송 수단을 함께 확인해야 합니다."
    )
    render_scenario_evidence(scenario)
    render_route_risk_panel(route_risk)
    render_limitations()

elif page == "품목 중요도":
    render_hero(
        "어떤 품목이 더 중요한가요?",
        "매출 기여도와 판매량의 흔들림을 함께 보고 관리 순서를 정합니다.",
    )
    render_flow_note(
        "4 / 8단계: 품목 중요도 확인",
        "ABC는 매출 중요도, XYZ는 수요 변동성을 뜻합니다. 높은 중요도 품목이 먼저 보호됩니다.",
    )
    left, right = st.columns(2)
    left.info(
        "**ABC는 매출 중요도입니다.** A는 매출 기여도가 큰 핵심 품목, "
        "C는 상대적으로 영향이 작은 품목입니다."
    )
    right.info(
        "**XYZ는 수요 안정성입니다.** X는 판매량이 안정적이고, "
        "Z는 판매량 변동이 커서 예측하기 어렵습니다."
    )
    st.markdown("**예:** AZ는 매출이 중요하면서 수요도 불안정하므로 가장 먼저 살핍니다.")
    classified = result.safety_stock.copy()
    st.subheader("ABC-XYZ 등급별 품목 목록")
    render_grade_count_cards(classified)
    st.plotly_chart(make_importance_figure(classified), width="stretch")
    st.markdown(
        '<p class="chart-note">점이 위쪽·앞쪽으로 갈수록 우선순위가 높습니다. '
        "점 크기는 매출 규모를 의미합니다.</p>",
        unsafe_allow_html=True,
    )
    st.dataframe(
        classified[
            [
                "sku_id",
                "name",
                "revenue",
                "revenue_share",
                "coefficient_of_variation",
                "abc_xyz",
                "priority_weight",
            ]
        ],
        width="stretch",
        hide_index=True,
        column_config={
            "sku_id": "품목 코드",
            "name": "품목명",
            "revenue": st.column_config.NumberColumn("누적 매출", format="₩%.0f"),
            "revenue_share": st.column_config.NumberColumn("매출 비중", format="percent"),
            "coefficient_of_variation": st.column_config.NumberColumn(
                "수요 변동계수", format="%.2f"
            ),
            "abc_xyz": "관리 등급",
            "priority_weight": "우선순위 점수",
        },
    )
    st.caption("분류 기준: ABC 누적 매출 80%·95%, XYZ 수요 변동계수 0.2·0.5")
    render_limitations()

elif page == "필요 재고":
    render_hero(
        "물류가 늦어질 때 얼마나 더 필요할까요?",
        "평균 수요뿐 아니라 수요 변화와 리드타임 변화까지 반영해 안전재고를 계산합니다.",
    )
    render_flow_note(
        "5 / 8단계: 안전재고 필요량 확인",
        "수요 변동성 σd와 리드타임 변동성 σL이 커질수록 필요한 안전재고가 증가합니다.",
    )
    render_scenario_evidence(scenario)
    st.markdown(
        '<div class="plain-box"><b>안전재고란?</b><br>'
        "예상보다 많이 팔리거나 배가 늦게 도착할 때 품절을 막기 위해 미리 확보하는 "
        "여유 재고입니다.</div>",
        unsafe_allow_html=True,
    )
    with st.expander("계산식과 용어 자세히 보기"):
        st.latex(r"SS = z \times \sqrt{L\sigma_d^2 + d^2\sigma_L^2}")
        st.markdown(
            "- `z`: 목표 서비스 수준에 따른 안전계수\n"
            "- `d`, `σd`: 월평균 수요와 수요 표준편차\n"
            "- `L`, `σL`: 평균 리드타임과 리드타임 표준편차\n\n"
            "위기배수는 평균 리드타임 `L`에만 적용하며 `σL`에는 다시 곱하지 않습니다. "
            "수요 또는 배송 기간이 더 불안정할수록 안전재고가 커집니다."
        )
    safety = result.safety_stock.copy()
    st.plotly_chart(make_stock_gap_figure(safety), width="stretch")
    st.markdown(
        '<p class="chart-note">필요 금액이 큰 상위 SKU를 기준으로 현재고, 권장재고, '
        "추가 필요 수량을 비교합니다.</p>",
        unsafe_allow_html=True,
    )
    st.plotly_chart(make_stock_figure(safety), width="stretch")
    st.markdown(
        '<p class="chart-note">위로 높이 솟은 점은 추가 확보 금액이 큰 SKU입니다. '
        "오른쪽으로 갈수록 판매량이 많고, 뒤로 갈수록 리드타임 부담이 큽니다.</p>",
        unsafe_allow_html=True,
    )
    st.dataframe(
        safety[
            [
                "sku_id",
                "name",
                "demand_mean",
                "current_stock",
                "recommended_stock",
                "required_quantity",
                "required_budget",
                "reorder_point",
            ]
        ],
        width="stretch",
        hide_index=True,
        column_config={
            "sku_id": "품목 코드",
            "name": "품목명",
            "demand_mean": st.column_config.NumberColumn("월평균 판매", format="%.1f"),
            "current_stock": "현재고",
            "recommended_stock": "권장 안전재고",
            "required_quantity": "추가 필요 수량",
            "required_budget": st.column_config.NumberColumn("추가 필요 금액", format="₩%.0f"),
            "reorder_point": "발주 시점 재고",
        },
    )
    render_limitations()

elif page == "예산 추천":
    render_hero(
        "예산이 부족하면 어느 수준까지 보호해야 할까요?",
        "SKU별로 90%·95%·99%·미보호 중 하나를 선택해 제한 예산을 배분합니다.",
    )
    render_flow_note(
        "6 / 8단계: 서비스수준 기반 예산 추천",
        "모든 품목을 최고 수준으로 보호할 수 없을 때, "
        "중요한 품목에 높은 서비스수준을 먼저 배정합니다.",
    )
    summary = result.summary
    allocation = result.allocation.copy()
    service_allocation_display = service_allocation.copy()
    budget_usage = (
        service_summary["allocated_budget"] / service_summary["budget"]
        if service_summary["budget"] > 0
        else 0.0
    )
    unprotected_count = int(service_summary["unprotected_skus"])
    protected_count = int(service_summary["protected_skus"])
    columns = st.columns(4)
    columns[0].metric("예산 사용률", f"{budget_usage:.1%}")
    columns[1].metric("보호 SKU", f"{protected_count:,}개")
    columns[2].metric("미보호 SKU", f"{unprotected_count:,}개")
    columns[3].metric("남은 보호예산", f"₩{service_summary['remaining_budget']:,.0f}")
    st.info(
        "서비스수준 배분은 기존 σL 포함 안전재고 공식으로 90%, 95%, 99% 후보를 만든 뒤, "
        "예산 안에서 SKU마다 하나의 보호 수준만 선택합니다. "
        f"현재 서비스수준 보호예산은 99% 전체 보호비용 {format_currency(service_full_budget)}의 "
        f"{budget_ratio:.0%}입니다."
    )
    render_service_level_cards(service_allocation, service_summary)
    left, right = st.columns([1, 1.25], gap="small")
    with left:
        st.plotly_chart(make_service_level_distribution_figure(service_allocation), width="stretch")
    with right:
        st.plotly_chart(make_budget_figure(allocation), width="stretch")
    st.markdown(
        '<p class="chart-note">왼쪽은 신규 서비스수준 배분 결과, '
        "오른쪽은 기존 우선순위 수량 배분 결과입니다. "
        "두 방식을 함께 보면 보호 수준과 실제 부족 수량을 동시에 판단할 수 있습니다.</p>",
        unsafe_allow_html=True,
    )
    service_allocation_display = service_allocation_display.sort_values(
        ["service_level", "priority_weight", "service_allocated_budget"],
        ascending=[False, False, False],
    )
    st.dataframe(
        service_allocation_display[
            [
                "sku_id",
                "name",
                "abc_xyz",
                "priority_weight",
                "service_level_label",
                "service_recommended_stock",
                "service_required_quantity",
                "service_allocated_budget",
                "service_status",
                "selection_reason",
            ]
        ],
        width="stretch",
        hide_index=True,
        column_config={
            "sku_id": "품목 코드",
            "name": "품목명",
            "abc_xyz": "관리 등급",
            "priority_weight": "중요도",
            "service_level_label": "추천 서비스수준",
            "service_recommended_stock": "권장 안전재고",
            "service_required_quantity": "추가 필요 수량",
            "service_allocated_budget": st.column_config.NumberColumn(
                "보호 비용", format="₩%.0f"
            ),
            "service_status": "상태",
            "selection_reason": "추천 사유",
        },
    )
    with st.expander("기존 우선순위 수량 배분도 함께 보기"):
        allocation_display = allocation.assign(
            is_recommended=allocation["allocated_quantity"] > 0
        ).sort_values(
            ["is_recommended", "priority_weight", "allocated_budget", "unmet_quantity"],
            ascending=[False, False, False, False],
        )
        st.dataframe(
            allocation_display[
                [
                    "sku_id",
                    "name",
                    "abc_xyz",
                    "required_budget",
                    "allocated_budget",
                    "allocated_quantity",
                    "unmet_quantity",
                    "fulfillment_rate",
                ]
            ],
            width="stretch",
            hide_index=True,
        )
    render_limitations()

elif page == "포기 SKU":
    render_hero(
        "이번 예산에서 보호하지 못한 품목은 무엇인가요?",
        "미보호 SKU와 예상손실액을 확인해 예산 부족의 결과를 명확히 봅니다.",
    )
    render_flow_note(
        "7 / 8단계: 포기 SKU와 예상손실 확인",
        "제한 예산에서는 일부 SKU를 보호하지 못할 수 있습니다. "
        "이 화면은 그 위험을 숫자로 보여줍니다.",
    )
    unprotected = service_allocation[service_allocation["service_level"] <= 0].sort_values(
        ["expected_loss", "priority_weight"],
        ascending=[False, False],
    )
    columns = st.columns(4, gap="small")
    columns[0].metric("미보호 SKU", f"{len(unprotected):,}개")
    columns[1].metric("예상손실 총액", format_currency(float(service_summary["expected_loss"])))
    columns[2].metric("보호 SKU", f"{int(service_summary['protected_skus']):,}개")
    columns[3].metric(
        "평균 보호수준",
        format_percent(float(service_summary["weighted_service_level"])),
    )
    st.warning(
        "예상손실액은 의사결정 비교를 위한 추정값이며 실제 손실액을 보장하지 않습니다. "
        "초기 산식은 `월평균 수요 × 단가 × 예상 결품기간 × 손실계수`입니다."
    )
    st.plotly_chart(make_unprotected_loss_figure(service_allocation), width="stretch")
    if unprotected.empty:
        st.success("현재 서비스수준 보호예산에서는 미보호 SKU가 없습니다.")
    else:
        st.dataframe(
            unprotected[
                [
                    "sku_id",
                    "name",
                    "abc_xyz",
                    "priority_weight",
                    "demand_mean",
                    "unit_cost",
                    "expected_loss",
                    "loss_reason",
                    "selection_reason",
                ]
            ],
            width="stretch",
            hide_index=True,
            column_config={
                "sku_id": "품목 코드",
                "name": "품목명",
                "abc_xyz": "관리 등급",
                "priority_weight": "중요도",
                "demand_mean": st.column_config.NumberColumn("월평균 수요", format="%.1f"),
                "unit_cost": st.column_config.NumberColumn("단가", format="₩%.0f"),
                "expected_loss": st.column_config.NumberColumn("예상손실액", format="₩%.0f"),
                "loss_reason": "손실 해석",
                "selection_reason": "미선택 사유",
            },
        )
    st.info(
        "포기 SKU가 업무상 중요한 거래처와 연결되어 있다면, 알고리즘 결과와 별도로 "
        "수동 예외 처리를 검토해야 합니다."
    )
    render_limitations()

elif page == "전략 비교":
    render_hero(
        "예산과 물류 충격이 달라지면 어떤 선택이 유리할까요?",
        "전략 비교와 What-if 시뮬레이션으로 위기 대응 예산의 효과를 확인합니다.",
    )
    render_flow_note(
        "8 / 8단계: 전략 비교와 최종 판단",
        "균등·비례·우선순위·서비스수준 배분을 비교해 같은 예산 비율에서 어떤 방식이 나은지 봅니다.",
    )
    st.subheader("AI 추천 효과 Before/After")
    render_effect_cards(strategy_effects)
    explanation_columns = st.columns(4)
    explanation_columns[0].info("**균등 배분**\n\n모든 품목에 같은 금액 한도를 줍니다.")
    explanation_columns[1].info("**비례 배분**\n\n모든 품목의 필요량을 같은 비율로 채웁니다.")
    explanation_columns[2].success("**우선순위 배분**\n\n중요 품목부터 먼저 필요한 양을 채웁니다.")
    explanation_columns[3].success(
        "**서비스수준 배분**\n\nSKU마다 90%·95%·99%·미보호 중 하나를 선택합니다."
    )
    st.subheader("예산별 중요 품목 보호 수준")
    st.plotly_chart(make_strategy_comparison_figure(comparison), width="stretch")
    st.caption("X축은 실제 숫자 비율로 정렬되어 100%가 항상 가장 오른쪽에 표시됩니다.")
    display_comparison = comparison.copy()
    display_comparison["budget_ratio"] = display_comparison["budget_ratio"].map(
        lambda value: f"{value:.0%}"
    )
    st.dataframe(
        display_comparison[
            [
                "budget_ratio",
                "strategy_label",
                "weighted_fulfillment",
                "fully_funded_skus",
                "unprotected_skus",
                "expected_loss",
                "allocated_budget",
                "remaining_budget",
            ]
        ],
        width="stretch",
        hide_index=True,
        column_config={
            "budget_ratio": "예산 비율",
            "strategy_label": "배분 방법",
            "weighted_fulfillment": st.column_config.NumberColumn(
                "중요 품목 보호 수준", format="percent"
            ),
            "fully_funded_skus": "완전 확보 품목",
            "unprotected_skus": "미보호 SKU",
            "expected_loss": st.column_config.NumberColumn("예상손실액", format="₩%.0f"),
            "allocated_budget": st.column_config.NumberColumn("사용 금액", format="₩%.0f"),
            "remaining_budget": st.column_config.NumberColumn("남은 금액", format="₩%.0f"),
        },
    )
    st.caption(
        "위험가중 충족률은 필요한 재고금액과 ABC-XYZ 중요도를 함께 반영합니다. "
        "따라서 중요한 품목을 먼저 보호할수록 높아집니다."
    )
    render_route_risk_panel(route_risk)
    st.subheader("What-if 위기 시뮬레이터")
    st.markdown(
        '<div class="whatif-note"><b>읽는 법</b><br>'
        "행은 물류 충격 시나리오, 열은 평상시 필요 예산 대비 투입 비율입니다. "
        "같은 금액을 투입했을 때 색이 초록색에 가까울수록 중요 품목 보호 수준이 높습니다.</div>",
        unsafe_allow_html=True,
    )
    what_if = run_what_if(products, sales, budget_ratio)
    st.plotly_chart(make_what_if_heatmap(what_if), width="stretch")
    left, right = st.columns([1.15, 1])
    with left:
        st.plotly_chart(make_what_if_risk_figure(what_if), width="stretch")
    with right:
        current_rows = what_if[
            (what_if["scenario"] == scenario)
            & (what_if["budget_ratio"].sub(budget_ratio).abs() < 1e-9)
        ]
        current_high_risk = (
            int(current_rows.iloc[0]["high_risk_skus"])
            if not current_rows.empty
            else int(what_if[what_if["scenario"] == scenario].iloc[0]["high_risk_skus"])
        )
        current_path = what_if[
            (what_if["scenario"] == scenario) & (what_if["budget_ratio"] > budget_ratio)
        ].sort_values("budget_ratio")
        better = current_path[current_path["high_risk_skus"] < current_high_risk]
        if not better.empty:
            candidate = better.iloc[0]
            st.success(
                "현재 시나리오에서 예산을 "
                f"{candidate['budget_ratio']:.0%}까지 올리면 고위험 SKU가 "
                f"{int(candidate['high_risk_skus'])}개로 줄어듭니다."
            )
        else:
            st.info(
                "현재 예산 이후 구간에서도 고위험 SKU가 즉시 줄지 않습니다. "
                "공급사 납기 단축이나 대체재 확보를 함께 검토하세요."
            )
        display_what_if = what_if.copy()
        display_what_if["budget_ratio"] = display_what_if["budget_ratio"].map(
            lambda value: f"{value:.0%}"
        )
        st.dataframe(
            display_what_if[
                [
                    "scenario_label",
                    "budget_ratio",
                    "priority_weighted_fulfillment",
                    "high_risk_skus",
                    "fully_funded_skus",
                    "unmet_budget",
                ]
            ],
            width="stretch",
            hide_index=True,
            column_config={
                "scenario_label": "시나리오",
                "budget_ratio": "평상시 예산 비율",
                "priority_weighted_fulfillment": st.column_config.NumberColumn(
                    "보호 수준", format="percent"
                ),
                "high_risk_skus": "고위험 SKU",
                "fully_funded_skus": "완전 확보 SKU",
                "unmet_budget": st.column_config.NumberColumn("미충족 금액", format="₩%.0f"),
            },
        )
    render_limitations()

elif page == "AI 조언":
    render_hero(
        "AI 재고 의사결정 코파일럿",
        "계산 결과를 위험 요약, 추천 조치, 근거, 개선 효과로 바꿔 실무 의사결정을 돕습니다.",
    )
    render_flow_note(
        "최종 요약: 사람이 결정하기 쉽게 정리",
        "AI는 계산을 대신하지 않고, 서비스수준·미보호 SKU·예상손실을 쉬운 문장으로 요약합니다.",
    )
    render_copilot_brief(copilot_brief, title="현재 조건 자동 브리핑")
    st.subheader("추천 배분의 Before/After 효과")
    render_effect_cards(strategy_effects)
    st.markdown(
        '<div class="plain-box"><b>발표 포인트</b><br>'
        "이 코파일럿은 원시 판매 이력을 그대로 설명하지 않고, 계산된 재고 위험·등급·예산 배정 "
        "결과를 실행 가능한 조치로 바꿉니다.</div>",
        unsafe_allow_html=True,
    )
    if api_key:
        st.success(f"OpenAI API 연결 준비 완료 · 모델: {openai_model}")
    else:
        st.info(
            "OpenAI API 키가 없어 데모 조언을 사용합니다. 왼쪽의 ‘OpenAI 계정 연결’에서 "
            "키를 입력할 수 있습니다."
        )
    force_demo = st.toggle("데모 모드 사용", value=not bool(api_key))
    st.caption(
        "API로 보내는 정보는 집계된 SKU 코드·등급·필요량·배정량이며 "
        "원시 판매 이력은 제외합니다."
    )
    if st.button("AI 조언 만들기", type="primary"):
        with st.spinner("분석 결과를 쉬운 말로 정리하고 있습니다..."):
            diagnosis = generate_diagnosis(
                result.allocation,
                str(SCENARIOS[scenario]["label"]),
                budget_ratio,
                api_key=api_key,
                model=openai_model,
                force_demo=force_demo,
            )
        if diagnosis.warning:
            st.warning(diagnosis.warning)
        st.caption(f"생성 방식: {diagnosis.mode}")
        st.markdown(diagnosis.text)
    render_limitations()

else:
    render_hero(
        "처음 사용하는 분을 위한 도움말",
        "용어, CSV 형식, 데이터 근거와 한계를 한곳에서 확인할 수 있습니다.",
    )
    st.subheader("추천 사용 순서")
    st.markdown(
        "1. 데이터 확인에서 분석 대상과 한계를 확인합니다.\n"
        "2. 위험 시나리오에서 GSCPI 참고값과 사용자가 선택한 시나리오를 비교합니다.\n"
        "3. 품목 중요도와 필요 재고에서 왜 재고가 필요한지 확인합니다.\n"
        "4. 예산 추천에서 SKU별 90%·95%·99%·미보호 결과를 봅니다.\n"
        "5. 포기 SKU에서 예상손실액을 확인합니다.\n"
        "6. 전략 비교와 AI 조언에서 최종 의사결정을 정리합니다."
    )
    st.subheader("CSV 업로드 형식")
    st.code(",".join(CSV_COLUMNS), language="text")
    st.write(
        "한 행은 한 SKU의 한 달 판매량입니다. 같은 SKU의 제품 정보는 매월 동일해야 하며 "
        "최소 2개월의 판매 이력이 필요합니다. `route`는 선택 열이며, 없으면 기존 분석은 "
        "정상 실행되고 항로 집중도만 ‘정보 없음’으로 표시됩니다."
    )
    sample_file = CSV_DIRECTORY / "01_electronics_stable.csv"
    if sample_file.exists():
        st.download_button(
            "CSV 예제 내려받기",
            sample_file.read_bytes(),
            file_name=sample_file.name,
            mime="text/csv",
        )

    st.subheader("물류 시나리오 근거")
    for _key, details in SCENARIOS.items():
        source = str(details["source"])
        url = str(details["source_url"])
        source_text = f"[{source}]({url})" if url else source
        st.markdown(
            f"- **{details['label']} {details['multiplier']}배** — "
            f"{details['description']} / {source_text}"
        )
    st.caption(
        "고충격·극단충격 Flexport 사례의 원문 링크는 현재 조사 기록에 없어 "
        "추가 검증이 필요합니다."
    )

    st.subheader("OpenAI 연결 안내")
    st.markdown(
        "ChatGPT Plus/Pro 구독과 OpenAI API 사용료는 별도입니다. "
        "`OPENAI_API_KEY` 환경변수 또는 화면의 비밀번호 입력을 사용합니다. "
        "기본 모델은 `gpt-5.5`이며 `SCM_OPENAI_MODEL`로 변경할 수 있습니다."
    )
    render_limitations()
