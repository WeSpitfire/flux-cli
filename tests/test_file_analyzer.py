"""
Tests for FileStructureAnalyzer
"""

import tempfile
from pathlib import Path
import pytest

from flux.core.file_analyzer import FileStructureAnalyzer, FileStructure


class TestFileStructureAnalyzer:
    """Test the FileStructureAnalyzer"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.analyzer = FileStructureAnalyzer()
    
    def test_analyze_simple_function(self):
        """Test analyzing a file with a simple function"""
        code = '''
def hello(name):
    return f"Hello {name}"
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            path = Path(f.name)
        
        try:
            structure = self.analyzer.analyze(path)
            assert len(structure.functions) == 1
            assert structure.functions[0].name == 'hello'
            assert structure.functions[0].args == ['name']
        finally:
            path.unlink()
    
    def test_analyze_class_with_methods(self):
        """Test analyzing a class with multiple methods"""
        code = '''
class Calculator:
    def add(self, a, b):
        return a + b
    
    def subtract(self, a, b):
        return a - b
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            path = Path(f.name)
        
        try:
            structure = self.analyzer.analyze(path)
            assert len(structure.classes) == 1
            assert structure.classes[0].name == 'Calculator'
            assert len(structure.classes[0].methods) == 2
            assert 'add' in structure.classes[0].method_names
            assert 'subtract' in structure.classes[0].method_names
        finally:
            path.unlink()
    
    def test_detect_duplicate_function(self):
        """Test detecting duplicate function"""
        code = '''
def process_data(data):
    return data.strip()
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            path = Path(f.name)
        
        try:
            can_add, msg = self.analyzer.can_add_function(path, 'process_data')
            assert not can_add
            assert 'already exists' in msg
            assert 'process_data' in msg
        finally:
            path.unlink()
    
    def test_detect_duplicate_method(self):
        """Test detecting duplicate method in class"""
        code = '''
class DataProcessor:
    def process(self, data):
        return data
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            path = Path(f.name)
        
        try:
            can_add, msg = self.analyzer.can_add_function(
                path, 'process', target_class='DataProcessor'
            )
            assert not can_add
            assert 'already exists' in msg
            assert 'process' in msg
            assert 'DataProcessor' in msg
        finally:
            path.unlink()
    
    def test_can_add_new_function(self):
        """Test that new functions can be added"""
        code = '''
def existing_func():
    pass
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            path = Path(f.name)
        
        try:
            can_add, msg = self.analyzer.can_add_function(path, 'new_func')
            assert can_add
            assert msg == 'OK'
        finally:
            path.unlink()
    
    def test_find_insertion_point_after_function(self):
        """Test finding insertion point after last function"""
        code = '''
def func1():
    pass

def func2():
    pass
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            path = Path(f.name)
        
        try:
            line = self.analyzer.find_best_insertion_point(path)
            # Should be after last function + spacing
            assert line > 5
        finally:
            path.unlink()
    
    def test_find_insertion_point_in_class(self):
        """Test finding insertion point inside a class"""
        code = '''
class MyClass:
    def method1(self):
        pass
    
    def method2(self):
        pass
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            path = Path(f.name)
        
        try:
            line = self.analyzer.find_best_insertion_point(path, target_class='MyClass')
            # Should be after last method
            assert line > 6
        finally:
            path.unlink()
    
    def test_analyze_with_imports(self):
        """Test that imports are captured"""
        code = '''
import os
from pathlib import Path

def func():
    pass
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            path = Path(f.name)
        
        try:
            structure = self.analyzer.analyze(path)
            assert len(structure.imports) >= 1
        finally:
            path.unlink()
    
    def test_class_not_found_error(self):
        """Test error when target class not found"""
        code = '''
class ExistingClass:
    pass
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            path = Path(f.name)
        
        try:
            can_add, msg = self.analyzer.can_add_function(
                path, 'new_method', target_class='NonExistentClass'
            )
            assert not can_add
            assert 'not found' in msg
        finally:
            path.unlink()
    
    def test_syntax_error_handling(self):
        """Test that syntax errors are caught"""
        code = '''
def broken function(:
    pass
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            path = Path(f.name)
        
        try:
            with pytest.raises(SyntaxError):
                self.analyzer.analyze(path)
        finally:
            path.unlink()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
