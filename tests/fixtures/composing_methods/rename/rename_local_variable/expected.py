def sum_numbers(numbers):
    """Sum all numbers in a list."""
    total = 0
    for num in numbers:
        total += num
    return total


result = sum_numbers([1, 2, 3, 4, 5])
print(result)
