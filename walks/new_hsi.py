import itertools
from collections import defaultdict

from fsm_gen.generator import FSMGenerator


def _find_shortest_path(fsm: FSMGenerator, end: str) -> list:
    """
    Find the shortest path from the initial state to the end state.
    
    Args:
        fsm (FSMGenerator): the FSM to find the shortest path in
        end (str): the end state

    Returns:
        list: the shortest path from the initial state to the end state
    """
    queue = [(fsm.states[0], [])]

    while queue:
        (state, path) = queue.pop(0)
        transitions = fsm._get_transitions(source=state)

        for transition in transitions:
            inp = transition["trigger"].split(" / ")[0]
            next_state = transition["dest"]

            if state == end:
                return path
            if next_state == end:
                return path + [inp]
            else:
                queue.append((next_state, path + [inp]))


def _generate_state_cover(fsm: FSMGenerator) -> dict[str, list[str]]:
    """
    Generate the state cover for the FSM.

    Args:
        fsm (FSMGenerator): the FSM to generate the state cover for
    
    Returns:
        dict: the state cover for the FSM
    """
    state_cover = {}
    for state in fsm.states[1:]:
        state_cover[state] = _find_shortest_path(fsm, state)

    state_cover[fsm.states[0]] = []
    return state_cover


def _generate_harmonised_state_identifiers(fsm: FSMGenerator) -> dict[str, set[str]]:
    """
    Generate a harmonised set of state identifiers for the FSM.

    Args:
        fsm (FSMGenerator): The FSM to generate state identifiers for.
        max_seqs_per_state (int): The maximum number of distinguishing sequences per state.

    Returns:
        dict: A harmonised set of state identifiers for the FSM.
    """
    max_len = 5
    state_identifiers = defaultdict(set)
    state_pairs = [(s1, s2) for i, s1 in enumerate(fsm.states) for s2 in fsm.states[i+1:]]
    test_sequences = [''.join(seq) for length in range(1, max_len + 1) for seq in itertools.product(fsm.events, repeat=length)]
    
    separating_sequences = {}  # Dictionary to store a harmonised separating sequence for each pair

    for s1, s2 in state_pairs:
        for seq in test_sequences:
            _, output1 = fsm.apply_input_sequence(s1, seq)
            _, output2 = fsm.apply_input_sequence(s2, seq)

            if output1 != output2:
                separating_sequences[(s1, s2)] = seq
                break  # Stop after finding one separating sequence

    # Apply harmonisation: Use the same separating sequence across state identifiers
    for (s1, s2), seq in separating_sequences.items():
        state_identifiers[s1].add(seq)
        state_identifiers[s2].add(seq)

    return state_identifiers


def generate_HSI_suite(fsm: FSMGenerator) -> dict[str, set[str]]:
    """
    Generate the HSI test set for the FSM using the HSI method.

    Args:
        fsm (FSMGenerator): The FSM to generate the HSI test set for.

    Returns:
        set: The HSI test set for the FSM.
    """
    state_identifiers = _generate_harmonised_state_identifiers(fsm)
    state_cover = _generate_state_cover(fsm)

    max_len = 5 
    input_sequences = [''.join(seq) for length in range(1, max_len + 1) 
                       for seq in itertools.product(fsm.events, repeat=length)]

    hsi_test_set = defaultdict(set)
    # concantenate each state's state cover seq with each input sequence, then concatenate with appropriate state identifier
    for state, state_cover_seq in state_cover.items():
        for input_seq in input_sequences:
            for state_identifier in state_identifiers[state]:
                hsi_test_set[state].add(''.join(state_cover_seq + [input_seq] + [state_identifier]))

    return hsi_test_set
