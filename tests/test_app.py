from __future__ import annotations

from streamlit.testing.v1 import AppTest


def test_streamlit_dashboard_loads_without_exception():
    app = AppTest.from_file("app.py", default_timeout=30)
    app.run()

    assert not app.exception
    assert app.title
    assert len(app.metric) >= 8
    assert len(app.radio) == 0
    assert any("재고 현황 요약" in block.value for block in app.markdown)


def test_all_navigation_pages_load_without_exception(monkeypatch):
    monkeypatch.setenv("SCM_SKIP_GSCPI", "1")
    pages = [
        "data",
        "scenario",
        "importance",
        "stock",
        "budget",
        "abandoned",
        "compare",
        "ai",
        "help",
    ]

    for page in pages:
        app = AppTest.from_file("app.py", default_timeout=30)
        app.query_params["page"] = page
        app.run()
        assert not app.exception, page


def test_bundled_csv_can_be_selected_in_the_ui():
    app = AppTest.from_file("app.py", default_timeout=30).run()
    app.selectbox[0].set_value("제공된 CSV 예제").run()

    assert not app.exception
    assert len(app.selectbox) == 3
