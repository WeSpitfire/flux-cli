"""Test file to demonstrate auto-fix functionality."""


def hello_world():
    """Function with trailing whitespace."""
    print("Hello, World!")
    return True


def another_function():
    """Function with excessive blank lines above."""
    x = 1
    y = 2
    return x + y


class TestClass:
    """Class with formatting issues."""

    def method_one(self):
        """Method with trailing spaces."""
        pass


    def method_two(self):
        """Another method."""
        return "test"


# Some code with trailing whitespace
data = {
    "name": "test",
    "value": 123
}

