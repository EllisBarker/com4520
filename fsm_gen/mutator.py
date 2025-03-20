import copy
import os
import pickle
import random

from fsm_gen.generator import FSMGenerator
from fsm_gen.machine import Machine

"""
A class to apply different types of mutations to a given FSM.
"""
class Mutator:
    DEBUG = False
    MUTATION_TYPES = ['add_state', 'remove_state', 'change_trigger_output', 'change_trans_dest']

    def __init__(self, fsm: FSMGenerator) -> None:
        """
        Create a mutator instance for a given FSM.

        Args:
            fsm (FSMGenerator): the (unmutated) FSM to apply mutations to.
        """
        self.fsm = fsm
        self.num_mutations = int(0.4 * len(self.fsm.states))
        self.mutations_applied = []


    def create_mutated_fsm(self):
        """
        Apply mutations to a given finite state machine, store the result and render the mutated FSM.

        Returns:
            Machine: The mutated FSM
        """
        self._mutate()
        self.fsm.machine = Machine(states=self.fsm.states, initial=self.fsm.states[0],
                                   graph_engine="pygraphviz", auto_transitions=False,
                                   transitions=self.fsm.transitions)
        
        # if not os.path.exists('pickles/mutated'):
        #     os.makedirs('pickles/mutated')    
        # pickle.dump(self.fsm, open(f'pickles/mutated/mutated.pkl', 'wb'))

        return self.fsm


    def _mutate(self):
        """
        Apply a variety of mutations to a given FSM (corresponding to the number of states).
        """
        for _ in range(self.num_mutations):
            original_fsm = copy.deepcopy(self.fsm)
            mutation = random.choice(self.MUTATION_TYPES)

            match mutation:
                case 'add_state':
                    self._add_state()
                case 'remove_state':
                    self._remove_state()
                case 'change_trigger_output':
                    self._change_trigger_output()
                case 'change_trans_dest':
                    self._change_trans_dest()

            # Ensure connectivity after each mutation (and apply change trigger output as a fallback)
            if not self._check_connectivity():
                self.fsm = original_fsm
                self._change_trigger_output()

        if self.DEBUG:
            print("Mutations applied:")
            for mutation in self.mutations_applied:
                print(f"\t{mutation}")
            self.get_machine_properties()

    
    def _add_state(self):
        """
        Add a new state to a FSM and ensure it is connected to other states in the system.
        """
        # Get random source state and transition
        source_state = random.choice(self.fsm.states)
        source_state_trans = random.choice([t for t in self.fsm.transitions if t["source"] == source_state])

        # Create new state
        last_state_num = self.fsm.states[-1][1:]
        new_state = f'S{int(last_state_num) + 1}'
        self.fsm.states.append(new_state)

        # Add new transition from new state to dest of source_state
        # Modify source_state transition to point to new state
        used_event = random.choice(self.fsm.events)
        self.fsm.transitions.append({
            "source": new_state,
            "trigger": used_event + ' / ' + str(random.randint(0, 1)),
            "dest": source_state_trans["dest"]
        })
        source_state_trans["dest"] = new_state

        # Add transitions from new state to other states for remaining events
        for event in self.fsm.events:
            if event != used_event:
                self.fsm.transitions.append({
                    "source": new_state,
                    "trigger": event + ' / ' + str(random.randint(0, 1)),
                    "dest": random.choice(self.fsm.states)
                })

        self.mutations_applied.append(f"Added state {new_state} using {source_state_trans}")
    

    def _remove_state(self):
        """
        Remove a state from a FSM and reroute/delete its associated transitions.
        """
        # Ensure initial state cannot be removed
        states_to_check = [state for state in self.fsm.states if state not in self.fsm.states[0]]
        state_found = False

        # Store original states and transitions in case the machine needs to be reverted
        original_states = copy.deepcopy(self.fsm.states)
        original_transitions = copy.deepcopy(self.fsm.transitions)
        original_fsm = copy.deepcopy(self.fsm)

        while len(states_to_check) != 0 and not state_found:
            state_to_remove = random.choice(states_to_check)

            # Only remove states if they have equal or more incoming transitions as outgoing transitions
            if self._get_num_transitions_exclude_loops(state_to_remove, True) >= self._get_num_transitions_exclude_loops(state_to_remove, False):
                outgoing_state_trans = [t for t in self.fsm.transitions if t["source"] == state_to_remove]
                incoming_state_trans = [t for t in self.fsm.transitions if t["dest"] == state_to_remove]

                # Remove all outgoing transitions, but store their destination states to ensure they can still be reached
                dest_states = []
                for transition in outgoing_state_trans:
                    self.fsm.transitions = [t for t in self.fsm.transitions if t != transition]
                    if transition["dest"] != state_to_remove:
                        dest_states.append(transition["dest"])

                random.shuffle(dest_states)
                self.fsm.states.remove(state_to_remove)

                # Reroute incoming transitions to previously found destination states
                for transition in incoming_state_trans:
                    if len(dest_states) > 0:
                        dest_state = dest_states[0]
                        transition["dest"] = dest_state
                        dest_states = dest_states[1:]
                    else:
                        dest_state = random.choice([state for state in self.fsm.states if state != transition["source"]])
                        transition["dest"] = dest_state

                # Check that connectivity is maintained when this state is removed
                if self._check_connectivity():
                    state_found = True
                    self.mutations_applied.append(f"Removed state {state_to_remove}")
                else:
                    self.fsm = original_fsm
                    self.fsm.states = original_states[:]
                    self.fsm.transitions = original_transitions[:]
                    self.fsm.machine = Machine(states=self.fsm.states, initial=self.fsm.states[0],
                                               graph_engine="pygraphviz", auto_transitions=False,
                                               transitions=self.fsm.transitions)
                    states_to_check.remove(state_to_remove)
            else:
                states_to_check.remove(state_to_remove)

        # Apply different mutation type if a state cannot be removed
        if not state_found:
            alternative_mutations = [self._change_trans_dest, self._change_trigger_output]
            alternative_mutation_choice = random.choice([0,1])
            alternative_mutations[alternative_mutation_choice]()


    def _change_trigger_output(self):
        """
        Alter the output of a random transition to an opposite value (0 -> 1, 1 -> 0).
        """
        transition = random.choice(self.fsm.transitions)
        while f"Changed trigger output of transition {transition}" in self.mutations_applied:
            transition = random.choice(self.fsm.transitions)
        transition_trigger = transition["trigger"].split(' / ')
        transition["trigger"] = f'{transition_trigger[0]} / {1 - int(transition_trigger[1])}'

        self.mutations_applied.append(f"Changed trigger output of transition {transition}")


    def _get_num_transitions_exclude_loops(self, state: str, incoming: bool) -> int:
        """
        Retrieve the number of transitions coming into or going out of a state (whilst ignoring those 
        that trigger loops within the same state).

        Args:
            state (str): The state to check transitions for.
            incoming (bool): Whether to check for incoming transitions (True) or outgoing transitions (False).

        Returns:
            int: The number of transitions incoming/outgoing for a specific state (excluding self-loops).
        """
        num_trans = 0

        for transition in self.fsm.transitions:
            if incoming:
                if transition["dest"] == state and transition["source"] != state:
                    num_trans +=1
            else:
                if transition["source"] == state and transition["dest"] != state:
                    num_trans += 1

        return num_trans

    
    def _change_trans_dest(self):
        """
        Alter the destination of a random transition within the FSM (whilst ensuring the FSM stays totally connected).
        """
        original_transitions = copy.deepcopy(self.fsm.transitions)
        original_fsm = copy.deepcopy(self.fsm)

        transition = random.choice(self.fsm.transitions)

        # Ensures FSM is connected still (and avoid applying mutation to already mutated transitions)
        while self._get_num_transitions_exclude_loops(transition["dest"], True) < 2 or f"Changed destination of transition {transition}" in self.mutations_applied:
            transition = random.choice(self.fsm.transitions)

        # Make sure random destination state cannot be the same state as original destination
        random_dest = transition["dest"]
        while random_dest == transition["dest"]:
            random_dest = random.choice(self.fsm.states)
        transition["dest"] = random_dest

        # Don't apply mutation if connectivity is lost
        if self._check_connectivity():
            self.mutations_applied.append(f"Changed destination of transition {transition}")
        else:
            self.fsm = original_fsm
            self.fsm.transitions = original_transitions[:]
            self.fsm.machine = Machine(states=self.fsm.states, initial=self.fsm.states[0],
                                       graph_engine="pygraphviz", auto_transitions=False,
                                       transitions=self.fsm.transitions)
            alternative_mutations = [self._change_trigger_output, self._change_trans_dest]
            alternative_mutation_choice = random.choice([0,1])
            alternative_mutations[alternative_mutation_choice]()


    def _check_determinism(self) -> bool:
        """
        For the FSM, determine whether or not it is deterministic (has only 1 of each input symbol per state).

        Returns:
            bool: Whether or not the machine is deterministic.
        """
        for state in self.fsm.states:
            transitions = [t for t in self.fsm.transitions if t["source"] == state]
            triggers = [t["trigger"].split(' / ')[0] for t in transitions]
            if len(triggers) != len(set(triggers)):
                return False
            
        return True


    def _check_connectivity(self) -> bool:
        """
        For the FSM, determine whether or not it is connected (any given state can be reached from any other state).

        Returns:
            bool: Whether or not the machine is connected.
        """
        def dfs(start_state):
            visited = set()
            stack = [start_state]
            while stack:
                state = stack.pop()
                if state not in visited:
                    visited.add(state)
                    for transition in self.fsm.transitions:
                        if transition['source'] == state:
                            stack.append(transition['dest'])
            return visited

        all_states = set(self.fsm.states)
        for state in self.fsm.states:
            if dfs(state) != all_states:
                return False
            
        return True

    def get_machine_properties(self):
        """
        Display the properties of the FSM in terminal (whether or not it is deterministic and connected).
        """
        connected = self._check_connectivity()
        deterministic = self._check_determinism()

        print(f"\nConnected: {connected}, Deterministic: {deterministic}")
