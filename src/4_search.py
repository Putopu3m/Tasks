def search(arr: list, number: int) -> bool:
    left_index, right_index = 0, len(arr) - 1
    while left_index <= right_index:
        mid_index = left_index + (right_index - left_index) // 2
        if arr[mid_index] == number:
            return True
        elif arr[mid_index] < number:
            left_index = mid_index + 1
        elif arr[mid_index] > number:
            right_index = mid_index - 1
    
    return False

print(search([1, 2, 3, 45, 356, 569, 600, 705, 923], 600))