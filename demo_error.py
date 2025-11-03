def calculate_average(numbers):
    total = sum(numbers)
    return total / len(numbers)

def main():
    data = [1, 2, 3, 4, 5]
    result = calculate_average(data)
    print(f"Average: {result}")
    
    # This will cause an error
    print(f"Undefined: {undefined_variable}")
    
if __name__ == "__main__":
    main()