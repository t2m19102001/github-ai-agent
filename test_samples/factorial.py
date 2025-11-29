def calculate_factorial(n):
    """Calculate factorial of n"""
    if n <= 1:
        return 1
    return n * calculate_factorial(n - 1)

if __name__ == "__main__":
    result = calculate_factorial(5)
    print(f"Factorial of 5: {result}")
