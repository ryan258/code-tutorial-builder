import json

import pytest
from code_tutorial_builder.scanner import (
    LearningOpportunity,
    ScanResult,
    scan_project,
    _score_file,
    _max_dependency_depth,
    _estimate_difficulty,
    _generate_title,
    _generate_rationale,
    _walk_source_files,
    FileAnalysis,
    read_gitnexus_meta,
)
from code_tutorial_builder.analysis import Component, ProgramAnalysis, analyze
from code_tutorial_builder.languages import PythonParser, get_profile


class TestScanProject:
    def test_scans_python_files(self, tmp_path):
        (tmp_path / "hello.py").write_text("def greet():\n    print('hi')\n")
        result = scan_project(tmp_path)
        assert result.files_scanned == 1
        assert len(result.opportunities) == 1

    def test_skips_hidden_and_venv_dirs(self, tmp_path):
        (tmp_path / ".venv").mkdir()
        (tmp_path / ".venv" / "lib.py").write_text("x = 1\n")
        (tmp_path / "node_modules").mkdir()
        (tmp_path / "node_modules" / "dep.py").write_text("x = 1\n")
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "mod.py").write_text("x = 1\n")
        (tmp_path / "real.py").write_text("def f():\n    return 1\n")

        result = scan_project(tmp_path)
        assert result.files_scanned == 1

    def test_skips_files_over_max_lines(self, tmp_path):
        (tmp_path / "big.py").write_text("x = 1\n" * 600)
        (tmp_path / "small.py").write_text("def f():\n    return 1\n")

        result = scan_project(tmp_path, max_file_lines=100)
        assert result.files_scanned == 1
        assert result.files_skipped == 1

    def test_max_opportunities_capped(self, tmp_path):
        for i in range(15):
            (tmp_path / f"mod{i}.py").write_text(
                f"def func{i}():\n    return {i}\n"
            )
        result = scan_project(tmp_path, max_opportunities=3)
        assert len(result.opportunities) <= 3

    def test_empty_directory(self, tmp_path):
        result = scan_project(tmp_path)
        assert result.files_scanned == 0
        assert result.opportunities == []

    def test_not_a_directory_raises(self, tmp_path):
        f = tmp_path / "file.py"
        f.write_text("x = 1\n")
        with pytest.raises(ValueError, match="Not a directory"):
            scan_project(f)

    def test_opportunities_sorted_by_score(self, tmp_path):
        # Simple file — low score
        (tmp_path / "simple.py").write_text("def f():\n    return 1\n")
        # Rich file — higher score
        (tmp_path / "rich.py").write_text(
            "def helper():\n    return 1\n\n"
            "def process(x):\n"
            "    if x > 0:\n"
            "        for i in range(x):\n"
            "            helper()\n"
            "    return x\n"
        )
        result = scan_project(tmp_path)
        assert len(result.opportunities) == 2
        assert result.opportunities[0].score >= result.opportunities[1].score

    def test_relative_paths_in_results(self, tmp_path):
        sub = tmp_path / "src"
        sub.mkdir()
        (sub / "mod.py").write_text("def f():\n    return 1\n")

        result = scan_project(tmp_path)
        assert result.opportunities[0].file_path == "src/mod.py"

    def test_ignores_unsupported_extensions(self, tmp_path):
        (tmp_path / "data.csv").write_text("a,b,c\n1,2,3\n")
        (tmp_path / "readme.md").write_text("# Hello\n")
        (tmp_path / "real.py").write_text("def f():\n    return 1\n")

        result = scan_project(tmp_path)
        assert result.files_scanned == 1

    def test_handles_parse_errors_gracefully(self, tmp_path):
        (tmp_path / "broken.py").write_text("def broken(:\n")
        (tmp_path / "good.py").write_text("def good():\n    return 1\n")

        result = scan_project(tmp_path)
        assert result.files_scanned == 1
        assert result.files_skipped == 1


class TestScoring:
    def _make_analysis(self, code):
        parser = PythonParser()
        profile = get_profile("python")
        parsed = parser.parse(code)
        graph = analyze(parsed, profile)
        return FileAnalysis(
            path=__import__("pathlib").Path("/fake/test.py"),
            language="python",
            parsed=parsed,
            graph=graph,
            profile=profile,
        )

    def test_concept_rich_file_scores_higher(self):
        simple = self._make_analysis("def f():\n    return 1\n")
        rich = self._make_analysis(
            "def f(n):\n"
            "    if n == 0:\n"
            "        return 1\n"
            "    return n * f(n - 1)\n"
        )
        root = __import__("pathlib").Path("/fake")
        simple_opp = _score_file(simple, root)
        rich_opp = _score_file(rich, root)
        assert rich_opp.score > simple_opp.score

    def test_dependency_rich_file_scores_higher(self):
        flat = self._make_analysis(
            "def a():\n    return 1\n\n"
            "def b():\n    return 2\n"
        )
        chained = self._make_analysis(
            "def a():\n    return 1\n\n"
            "def b():\n    return a()\n"
        )
        root = __import__("pathlib").Path("/fake")
        flat_opp = _score_file(flat, root)
        chained_opp = _score_file(chained, root)
        assert chained_opp.score > flat_opp.score


