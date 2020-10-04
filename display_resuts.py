import pprint

data = {}

with open("results.txt", "r") as results_file:
    lines = results_file.readlines()

    for i in range(0, len(lines), 5):
        date = lines[i][6:].strip()
        gen = lines[i + 1][13:].strip()
        pop_size = lines[i + 2][9:].strip()
        max_score = lines[i + 3][11:].strip()
        data[date] = {
            "generations": int(gen),
            "pop_size": int(pop_size),
            "max_score": int(max_score)
        }


pprint.pprint(data)





