# code from: https://matplotlib.org/stable/gallery/lines_bars_and_markers/barchart.html on how to make pair bar charts
# and: https://docs.python.org/3/library/csv.html on how to use CSVs
# and: https://evanhahn.com/python-skip-header-csv-reader/ to skip headers with dictionary readers
# and: https://stackabuse.com/rotate-axis-labels-in-matplotlib/ to rotate the ticks on the x axist

import matplotlib.pyplot as plt
import numpy as np
import csv

MAX_NAME_WIDTH = 5

with open('results-vector.csv', newline='') as csvfile:
    licmreader = csv.DictReader(csvfile, delimiter=',', quotechar='|')

    benchmark_names = []
    op = []
    naive = []
    baseline = []
    for row in licmreader:
        name = row["benchmark"]
        if len(name) > MAX_NAME_WIDTH:
            name = name[:MAX_NAME_WIDTH]
        if name not in benchmark_names:
            benchmark_names.append(name)
        run_type = row["run"]
        result = row["result"]
        if run_type == "op":
            op.append(float(result))
        elif run_type == "naive":
            naive.append(float(result))
        elif run_type == "baseline":
            baseline.append(float(result))
        else:
            raise RuntimeError(f"Malformed Type {run_type}.")

    assert len(op) == len(naive) == len(baseline) == len(benchmark_names)

    x = np.arange(len(benchmark_names))  # the label locations
    width = 0.35  # the width of the bars

    fig, ax = plt.subplots()
    rects2 = ax.bar(x + width/2, naive, width, label='Naive')
    rects3 = ax.bar(x + width/2, op, width, label='Opportunistic')

    # Add some text for labels, title and custom x-axis tick labels, etc.
    ax.set_ylabel('Number of Vectors Created')
    ax.set_title(
        'Number of Vectors Created Dynamically in 2 Different Vectorization Strategies')
    ax.set_xticks(x, benchmark_names)
    plt.xticks(rotation=45)
    ax.legend()

    ax.bar_label(rects2, padding=3)
    ax.bar_label(rects3, padding=3)

    fig.tight_layout()

    plt.show()
