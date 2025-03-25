import random
from enum import Enum

from fsm_gen.generator import FSMGenerator

"""
A class to perform different types of (often random) walks on a given FSM.
"""
class RandomWalk:
    MAX_WALK_LENGTH = 100000
    class WalkType(Enum): 
        RANDOM = 0
        RANDOM_WITH_RESET = 1
        LIMITED_SELF_LOOP = 2
        STATISTICAL = 3

        def __str__(self):
            return "".join(self.name.split("_")).lower()

    
    def __init__(self, original_fsm: FSMGenerator, mutated_fsm: FSMGenerator, target_coverage: int, HSI_suite: dict) -> None:
        """
        Create a walker instance for a given FSM and target coverage.

        Args:
            fsm (FSMGenerator): the (mutated) FSM to perform the walks on.
            target_coverage (int): the target coverage of transitions to reach during walks.
            HSI_suite (dict): the HSI suite for the unmutated FSM (ways to distinguish states).
        """
        self.original_fsm = original_fsm
        self.mutated_fsm = mutated_fsm
        self.transitions_length = len(mutated_fsm.transitions)
        self.target_coverage = target_coverage
        self.HSI_suite = HSI_suite


    def walk(self, walk_type: WalkType, step_limit: int = 5) -> list[str]:
        """
        Perform a specific type of walk on the FSM and return its length.

        Args:
            walk_type (WalkType): the type of walk to perform on the FSM.
            step_limit (int): number of steps away from an identified state before resetting.

        Returns:
            int: length of the walk performed in order to meet the target coverage.
        """
        self.mutated_fsm.machine.state = self.mutated_fsm.machine.initial
        if walk_type == self.WalkType.RANDOM:
            result = self._random_walk()
        elif walk_type == self.WalkType.RANDOM_WITH_RESET:
            result = self._random_walk_with_reset(step_limit)
        elif walk_type == self.WalkType.LIMITED_SELF_LOOP:
            result = self._limited_self_loop_walk()
        elif walk_type == self.WalkType.STATISTICAL:
            result = self._statistical_walk()
        return result
    

    def _statistical_walk(self) -> int:
        """
        Navigate a FSM with randomly assigned probability for each input at any 
        state. Some transitions are more likely to be explored than others.

        Returns:
            int: length of the walk performed in order to meet the target coverage.
        """
        transitions_executed = set()
        coverage = 0
        state = self.mutated_fsm.machine.initial
        walk = []

        input_probabilities = []
        probabilities = [random.random() for i in range(0, len(self.mutated_fsm.events))]
        summed_probabilities = sum(probabilities)
        for i in range(0, len(probabilities)):
            input_probabilities.append(probabilities[i] / summed_probabilities)

        while coverage < self.target_coverage:
            if len(walk) > self.MAX_WALK_LENGTH:
                return -1

            triggers = self.mutated_fsm._get_triggers(state)
            trigger = random.choices(triggers, input_probabilities, k=1)[0]

            self.mutated_fsm.machine.trigger(trigger)
            transitions_executed.add(f"{state}->{trigger}")
            walk.append(trigger)

            state = self.mutated_fsm.machine.state
            coverage = len(transitions_executed) / self.transitions_length * 100

        return walk


    def _limited_self_loop_walk(self) -> int:
        """
        Navigate a FSM with uniform probability for each trigger at any state.
        Stores self-loop transitions whenever they are encountered and avoids using them in
        future in order to aid progression.

        Returns:
            int: length of the walk performed in order to meet the target coverage.
        """
        transitions_executed = set()
        coverage = 0
        state = self.mutated_fsm.machine.initial
        walk = []
        self_loop_triggers = []

        while coverage < self.target_coverage:
            if len(walk) > self.MAX_WALK_LENGTH:
                return -1
            
            triggers = self.mutated_fsm._get_triggers(state)

            # Limit triggers to those that are not already explored self-loops
            triggers_excluding_self_loops = [t for t in triggers if [state, t] not in self_loop_triggers]
            if len(triggers_excluding_self_loops) != 0:
                trigger = random.choice(triggers_excluding_self_loops)
            # Fallback incase only option is to self-loop (theoretically impossible in connected machine)
            else:
                trigger = random.choice(triggers)
            previous_state = self.mutated_fsm.machine.state

            self.mutated_fsm.machine.trigger(trigger)
            transitions_executed.add(f"{state}->{trigger}")
            walk.append(trigger)

            state = self.mutated_fsm.machine.state
            current_state = self.mutated_fsm.machine.state

            # Record presence of a self-loop and the trigger it is associated with
            if previous_state == current_state and [state, trigger] not in self_loop_triggers:
                self_loop_triggers.append([state, trigger])

            coverage = len(transitions_executed) / self.transitions_length * 100

        return walk


    def _random_walk_with_reset(self, step_limit: int) -> int:
        """
        Navigate a FSM with uniform probability for each trigger at any state.
        If a state has not been identified through the HSI set for a certain number of steps, the
        machine resets to its initial state.

        Args:
            step_limit (int): number of steps away from an identified state before resetting.

        Returns:
            int: length of the walk performed in order to meet the target coverage.
        """
        walk = []
        walk_since_reset = []
        steps_since_identification = 0
        coverage = 0
        state = self.mutated_fsm.machine.initial
        transitions_executed = set()

        while coverage < self.target_coverage:
            if len(walk) > self.MAX_WALK_LENGTH:
                return -1
            
            triggers = self.mutated_fsm._get_triggers(state)
            trigger = random.choice(triggers)

            self.mutated_fsm.machine.trigger(trigger)
            transitions_executed.add(f"{state}->{trigger}")
            walk.append(trigger)
            walk_since_reset.append(f"{state}->{trigger}")

            for index, input_seq in enumerate(self.HSI_suite.keys()):
                io_sequence = {}
                key = ""
                outputs = ()
                for pair in walk_since_reset[:len(input_seq)]:
                    io = pair.split("->")[1].split(" / ")
                    key += str(io[0])
                    outputs += (io[1],)
                io_sequence[key] = outputs

                if key in self.HSI_suite.keys() and io_sequence[key] == self.HSI_suite[input_seq]:
                    break
                elif index == len(self.HSI_suite):
                    steps_since_identification += 1

            if steps_since_identification >= step_limit:
                self.mutated_fsm.machine.state = self.mutated_fsm.machine.initial
                walk_since_reset = []
                steps_since_identification = 0

            state = self.mutated_fsm.machine.state
            coverage = len(transitions_executed) / self.transitions_length * 100

        return walk
    

    def _random_walk(self) -> int:
        """
        Navigate a FSM with uniform probability for each trigger at any state.
        The pure random approach.

        Returns:
            int: length of the walk performed in order to meet the target coverage.
        """
        transitions_executed = set()
        coverage = 0
        state = self.mutated_fsm.machine.initial
        walk = []

        while coverage < self.target_coverage:
            if len(walk) > self.MAX_WALK_LENGTH:
                return -1
            
            triggers = self.mutated_fsm._get_triggers(state)
            trigger = random.choice(triggers)

            self.mutated_fsm.machine.trigger(trigger)
            transitions_executed.add(f"{state}->{trigger}")
            walk.append(trigger)

            state = self.mutated_fsm.machine.state
            coverage = len(transitions_executed) / self.transitions_length * 100

        return walk


    def detected_fault(self, mutated_walk: list[str]) -> int:
        """
        Check whether walk detected fault in mutated FSM.
        
        Args:
            mutated_walk (list[str]): the walk performed on the mutated FSM.
            
        Returns:
            int: the index of the fault detected in the walk.
        """
        if mutated_walk == -1:
            return -1

        mutated_walk_inputs = "".join([trigger.split(" / ")[0] for trigger in mutated_walk])
        mutated_walk_outputs = tuple([trigger.split(" / ")[1] for trigger in mutated_walk])

        _, outputs = self.original_fsm.apply_input_sequence(self.original_fsm.machine.initial, mutated_walk_inputs)

        for index, output in enumerate(outputs):
            if output != mutated_walk_outputs[index]:
                return index + 1
            
        return -1
