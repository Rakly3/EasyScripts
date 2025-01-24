# Terminal colors
INFO_COLOR = "\033[94m"  # Light blue
WARNING_COLOR = "\033[93m"  # Yellow
ERROR_COLOR = "\033[91m"  # Light red
END_COLOR = "\033[0m"  # Reset to default color


def iprint(text):
    """Print text in info color"""
    print(f"{INFO_COLOR}{text}{END_COLOR}")


def wprint(text):
    """Print text in warning color"""
    print(f"{WARNING_COLOR}{text}{END_COLOR}")


def eprint(text):
    """Print text in error color"""
    print(f"{ERROR_COLOR}{text}{END_COLOR}")
