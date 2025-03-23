import csv
import datetime
import gc
import os

from mpi4py import MPI
from tqdm import tqdm

from fsm_gen.generator import FSMGenerator
from fsm_gen.mutator import Mutator
from walks.hsi import generate_HSI_suite
from walks.random_walk import RandomWalk

TIME = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

def setup_csvs(num_workers, state_size, input_size):
    if not os.path.exists("results"):
        os.mkdir("results")

    for i in range(1, num_workers + 1):
        filename = f"results/S{state_size}_I{input_size}_{i}_{TIME}.csv"
        with open(filename, mode="w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["State Size", "Input Size", "Percent Coverage", "HSI Suite Length", "Walk Type", "Walk Length", "Time Taken"])


def write_to_csv(original_state_size, key, result, rank):
    state_size, input_size, _, percent, walk_type = key.split("_")
    filename = f"results/S{original_state_size}_I{input_size}_{rank}_{TIME}.csv"

    with open(filename, mode="a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([state_size, input_size, percent, result["hsi_len"], walk_type, result["walk_len"], result["time_taken"]])


def run_walk(state_size, input_size, index, percent, walk_type, rank):
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

    write_to_csv(state_size, f"{len(fsm.states)}_{input_size}_{index}_{percent}_{walk_type}", results, rank)



def main(state_size, input_size_key):
    input_size_multipliers = {"2": 2, "n/2": 0.5, "n": 1, "2n": 2}
    percent_coverage = [80, 90, 95, 99.5]
    
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()  # Process ID
    size = comm.Get_size()  # Total number of processes

    if rank == 0:  # Master process distributes work
        tasks = []

        if not(state_size >= 20 and input_size_key == "2"):                
            input_size = 2 if input_size_key == "2" else int(state_size * input_size_multipliers[input_size_key])

            for i in range(20):
                for walk_type in RandomWalk.WalkType:
                    for percent in percent_coverage:
                        tasks.append((state_size, input_size, i, percent, walk_type))

        # Distribute tasks to worker processes
        num_workers = size - 1
        chunk_size = len(tasks) // num_workers
        task_chunks = [tasks[i * chunk_size : (i + 1) * chunk_size] for i in range(num_workers)]
        setup_csvs(num_workers, state_size, input_size)

        for i in range(num_workers):
            comm.send(task_chunks[i], dest=i + 1, tag=11)

    else:  # Worker processes
        tasks = comm.recv(source=0, tag=11)
        
        # Progress bar for each worker
        for task in tqdm(tasks, desc=f"Worker {rank}", position=rank, leave=True):
            run_walk(*task, rank)
            gc.collect()
            

if __name__ == "__main__":
    main(40, "2n")
