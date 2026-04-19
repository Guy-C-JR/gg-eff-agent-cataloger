from pathlib import Path

from gg_eff_agent_cataloger.readme_analysis import find_broken_local_links


def test_find_broken_local_links(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "ok.md").write_text("ok", encoding="utf-8")

    readme = """
[good](docs/ok.md)
[bad](docs/missing.md)
[external](https://example.com)
"""

    broken = find_broken_local_links(tmp_path, readme)
    assert broken == ["docs/missing.md"]
