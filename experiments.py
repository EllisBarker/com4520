import csv
import datetime

from mpi4py import MPI
from tqdm import tqdm

from fsm_gen.generator import FSMGenerator
from fsm_gen.mutator import Mutator
from walks.hsi import generate_HSI_suite
from walks.random_walk import RandomWalk


def run_walk(state_size, input_size, index, percent, walk_type):
    fsm = FSMGenerator(state_size, input_size)
    mutator = Mutator(fsm)
    hsi_suite = generate_HSI_suite(fsm)
    mutated_fsm = mutator.create_mutated_fsm()
    
    walker = RandomWalk(mutated_fsm, percent, hsi_suite)

    start_time = datetime.datetime.now()
    walk_length = walker.walk(walk_type)
    end_time = datetime.datetime.now()

    results = {
        "hsi_len": len(hsi_suite),
        "walk_len": walk_length,
        "time_taken": end_time - start_time
    }

    return f"{len(fsm.states)}_{input_size}_{index}_{percent}_{walk_type}", results


def distribute_tasks(state_sizes, input_size_multipliers, percent_coverage):
    tasks = []
    for state_size in state_sizes:
        for input_size_key in input_size_multipliers.keys():
            if state_size >= 20 and input_size_key == "2":
                continue

            if input_size_key == "2":
                input_size = 2
            else:
                input_size = int(state_size * input_size_multipliers[input_size_key])

            for i in range(20):
                for walk_type in RandomWalk.WalkType:
                    for percent in percent_coverage:
                        tasks.append((state_size, input_size, i, percent, walk_type))

    return tasks
                

def main():
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()

    state_sizes = [5, 10, 20, 40]
    input_size_multipliers = {"2": 2, "n/2": 0.5, "n": 1, "2n": 2}
    percent_coverage = [80, 80, 95, 99.5]

    if rank == 0:
        tasks = distribute_tasks(state_sizes, input_size_multipliers, percent_coverage)
        total_tasks = len(tasks)
        chunks = [tasks[i::size] for i in range(size)]
        print(f"Running {total_tasks} tasks on {size} processes.")
    else:
        total_tasks = None
        chunks = None

    total_tasks = comm.bcast(total_tasks, root=0)
    task_chunk = comm.scatter(chunks, root=0)

    results = []

    for task in tqdm(task_chunk, desc=f"Rank {rank}", leave=True, position=rank, dynamic_ncols=True):
        state_size, input_size, index, percent, walk_type = task
        key, walk_results = run_walk(state_size, input_size, index, percent, walk_type)
        results.append((key, walk_results))

    all_results = comm.gather(results, root=0)

    if rank == 0:
        filename = f"result_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        with open(filename, mode="w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["State Size", "Input Size", "Percent Coverage", "HSI Suite Length", "Walk Type", "Walk Length", "Time Taken"])

            for result_set in all_results:
                for key, result in result_set:
                    state_size, input_size, _, percent, walk_type = key.split("_")
                    writer.writerow([state_size, input_size, percent, result["hsi_len"], walk_type, result["walk_len"], result["time_taken"]])


if __name__ == '__main__':
    main()
