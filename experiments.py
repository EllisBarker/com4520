import csv
import datetime
import os

from fsm_gen.generator import FSMGenerator
from fsm_gen.mutator import Mutator
from walks.hsi import generate_HSI_suite
from walks.random_walk import RandomWalk

FILENAME = f"results/{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"

def write_to_csv(state_size, input_size, percent, walk_type, result):
    with open(FILENAME, mode="a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([state_size, input_size, percent, result["hsi_len"], walk_type, result["walk_len"], result["detected_fault_index"], result["time_taken"]])


def run_walk(state_size, input_size, percent, walk_type):
    fsm = FSMGenerator(state_size, input_size)
    hsi_suite = generate_HSI_suite(fsm)
    mutator = Mutator(fsm)
    mutated_fsm = mutator.create_mutated_fsm()
    
    walker = RandomWalk(fsm, mutated_fsm, percent, hsi_suite)

    start_time = datetime.datetime.now()
    walk = walker.walk(walk_type)
    end_time = datetime.datetime.now()
    detected_fault = walker.detected_fault(walk)

    results = {
        "hsi_len": len(hsi_suite),
        "walk_len": len(walk) if type(walk) == list else walk,
        "detected_fault_index": detected_fault,
        "time_taken": end_time - start_time
    }

    write_to_csv(state_size, input_size, percent, walk_type, results)


def main():
    state_sizes = [5, 10, 20, 40]
    input_size_multipliers = {"2": 2, "n/2": 0.5, "n": 1, "2n": 2}
    percent_coverage = [80, 90, 95, 99.5]

    if not os.path.exists("results"):
        os.mkdir("results")

    with open(FILENAME, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["State Size", "Input Size", "Percent Coverage", "HSI Suite Length", "Walk Type", "Walk Length", "Detected Fault Index", "Time Taken"])

    for state_size in state_sizes:
        for input_size_multiplier in input_size_multipliers:
            if state_size >= 20 and input_size_multiplier == "2":
                continue

            input_size = 2 if input_size_multiplier == "2" else int(state_size * input_size_multipliers[input_size_multiplier])

            for _ in range(20):
                for walk_type in RandomWalk.WalkType:
                    for percent in percent_coverage:
                        run_walk(state_size, input_size, percent, walk_type)

if __name__ == "__main__":
    main()