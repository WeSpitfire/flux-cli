
def test_count_lines_of_code():
    """Test counting lines of code in a file."""
    code = '''
# This is a comment

def foo():
    pass

# Another comment

def bar():
    pass

'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        f.flush()
        path = Path(f.name)

    try:
        loc = count_lines_of_code(path)
        assert loc == 4  # Only the function definitions and 'pass' lines are counted
    finally:
        path.unlink()

def test_count_lines_of_code_empty_file():
    """Test counting lines of code in an empty file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.flush()
        path = Path(f.name)

    try:
        loc = count_lines_of_code(path)
        assert loc == 0
    finally:
        path.unlink()
