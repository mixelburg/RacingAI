#  Copyright (c) 2020. Ivan Krokha (Mixelburg)
import concurrent.futures
import subprocess
from colorama import Fore
import colorama
import time
colorama.init()

NUM = 10
NUM_SIMULATIONS = 5

for pop_size in range(30, 10, -2):
    with open("config-feedforward.txt", "r+") as config_file:
        lines = config_file.readlines()
        lines[3] = f"pop_size              = {pop_size}\n"

    with open("config-feedforward.txt", "w") as config_file:
        config_file.writelines(lines)

    start_time = time.time()

    for k in range(NUM):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            for i in range(NUM_SIMULATIONS):
                print(f"""
                {Fore.GREEN}
                NUM: {k + 1}/{NUM}
                RUNNING SIMULATION {i + 1}/{NUM_SIMULATIONS}
                POP_SIZE: {pop_size}
                {Fore.RESET}
                """)

                executor.submit(subprocess.run, "venv/Scripts/python.exe main.py")
    print(f"""
    {Fore.RED}
    --- {float(time.time() - start_time)} seconds---
    --- {float(time.time() - start_time) / 60} minutes---
    {Fore.RESET}
    """)
