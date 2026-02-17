#!/usr/bin/env python3

import glob
import os
import csv

pattern = "./data/jealousy/experiments/*/data.csv"

print("experiment\tg1_j1\tg1_j2\tg2_j1\tg2_j2")

for filepath in glob.glob(pattern):
    # Extract experiment name (the * part)
    experiment = os.path.basename(os.path.dirname(filepath))

    counts = {
        (1, 1): 0,
        (1, 2): 0,
        (2, 1): 0,
        (2, 2): 0,
    }

    with open(filepath, newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            try:
                gender = int(row["Gender"])
                jealousy = int(row["Jealousy"])
            except (KeyError, TypeError, ValueError):
                # Skip malformed rows
                continue

            if (gender, jealousy) in counts:
                counts[(gender, jealousy)] += 1

    print(
        f"{experiment}\t"
        f"{counts[(1,1)]}\t"
        f"{counts[(1,2)]}\t"
        f"{counts[(2,1)]}\t"
        f"{counts[(2,2)]}"
    )