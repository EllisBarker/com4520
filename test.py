from fsm_gen.generator import FSMGenerator
from fsm_gen.mutator import Mutator
from walks.new_hsi import generate_HSI_suite
from walks.random_walk import RandomWalk

fsm = FSMGenerator(10,2)
fsm.draw("tetetet.png")

mutator = Mutator(fsm)
hsi_suite = generate_HSI_suite(fsm)
mutated_fsm = mutator.create_mutated_fsm()

walker = RandomWalk(mutated_fsm, 99.5, hsi_suite)

walk_length, resets = walker._random_walk_with_reset(5)

print(walk_length, resets)