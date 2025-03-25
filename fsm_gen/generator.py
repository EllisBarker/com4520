import pickle
import random
from pathlib import Path

from fsm_gen.machine import Machine

"""
A class to generate a FSM satisfying specific realistic properties.
"""
class FSMGenerator:
    def __init__(self, num_states: int, num_inputs: int) -> None:
        """
        Create a finite state machine with a given number of states and inputs.

        Args:
            num_states (int): the number of inputs that can be attempted at any state.
            num_inputs (int): the number of states that are in the FSM.
        """
        self.states = [f"S{i}" for i in range(num_states)]
        self.events = [f"{chr(i + 65)}" for i in range(num_inputs)]

        self._try_generate_connected_machine()

    
    def _try_generate_connected_machine(self) -> None:
        """
        Try to generate a connected machine. If the machine is not connected, try again.
        """
        connected = False

        while not connected:
            self.transitions = self._generate_transitions()        
            connected = self._ensure_connected_machine()

        self._add_leftover_transitions()
        self._make_minimal()
        self._cleanup_transitions()
        self.machine = Machine(states=self.states, initial=self.states[0], 
                               graph_engine='pygraphviz', auto_transitions=False, 
                               transitions=self.transitions)


    def _generate_transitions(self) -> list:
        """
        Generate random transitions between states.

        Returns:
            list: A list of dictionaries representing the transitions.
        """
        transitions = []

        for state in self.states:
            events = random.sample(self.events, len(self.events) - 1)
            for event in events:
                dest = random.choice(self.states)
        
                transitions.append({
                    'trigger': event + ' / ' + str(random.randint(0, 1)),
                    'source': state,
                    'dest': dest
                })

        return transitions


    def _is_reachable_from(self, state: str, target: str) -> bool:
        """
        Check if a target state is reachable from a given state.

        Args:
            state (str): The source state.
            target (str): The target state.

        Returns:
            bool: True if the target state is reachable from the source state, False otherwise.
        """
        reachable_states = set()
        states_to_check = [state]

        while states_to_check:
            current_state = states_to_check.pop()

            if current_state == target:
                return True
            
            for transition in self.transitions:
                if transition['source'] == current_state and transition['dest'] not in reachable_states:
                    reachable_states.add(transition['dest'])
                    states_to_check.append(transition['dest'])

        return False
    

    def _get_triggers(self, state: str) -> list:
        """
        Get triggers for a given state.

        Args:
            state (str): The state to get triggers for.

        Returns:
            list: A list of triggers for the given state.
        """
        triggers = []

        for transition in self.transitions:
            if transition['source'] == state:
                triggers.append(transition['trigger'])

        return triggers
    

    def _add_leftover_transitions(self) -> None:
        """
        Add any transitions that are missing for an event to make the machine complete.
        """
        for state in self.states:
            current_triggers = [trigger[0] for trigger in self._get_triggers(state)]
            available_triggers = [event for event in self.events if event not in current_triggers]

            for trigger in available_triggers:
                dest = random.choice(self.states)

                self.transitions.append({
                    'trigger': trigger + ' / ' + str(random.randint(0, 1)),
                    'source': state,
                    'dest': dest
                })
        

    def _ensure_connected_machine(self) -> bool:
        """
        Ensure that all states are reachable from any other state.

        Returns:
            bool: True if the machine is connected, False otherwise.
        """
        for state in self.states:
            for target in self.states:
                if state == target:
                    continue

                if not self._is_reachable_from(state, target):
                    current_triggers = [trigger[0] for trigger in self._get_triggers(state)]
                    available_triggers = [event for event in self.events if event not in current_triggers]

                    if not available_triggers:
                        return False
                    
                    self.transitions.append({
                        'trigger': available_triggers[0] + ' / ' + str(random.randint(0, 1)),
                        'source': state,
                        'dest': target
                    })

        return True
    

    def _find_1_equivalent(self) -> dict[str, set]:
        """
        Find the states that are equivalent with respect to their input/output.

        Returns:
            dict: A dictionary of equivalence sets.
        """
        equivalence_sets = dict()

        for state in self.states:
            triggers = self._get_triggers(state)

            io_string = ""
            for trigger in triggers:
                io_string += f"{trigger},"
            
            io_list = io_string.split(",")
            io_list.sort()
            io_string = "".join(io_list)

            if io_string not in equivalence_sets.keys():
                equivalence_sets[io_string] = set()
                
            equivalence_sets[io_string].add(state)

        return equivalence_sets
    

    def _get_dest_from_trigger(self, source: str, trigger: str) -> str:
        """
        Get the destination state from a given source state and trigger.
        
        Args:
            source (str): The source state of the transition.
            trigger (str): The trigger of the transition.
            
        Returns:
            str: The destination state of the transition.
        """
        
        for transition in self.transitions:
            if transition['source'] == source and transition['trigger'] == trigger:
                return transition['dest']
            
        #return None
        raise LookupError(f"No valid transition found for state '{source}' with trigger '{trigger}'")
    

    def _get_transitions(self, source: str=None, dest: str=None) -> list:
        """
        Get transitions from the machine.
        
        Args:
            source (str): The source state of the transition.
            dest (str): The destination state of the transition.
            
        Returns:
            list: A list of transitions.
        """
        transitions = []

        for transition in self.transitions:
            if source and dest:
                if transition['source'] == source and transition['dest'] == dest:
                    transitions.append(transition)
            elif source:
                if transition['source'] == source:
                    transitions.append(transition)
            elif dest:
                if transition['dest'] == dest:
                    transitions.append(transition)

        return transitions


    def _find_equivalent_states(self) -> list[set]:
        """
        Find 2+-equivalent states with respect to their transitions.

        Returns:
            list: A list of sets of equivalent states.
        """
        previous_equivalence_dict = self._find_1_equivalent()

        # Check for if every transition is 1-equivalent for every state in the FSM
        if len(previous_equivalence_dict) != 1:
            while True:
                current_equivalence_dict = dict()

                for key, eq_set in previous_equivalence_dict.items():
                    for state in eq_set:
                        triggers = self._get_triggers(state)
                        subset_pointer = key

                        for trigger in triggers:
                            trigger_input = trigger.split(" / ")[0]
                            trigger_output = trigger.split(" / ")[1]
                            subset_pointer += trigger_input
                            subset_pointer += trigger_output

                            dest = self._get_dest_from_trigger(state, trigger)

                            for key, eq_set in previous_equivalence_dict.items():
                                if dest in eq_set:
                                    subset_pointer += f"{key},"
                                    break

                        subset_pointer_list = subset_pointer.split(",")
                        subset_pointer_list.sort()
                        subset_pointer = "".join(subset_pointer_list)

                        if subset_pointer not in current_equivalence_dict.keys():
                            current_equivalence_dict[subset_pointer] = set()
                    
                        current_equivalence_dict[subset_pointer].add(state)
                                                    
                if sorted(current_equivalence_dict.values()) == sorted(previous_equivalence_dict.values()):
                    break

                previous_equivalence_dict = current_equivalence_dict

        equivalent_states = []
        for eq_set in previous_equivalence_dict.values():
            if len(eq_set) > 1:
                equivalent_states.append(eq_set)

        return equivalent_states


    def _make_minimal(self) -> None:
        """
        Make the machine minimal by removing redundant states.
        """
        equivalence_states = self._find_equivalent_states()
        equivalence_states = [list(eq_set) for eq_set in equivalence_states]

        for eq_set in equivalence_states:
            for state_index in range(1, len(eq_set)):
                state = eq_set[state_index]

                source_transitions = self._get_transitions(source=state)
                dest_transitions = self._get_transitions(dest=state)

                for transition in dest_transitions:
                    transition["dest"] = eq_set[0]

                for transition in source_transitions:
                    transition["source"] = eq_set[0]

                self.states.remove(state)


    def _cleanup_transitions(self) -> None:
        """
        Remove duplicate transitions from the machine.
        """
        transitions = []
        for transition in self.transitions:
            if transition not in transitions:
                transitions.append(transition)

        self.transitions = transitions


    def save(self, filename: str) -> None:
        """
        Save the machine to a pickle file.

        Args:
            filename (str): The name of the pickle file.
        """
        pickle.dump(self, open(filename, 'wb'))


    def draw(self, filename: str, title: str = None) -> None:
        """
        Draw the machine and save to a file in the 'fsm_imgs/' directory.
        Specify extension in filename.

        Args:
            filename (str): The name of the file to save to.
            title (str): The title of the graph.
        """
        Path("fsm_imgs").mkdir(parents=True, exist_ok=True)
        self.machine.draw_graph(title).draw(f"fsm_imgs/{filename}", prog='dot')


    def apply_input_sequence(self, state: str, sequence: str) -> tuple[str]:
        """
        Apply an input sequence to the machine.
        
        Args:
            state (str): The state to start from.
            sequence (str): The input sequence to apply.

        Returns:
            tuple: The final state and the output sequence.
        """
        output_seq = []

        for event in sequence:
            if event not in self.events:
                raise ValueError(f"Invalid event: '{event}' in sequence.")
            for transition in self.transitions:
                if transition['source'] == state and transition['trigger'].startswith(event):
                    output_seq.append(transition['trigger'].split(" / ")[1])
                    state = transition['dest']
                    break

        return state, tuple(output_seq)
