"""Tests for the 3-panel mesh comparison feature (issue #31, Phase 3/029).

Covers: site build artifacts, HTML structure, CSS coverage, manifest data
readiness, and Python equivalents of compare.js pure-logic functions.

Browser-level concerns (console errors, toggle interaction, visual rendering)
require manual testing — see specs/031-compare-test-validate/spec.md.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]


REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "registry_data" / "manifest.toml"
SITE_SRC = REPO_ROOT / "site" / "src"
SITE_DIST = REPO_ROOT / "site" / "dist"
COMPARE_HTML_SRC = SITE_SRC / "compare.html"
COMPARE_JS_SRC = SITE_SRC / "js" / "compare.js"
STYLES_CSS_SRC = SITE_SRC / "styles.css"
NAV_JS_SRC = SITE_SRC / "js" / "nav.js"

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def manifest():
    with open(MANIFEST_PATH, "rb") as f:
        return tomllib.load(f)


@pytest.fixture(scope="module")
def compare_html_text():
    return COMPARE_HTML_SRC.read_text()


@pytest.fixture(scope="module")
def styles_text():
    return STYLES_CSS_SRC.read_text()


@pytest.fixture(scope="module")
def compare_js_text():
    return COMPARE_JS_SRC.read_text()


@pytest.fixture(scope="module")
def nav_js_text():
    return NAV_JS_SRC.read_text()


# ---------------------------------------------------------------------------
# Site build
# ---------------------------------------------------------------------------

class TestSiteBuild:
    def test_site_builds_cleanly(self):
        result = subprocess.run(
            [sys.executable, "scripts/build_site.py"],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        assert result.returncode == 0, f"build_site.py failed:\n{result.stderr}"

    def test_compare_html_in_dist(self):
        assert (SITE_DIST / "compare.html").exists(), "compare.html not found in site/dist"

    def test_compare_js_in_dist(self):
        # compare.js may be hashed; check for any compare*.js file
        js_files = list((SITE_DIST / "js").glob("compare*.js")) if (SITE_DIST / "js").exists() else []
        # Also accept a flat dist layout
        flat_files = list(SITE_DIST.glob("compare*.js"))
        assert js_files or flat_files or (SITE_DIST / "js" / "compare.js").exists(), \
            "compare.js not found in site/dist"

    def test_styles_in_dist(self):
        css_files = list(SITE_DIST.glob("*.css")) + list(SITE_DIST.glob("styles*.css"))
        assert css_files, "No CSS file found in site/dist"

    def test_dist_has_expected_file_count(self):
        all_files = list(SITE_DIST.rglob("*"))
        file_count = sum(1 for f in all_files if f.is_file())
        assert file_count >= 20, f"site/dist seems sparse: {file_count} files"


# ---------------------------------------------------------------------------
# HTML structure
# ---------------------------------------------------------------------------

class TestCompareHtmlStructure:
    REQUIRED_IDS = ["domain-select", "compare-btn", "compare-panels", "compare-banner"]

    def test_required_ids_present(self, compare_html_text):
        for id_ in self.REQUIRED_IDS:
            assert f'id="{id_}"' in compare_html_text, \
                f"Missing id={id_!r} in compare.html"

    def test_title_tag_present(self, compare_html_text):
        assert "<title>" in compare_html_text

    def test_title_contains_compare(self, compare_html_text):
        import re
        match = re.search(r"<title>(.*?)</title>", compare_html_text, re.IGNORECASE)
        assert match and "compare" in match.group(1).lower(), \
            "Page <title> should mention 'Compare'"

    def test_viewport_meta_present(self, compare_html_text):
        assert 'name="viewport"' in compare_html_text, \
            "Missing viewport meta for responsive behaviour"

    def test_compare_js_script_tag(self, compare_html_text):
        assert "compare.js" in compare_html_text, \
            "compare.js not referenced in compare.html"

    def test_script_type_module(self, compare_html_text):
        assert 'type="module"' in compare_html_text, \
            "Script tag should use type='module' for ES import support"

    def test_styles_css_linked(self, compare_html_text):
        assert "styles.css" in compare_html_text, \
            "compare.html does not link styles.css"

    def test_aria_live_on_dynamic_regions(self, compare_html_text):
        assert "aria-live" in compare_html_text, \
            "Dynamic compare-panels / compare-banner should have aria-live"

    def test_compare_html_in_nav_pages(self, nav_js_text):
        assert "compare.html" in nav_js_text, \
            "compare.html must appear in nav.js PAGES array"

    def test_header_footer_divs_present(self, compare_html_text):
        assert 'id="site-header"' in compare_html_text
        assert 'id="site-footer"' in compare_html_text


# ---------------------------------------------------------------------------
# CSS coverage
# ---------------------------------------------------------------------------

class TestCompareCSS:
    def test_compare_grid_defined(self, styles_text):
        assert ".compare-grid" in styles_text, "Missing .compare-grid in styles.css"

    def test_compare_panel_defined(self, styles_text):
        assert ".compare-panel" in styles_text, "Missing .compare-panel in styles.css"

    def test_compare_banner_defined(self, styles_text):
        assert ".compare-banner" in styles_text, "Missing .compare-banner in styles.css"

    def test_compare_controls_defined(self, styles_text):
        assert ".compare-controls" in styles_text, "Missing .compare-controls in styles.css"

    def test_thumb_svg_defined(self, styles_text):
        assert ".thumb-svg" in styles_text, \
            "Missing .thumb-svg; used by bboxSvg() for mesh thumbnails"

    def test_responsive_mobile_single_column(self, styles_text):
        assert "grid-template-columns: 1fr" in styles_text or \
               "grid-template-columns:1fr" in styles_text, \
            "Mobile CSS should stack compare panels to single column"

    def test_responsive_breakpoint_max_width_present(self, styles_text):
        assert "max-width" in styles_text, \
            "Responsive max-width media query missing from styles.css"

    def test_compare_grid_three_column_desktop(self, styles_text):
        assert "repeat(3, 1fr)" in styles_text or "repeat(3,1fr)" in styles_text, \
            "compare-grid should use 3-column layout on desktop"


# ---------------------------------------------------------------------------
# compare.js source checks
# ---------------------------------------------------------------------------

class TestCompareJsSource:
    REQUIRED_FUNS = ["inferStrategy", "groupVariants", "recommend", "renderPanels", "bboxSvg"]

    def test_required_functions_defined(self, compare_js_text):
        for fn in self.REQUIRED_FUNS:
            assert f"function {fn}" in compare_js_text, \
                f"Function {fn!r} not found in compare.js"

    def test_imports_nav_and_manifest_loader(self, compare_js_text):
        assert "nav.js" in compare_js_text
        assert "manifest-loader" in compare_js_text

    def test_strategy_keys_defined(self, compare_js_text):
        for key in ("triangle", "quad", "mixed"):
            assert key in compare_js_text, f"Strategy key {key!r} missing from compare.js"

    def test_element_type_used_for_inference(self, compare_js_text):
        assert "element_type" in compare_js_text, \
            "inferStrategy() should inspect mesh.element_type"

    def test_empty_variant_note_handled(self, compare_js_text):
        assert "compare-empty" in compare_js_text, \
            "compare.js should handle zero-variant case with .compare-empty message"


# ---------------------------------------------------------------------------
# Manifest data readiness
# ---------------------------------------------------------------------------

class TestManifestCompareData:
    def test_manifest_has_domains(self, manifest):
        assert manifest.get("domains"), "manifest.toml must have at least one domain"

    def test_rectangles_domain_exists(self, manifest):
        names = [d["name"] for d in manifest["domains"]]
        assert "Rectangles" in names, "Rectangles domain not in manifest"

    def test_rectangles_has_triangle_element_type(self, manifest):
        rect = next(d for d in manifest["domains"] if d["name"] == "Rectangles")
        tri = [m for m in rect["meshes"] if m.get("element_type") == "triangle"]
        assert tri, "Rectangles domain needs at least one mesh with element_type=triangle"

    def test_rectangles_has_quad_element_type(self, manifest):
        rect = next(d for d in manifest["domains"] if d["name"] == "Rectangles")
        quad = [m for m in rect["meshes"] if m.get("element_type") == "quadrilateral"]
        assert quad, "Rectangles domain needs at least one mesh with element_type=quadrilateral"

    def test_at_least_one_multi_strategy_domain(self, manifest):
        """At least one domain must yield >=2 grouped variants for comparison."""
        multi = [d for d in manifest["domains"] if len(_group_variants(d)) >= 2]
        assert multi, (
            "No domain has >=2 detectable mesh strategies. "
            "Add element_type or tri/quad/mixed filename hints to manifest."
        )

    def test_compare_page_data_is_not_empty(self, manifest):
        """compare.html would NOT show 'no variants' for all domains."""
        any_variants = any(len(_group_variants(d)) >= 1 for d in manifest["domains"])
        assert any_variants, "All domains return empty variants -- compare page unusable"


# ---------------------------------------------------------------------------
# Pure-logic equivalents of compare.js functions
# (These are Python mirrors of the JS to enable unit testing without a browser)
# ---------------------------------------------------------------------------

_STRATEGIES = [
    {"key": "triangle",  "label": "Triangle",      "typeMatch": "triangle",      "nameHint": "tri"},
    {"key": "quad",      "label": "Quad-Dominant", "typeMatch": "quadrilateral", "nameHint": "quad"},
    {"key": "mixed",     "label": "Mixed",         "typeMatch": "mixed",         "nameHint": "mixed"},
]


def _infer_strategy(mesh: dict) -> str | None:
    et = (mesh.get("element_type") or "").lower()
    fn = (mesh.get("filename") or "").lower()
    for s in _STRATEGIES:
        if et == s["typeMatch"]:
            return s["key"]
    for s in _STRATEGIES:
        if s["nameHint"] in fn:
            return s["key"]
    return None


def _group_variants(domain: dict) -> list[dict]:
    groups: dict[str, dict] = {}
    for mesh in domain.get("meshes", []):
        strategy = _infer_strategy(mesh)
        if not strategy or strategy in groups:
            continue
        groups[strategy] = mesh
    return [
        {"strategy": s["key"], "label": s["label"], "mesh": groups[s["key"]]}
        for s in _STRATEGIES
        if s["key"] in groups
    ]


def _recommend(variants: list[dict]) -> str:
    with_count = [v for v in variants if (v["mesh"].get("element_count") or 0) > 0]
    if len(with_count) > 1:
        best = min(with_count, key=lambda v: v["mesh"]["element_count"])
        return best["label"]
    with_size = [v for v in variants if (v["mesh"].get("size_mb") or 0) > 0]
    if len(with_size) > 1:
        best = min(with_size, key=lambda v: v["mesh"]["size_mb"])
        return best["label"]
    return ""


class TestInferStrategy:
    def test_triangle_by_element_type(self):
        assert _infer_strategy({"element_type": "triangle"}) == "triangle"

    def test_quad_by_element_type(self):
        assert _infer_strategy({"element_type": "quadrilateral"}) == "quad"

    def test_mixed_by_element_type(self):
        assert _infer_strategy({"element_type": "mixed"}) == "mixed"

    def test_triangle_by_filename(self):
        assert _infer_strategy({"filename": "gulf_tri.14"}) == "triangle"

    def test_quad_by_filename(self):
        assert _infer_strategy({"filename": "gulf_quad.14"}) == "quad"

    def test_mixed_by_filename(self):
        assert _infer_strategy({"filename": "mixed_test.14"}) == "mixed"

    def test_element_type_takes_priority_over_filename(self):
        mesh = {"element_type": "triangle", "filename": "mixed_test.14"}
        assert _infer_strategy(mesh) == "triangle"

    def test_case_insensitive_element_type(self):
        assert _infer_strategy({"element_type": "TRIANGLE"}) == "triangle"
        assert _infer_strategy({"element_type": "Quadrilateral"}) == "quad"

    def test_unknown_returns_none(self):
        assert _infer_strategy({"filename": "default.14"}) is None
        assert _infer_strategy({}) is None
        assert _infer_strategy({"element_type": ""}) is None

    def test_none_fields_handled(self):
        assert _infer_strategy({"element_type": None, "filename": None}) is None


class TestGroupVariants:
    def test_rectangles_domain_yields_two_strategies(self, manifest):
        rect = next(d for d in manifest["domains"] if d["name"] == "Rectangles")
        variants = _group_variants(rect)
        assert len(variants) >= 2
        keys = {v["strategy"] for v in variants}
        assert "triangle" in keys
        assert "quad" in keys

    def test_deduplicates_same_strategy(self):
        domain = {
            "meshes": [
                {"element_type": "triangle", "filename": "a.14"},
                {"element_type": "triangle", "filename": "b.14"},
            ]
        }
        variants = _group_variants(domain)
        assert len(variants) == 1
        assert variants[0]["strategy"] == "triangle"

    def test_empty_meshes_returns_empty(self):
        assert _group_variants({"meshes": []}) == []
        assert _group_variants({}) == []

    def test_no_strategy_hints_returns_empty(self):
        domain = {"meshes": [{"filename": "default.14"}, {"filename": "variant2.14"}]}
        assert _group_variants(domain) == []

    def test_all_three_strategies_found(self):
        domain = {
            "meshes": [
                {"element_type": "triangle"},
                {"element_type": "quadrilateral"},
                {"element_type": "mixed"},
            ]
        }
        variants = _group_variants(domain)
        assert len(variants) == 3
        keys = {v["strategy"] for v in variants}
        assert keys == {"triangle", "quad", "mixed"}

    def test_preserves_strategy_order(self):
        domain = {
            "meshes": [
                {"element_type": "mixed"},
                {"element_type": "quadrilateral"},
                {"element_type": "triangle"},
            ]
        }
        variants = _group_variants(domain)
        keys = [v["strategy"] for v in variants]
        assert keys == ["triangle", "quad", "mixed"]

    def test_label_matches_strategy(self):
        domain = {"meshes": [{"element_type": "quadrilateral"}]}
        variants = _group_variants(domain)
        assert variants[0]["label"] == "Quad-Dominant"


class TestRecommend:
    def test_picks_fewest_elements(self):
        variants = [
            {"strategy": "triangle",  "label": "Triangle",      "mesh": {"element_count": 60000}},
            {"strategy": "quad",      "label": "Quad-Dominant", "mesh": {"element_count": 35000}},
            {"strategy": "mixed",     "label": "Mixed",         "mesh": {"element_count": 40000}},
        ]
        assert _recommend(variants) == "Quad-Dominant"

    def test_falls_back_to_smallest_file_when_no_counts(self):
        variants = [
            {"strategy": "triangle",  "label": "Triangle",      "mesh": {"size_mb": 1.5}},
            {"strategy": "quad",      "label": "Quad-Dominant", "mesh": {"size_mb": 0.8}},
        ]
        assert _recommend(variants) == "Quad-Dominant"

    def test_empty_when_single_variant_with_count(self):
        variants = [
            {"strategy": "triangle", "label": "Triangle", "mesh": {"element_count": 1000}},
        ]
        assert _recommend(variants) == ""

    def test_empty_when_no_counts_or_sizes(self):
        variants = [
            {"strategy": "triangle",  "label": "Triangle",      "mesh": {}},
            {"strategy": "quad",      "label": "Quad-Dominant", "mesh": {}},
        ]
        assert _recommend(variants) == ""

    def test_empty_when_counts_are_zero(self):
        variants = [
            {"strategy": "triangle",  "label": "Triangle",      "mesh": {"element_count": 0}},
            {"strategy": "quad",      "label": "Quad-Dominant", "mesh": {"element_count": 0}},
        ]
        assert _recommend(variants) == ""

    def test_element_count_wins_over_size(self):
        variants = [
            {"strategy": "triangle",  "label": "Triangle",      "mesh": {"element_count": 100, "size_mb": 5.0}},
            {"strategy": "quad",      "label": "Quad-Dominant", "mesh": {"element_count": 50,  "size_mb": 0.1}},
        ]
        assert _recommend(variants) == "Quad-Dominant"

    def test_only_one_has_count_no_recommendation(self):
        # Only 1 of 2 has element_count -- can't compare, falls back to size
        variants = [
            {"strategy": "triangle",  "label": "Triangle",      "mesh": {"element_count": 100, "size_mb": 0}},
            {"strategy": "quad",      "label": "Quad-Dominant", "mesh": {"size_mb": 0}},
        ]
        assert _recommend(variants) == ""


# ---------------------------------------------------------------------------
# Edge-case integration
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_domain_with_no_strategy_meshes_yields_empty(self):
        domain = {
            "name": "NakedDomain",
            "meshes": [{"filename": "default.14"}, {"filename": "variant2.14"}],
        }
        assert _group_variants(domain) == []

    def test_partial_coverage_still_produces_variants(self, manifest):
        rect = next(d for d in manifest["domains"] if d["name"] == "Rectangles")
        variants = _group_variants(rect)
        # Rectangles has triangle+quad but not mixed -- partial is still valid
        assert len(variants) >= 2
        present = {v["strategy"] for v in variants}
        # Missing strategies documented as "Not in registry" note in compare.js
        assert "triangle" in present and "quad" in present

    def test_recommend_empty_on_current_manifest_data(self, manifest):
        # Current manifest has no element_count and Rectangles has size_mb=0
        # recommend() is expected to return "" -- no false recommendations
        rect = next(d for d in manifest["domains"] if d["name"] == "Rectangles")
        variants = _group_variants(rect)
        result = _recommend(variants)
        assert result == "", (
            "With no element_count or positive size_mb in manifest, "
            "recommend() should return '' (no banner shown)"
        )
