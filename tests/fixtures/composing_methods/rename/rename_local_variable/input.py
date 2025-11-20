def sum_numbers(numbers):
    """Sum all numbers in a list."""
    count = 0
    for num in numbers:
        count += num
    return count


result = sum_numbers([1, 2, 3, 4, 5])
print(result)
