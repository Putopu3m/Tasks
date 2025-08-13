import json
import random
import time
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
from multiprocessing import Pool, Process, Queue, cpu_count
from typing import Callable, List


def generate_data(n: int) -> List[int]:
    return [random.randint(1, 1000) for _ in range(n)]


def timer(func: Callable):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        return {"result": result, "elapsed": elapsed}

    return wrapper


def miller_rabin_test(n: int = 5) -> bool:
    if n < 2:
        return False
    small_primes = (2, 3, 5, 7, 11)
    if n in small_primes:
        return True
    if any(n % p == 0 for p in small_primes):
        return False

    d = n - 1
    s = 0
    while d % 2 == 0:
        d //= 2
        s += 1

    def _try(a: int) -> bool:
        x = pow(a, d, n)
        if x == 1 or x == n - 1:
            return True
        for _ in range(s - 1):
            x = (x * x) % n
            if x == n - 1:
                return True
        return False

    for a in small_primes:
        if a % n == 0:
            continue
        if not _try(a):
            return False
    return True


@timer
def thread_pool(func: Callable, iterable: List) -> List:
    with ThreadPoolExecutor() as executor:
        results = executor.map(func, iterable)

    return results


@timer
def process_pool(func: Callable, iterable: List) -> List:
    with Pool(processes=cpu_count()) as pool:
        results = pool.map(func, iterable)

    return results


def worker(tasks_queue: Queue, results_queue: Queue, func):
    batch = []
    batch_size = 500
    while True:
        item = tasks_queue.get()
        if item is None:
            if batch:
                results_queue.put(batch)
            break
        batch.append(func(item))
        if len(batch) >= batch_size:
            results_queue.put(batch)
            batch = []


@timer
def processes_queue(func, iterable, num_workers=cpu_count()):
    tasks_queue = Queue()
    results_queue = Queue()

    processes = [
        Process(target=worker, args=(tasks_queue, results_queue, func))
        for _ in range(num_workers)
    ]

    for p in processes:
        p.start()

    for item in iterable:
        tasks_queue.put(item)

    for _ in range(num_workers):
        tasks_queue.put(None)

    results = []

    while len(results) < len(iterable):
        batch = results_queue.get()
        results.extend(batch)

    for p in processes:
        p.join()

    return results


@timer
def sync(func: Callable, iterable: List) -> List:
    return [func(item) for item in iterable]


def create_plot(funcs: List[Callable], elapsed_results: List):
    try:
        import matplotlib.pyplot as plt
    except ModuleNotFoundError as e:
        print(str(e))
        return

    plt.bar(list(map(lambda func: func.__name__, funcs)), elapsed_results)
    plt.title("Параллельная обработка числовых данных")
    plt.xlabel("Методы")
    plt.ylabel("Затраченное время")
    plt.savefig("elapsed_time.png")


if __name__ == "__main__":
    numbers = generate_data(1000000)

    funcs = [
        sync,
        process_pool,
        processes_queue,
        thread_pool,
    ]

    elapsed_results = [func(miller_rabin_test, numbers)["elapsed"] for func in funcs]
    create_plot(funcs, elapsed_results)

    results = []
    for func_name, elapsed_time in zip(
        [func.__name__ for func in funcs], elapsed_results
    ):
        results.append({func_name: elapsed_time})

    with open("results.json", "w+", encoding="utf-8") as file:
        file.write(json.dumps(results, ensure_ascii=False))
