def calculate_total(items):
    """
    Calculate the total of all item prices in the given list.

    Args:
        items (list): A list of dictionaries, where each dictionary has a 'price' key.

    Returns:
        float: The total of all item prices.
    """
    total = 0
    for item in items:
        try:
            total += item['price']
        except KeyError:
            print(f"Warning: Item {item} is missing a 'price' key. Skipping.")
    return total

