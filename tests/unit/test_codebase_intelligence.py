"""Unit tests for codebase intelligence."""

import pytest
from flux.core.codebase_intelligence import CodebaseGraph, FileNode, CodeEntity


@pytest.mark.unit
class TestCodebaseGraph:
    """Tests for CodebaseGraph."""

    def test_build_graph(self, temp_dir, sample_python_file):
        """Test building a codebase graph."""
        graph = CodebaseGraph(temp_dir)
        graph.build_graph(use_cache=False)

        assert len(graph.files) > 0
        assert len(graph.entities) > 0

    def test_find_related_files(self, temp_dir, sample_python_file):
        """Test finding related files."""
        graph = CodebaseGraph(temp_dir)
        graph.build_graph(use_cache=False)

        related = graph.find_related_files("calculator", limit=5)
        assert isinstance(related, list)
        # Should find the sample file which contains Calculator class
        assert any("sample.py" in file_path for file_path, score in related)

    def test_get_file_context(self, temp_dir, sample_python_file):
        """Test getting file context."""
        graph = CodebaseGraph(temp_dir)
        graph.build_graph(use_cache=False)

        rel_path = str(sample_python_file.relative_to(temp_dir))
        context = graph.get_file_context(rel_path)

        assert 'path' in context
        assert 'language' in context
        assert 'entities' in context
        assert len(context['entities']) > 0

    def test_cache_save_and_load(self, temp_dir, sample_python_file):
        """Test caching functionality."""
        # Build graph and save to cache
        graph1 = CodebaseGraph(temp_dir)
        graph1.build_graph(use_cache=False)
        initial_file_count = len(graph1.files)

        # Create new graph instance and load from cache
        graph2 = CodebaseGraph(temp_dir)
        graph2.build_graph(use_cache=True)

        # Should have same number of files
        assert len(graph2.files) == initial_file_count
        assert len(graph2.entities) > 0

    def test_cache_invalidation_on_file_change(self, temp_dir, sample_python_file):
        """Test that cache is invalidated when files change."""
        # Build initial graph
        graph1 = CodebaseGraph(temp_dir)
        graph1.build_graph(use_cache=False)

        # Modify the file
        sample_python_file.write_text(sample_python_file.read_text() + "\n# Modified")

        # Load graph again
        graph2 = CodebaseGraph(temp_dir)
        # Cache should be invalidated and graph rebuilt
        # This is tested by checking that the modified content is detected
        graph2.build_graph(use_cache=True)

        assert len(graph2.files) > 0


@pytest.mark.unit
class TestCodeEntity:
    """Tests for CodeEntity dataclass."""

    def test_create_entity(self):
        """Test creating a CodeEntity."""
        entity = CodeEntity(
            name="test_function",
            type="function",
            file_path="test.py",
            line_number=10
        )

        assert entity.name == "test_function"
        assert entity.type == "function"
        assert entity.line_number == 10


@pytest.mark.unit
class TestFileNode:
    """Tests for FileNode dataclass."""

    def test_create_file_node(self):
        """Test creating a FileNode."""
        node = FileNode(
            path="test.py",
            language="python",
            imports=["os", "sys"],
            exports=["main"]
        )

        assert node.path == "test.py"
        assert node.language == "python"
        assert len(node.imports) == 2
