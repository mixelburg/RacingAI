import time
from pprint import pprint
from matplotlib import pyplot as plt

data = {}

with open("results.txt", "r") as results_file:
    lines = results_file.readlines()

    for i in range(0, len(lines), 5):
        date = lines[i][6:].strip()
        gen_num = int(lines[i + 1].split(":")[1].strip())
        pop_size = int(lines[i + 2].split(":")[1].strip())
        max_score = int(lines[i + 3].split(":")[1].strip())
        data[date] = {
            "num_gens": gen_num,
            "pop_size": pop_size,
            "max_score": max_score
        }

pop_sizes = list(dict.fromkeys([value["pop_size"] for value in data.values()]))
data_by_pop_sizes = {pop_size:[value["num_gens"] for value in data.values() if value["pop_size"] == pop_size]
                     for pop_size in pop_sizes}
for key, value in data_by_pop_sizes.items():
    print(f"{key}: {value}")
print()

data_by_pop_sizes = {k: v for k, v in sorted(data_by_pop_sizes.items(), key=lambda item: item[0])}
for key, value in data_by_pop_sizes.items():
    print(f"{key}: {value}")
print()

data_by_pop_sizes = {key:round(sum(val)/len(val), 2) for key, val in data_by_pop_sizes.items()}
for key, value in data_by_pop_sizes.items():
    print(f"{key}: {value}")
print()


pop_sizes = tuple(data_by_pop_sizes.keys())
avg_num_gen = tuple(data_by_pop_sizes.values())


plt.style.use("fivethirtyeight")
plt.plot(pop_sizes, avg_num_gen)
plt.xlabel("population sizes")
plt.ylabel("num generations")

plt.title("avg generations by pop sizes")
plt.grid(True)

plt.tight_layout()

plt.show()