class TestMaxDependencyDepth:
    def test_no_dependencies(self):
        graph = ProgramAnalysis(
            components=[Component(name="a", kind="function", body="")],
            dependency_order=["a"],
            concepts=[],
            call_graph={"a": []},
            reverse_graph={"a": []},
        )
        assert _max_dependency_depth(graph) == 0

    def test_simple_chain(self):
        graph = ProgramAnalysis(
            components=[
                Component(name="a", kind="function", body="", calls=["b"]),
                Component(name="b", kind="function", body="", calls=["c"]),
                Component(name="c", kind="function", body="", calls=[]),
            ],
            dependency_order=["c", "b", "a"],
            concepts=[],
            call_graph={"a": ["b"], "b": ["c"], "c": []},
            reverse_graph={"a": [], "b": ["a"], "c": ["b"]},
        )
        assert _max_dependency_depth(graph) == 2

    def test_handles_cycles(self):
        graph = ProgramAnalysis(
            components=[
                Component(name="a", kind="function", body="", calls=["b"]),
                Component(name="b", kind="function", body="", calls=["a"]),
            ],
            dependency_order=["a", "b"],
            concepts=[],
            call_graph={"a": ["b"], "b": ["a"]},
            reverse_graph={"a": ["b"], "b": ["a"]},
        )
        # Should not infinite loop; depth is bounded
        depth = _max_dependency_depth(graph)
        assert depth >= 0


class TestEstimateDifficulty:
    def test_beginner(self):
        assert _estimate_difficulty(["iteration"], 1, 0) == "beginner"

    def test_intermediate(self):
        assert _estimate_difficulty(["iteration", "control flow"], 3, 1) == "intermediate"

    def test_advanced(self):
        assert _estimate_difficulty(
            ["recursion", "error handling", "state management"], 5, 3
        ) == "advanced"


class TestLearningOpportunity:
    def test_to_dict(self):
        opp = LearningOpportunity(
            title="Test",
            file_path="test.py",
            components=["f"],
            concepts=["iteration"],
            difficulty="beginner",
            score=0.75,
            rationale="Good lesson.",
            component_count=1,
            dependency_depth=0,
        )
        d = opp.to_dict()
        assert d["title"] == "Test"
        assert d["score"] == 0.75
        assert "gitnexus_context" not in d

    def test_to_dict_with_gitnexus(self):
        opp = LearningOpportunity(
            title="Test",
            file_path="test.py",
            components=[],
            concepts=[],
            difficulty="beginner",
            score=0.5,
            rationale="OK.",
            gitnexus_context={"index_available": True},
        )
        d = opp.to_dict()
        assert d["gitnexus_context"]["index_available"] is True


class TestScanResult:
    def test_to_json(self):
        result = ScanResult(
            root="/tmp",
            files_scanned=1,
            files_skipped=0,
            opportunities=[],
        )
        data = json.loads(result.to_json())
        assert data["files_scanned"] == 1
        assert data["opportunities"] == []


class TestGitNexusMeta:
    def test_reads_meta_json(self, tmp_path):
        gn = tmp_path / ".gitnexus"
        gn.mkdir()
        (gn / "meta.json").write_text('{"stats": {"nodes": 42}}')

        meta = read_gitnexus_meta(tmp_path)
        assert meta["stats"]["nodes"] == 42

    def test_returns_none_when_missing(self, tmp_path):
        assert read_gitnexus_meta(tmp_path) is None

    def test_scan_detects_gitnexus(self, tmp_path):
        gn = tmp_path / ".gitnexus"
        gn.mkdir()
        (gn / "meta.json").write_text('{"stats": {"nodes": 1}}')
        (tmp_path / "mod.py").write_text("def f():\n    return 1\n")

        result = scan_project(tmp_path)
        assert result.gitnexus_available is True
        assert result.opportunities[0].gitnexus_context is not None


class TestWalkSourceFiles:
    def test_walks_recursively(self, tmp_path):
        sub = tmp_path / "pkg"
        sub.mkdir()
        (tmp_path / "a.py").write_text("")
        (sub / "b.py").write_text("")

        files = _walk_source_files(tmp_path, {".py"})
        names = [f.name for f in files]
        assert "a.py" in names
        assert "b.py" in names

    def test_skips_egg_info(self, tmp_path):
        egg = tmp_path / "mylib.egg-info"
        egg.mkdir()
        (egg / "setup.py").write_text("")
        (tmp_path / "real.py").write_text("")

        files = _walk_source_files(tmp_path, {".py"})
        assert len(files) == 1
        assert files[0].name == "real.py"

    def test_skips_symlinked_directories(self, tmp_path):
        real = tmp_path / "real"
        real.mkdir()
        (real / "mod.py").write_text("")

        link = tmp_path / "linked"
        link.symlink_to(real)

        files = _walk_source_files(tmp_path, {".py"})
        assert len(files) == 1
        assert files[0].parent.name == "real"

    def test_survives_symlink_loop(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "mod.py").write_text("")
        (sub / "loop").symlink_to(tmp_path)

        # Must terminate without error
        files = _walk_source_files(tmp_path, {".py"})
        assert len(files) == 1
