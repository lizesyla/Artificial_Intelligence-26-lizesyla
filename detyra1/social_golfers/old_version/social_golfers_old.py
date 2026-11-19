import itertools
import time
from typing import List, Set, Tuple, Optional, Dict
from dataclasses import dataclass


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class GolfersConfig:
    """Configuration for the Social Golfers Problem.
    
    Attributes:
        num_golfers: Total number of golfers (N)
        groups_per_week: Number of groups per week (G)
        golfers_per_group: Golfers per group (S)
        max_weeks_to_attempt: Target number of weeks to schedule
        search_timeout_seconds: Maximum search time before giving up
        verbose: If True, print detailed progress information
    """
    num_golfers: int = 32
    groups_per_week: int = 8
    golfers_per_group: int = 4
    max_weeks_to_attempt: int = 5
    search_timeout_seconds: float = 60.0
    verbose: bool = True
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        assert self.num_golfers == self.groups_per_week * self.golfers_per_group, \
            f"num_golfers ({self.num_golfers}) must equal groups_per_week x golfers_per_group"
        assert self.num_golfers > 0
        assert self.groups_per_week > 0
        assert self.golfers_per_group > 0


# =============================================================================
# CORE DATA STRUCTURES
# =============================================================================

@dataclass
class ScheduleState:
    """Represents a partial or complete schedule."""
    weeks: List[List[Set[int]]]  # List of weeks, each week is list of groups
    
    def __post_init__(self):
        if self.weeks is None:
            self.weeks = []


class PairTracker:
    """
    Tracks which pairs of golfers have played together.
    Efficiently checks and updates pair co-occurrence constraints.
    """
    
    def __init__(self):
        # pair_history[(i, j)] = set of week indices where i and j played together
        # Only store with i < j for consistency
        self.pair_history: Dict[Tuple[int, int], Set[int]] = {}
    
    def get_pair_key(self, g1: int, g2: int) -> Tuple[int, int]:
        """Get canonical pair key (smaller ID first)."""
        return (min(g1, g2), max(g1, g2))
    
    def has_played_together(self, g1: int, g2: int) -> bool:
        """Check if two golfers have already played together."""
        key = self.get_pair_key(g1, g2)
        return key in self.pair_history and len(self.pair_history[key]) > 0
    
    def played_in_week(self, g1: int, g2: int, week_idx: int) -> bool:
        """Check if two golfers played together in a specific week."""
        key = self.get_pair_key(g1, g2)
        if key not in self.pair_history:
            return False
        return week_idx in self.pair_history[key]
    
    def record_pair(self, g1: int, g2: int, week_idx: int):
        """Record that two golfers played together in a given week."""
        key = self.get_pair_key(g1, g2)
        if key not in self.pair_history:
            self.pair_history[key] = set()
        self.pair_history[key].add(week_idx)
    
    def record_week_pairs(self, groups: List[Set[int]], week_idx: int):
        """Record all pairs in a week's groups."""
        for group in groups:
            golfers_list = list(group)
            for i in range(len(golfers_list)):
                for j in range(i + 1, len(golfers_list)):
                    self.record_pair(golfers_list[i], golfers_list[j], week_idx)
    
    def can_add_group(self, group: Set[int], week_idx: int) -> bool:
        """
        Check if adding this group would violate pair constraints.
        Returns True if all pairs in this group haven't played together before.
        """
        golfers_list = list(group)
        for i in range(len(golfers_list)):
            for j in range(i + 1, len(golfers_list)):
                if self.played_in_week(golfers_list[i], golfers_list[j], week_idx):
                    return False
        return True
    
    def get_total_pairs(self) -> int:
        """Get total number of unique pairs that have been recorded."""
        return len(self.pair_history)
    
    def get_pairs_with_history(self) -> int:
        """Get number of pairs that have played together at least once."""
        return sum(1 for pairs in self.pair_history.values() if len(pairs) > 0)
    
    def clone(self) -> 'PairTracker':
        """Create a deep copy of this tracker."""
        new_tracker = PairTracker()
        new_tracker.pair_history = {
            k: v.copy() for k, v in self.pair_history.items()
        }
        return new_tracker


# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================

def validate_schedule(schedule: List[List[Set[int]]], config: GolfersConfig) -> Tuple[bool, List[str]]:
    """
    Validate a complete schedule.
    
    Returns:
        (is_valid, list of error messages)
    """
    errors = []
    pair_tracker = PairTracker()
    
    # Check number of weeks
    if len(schedule) == 0:
        errors.append("Schedule has no weeks")
        return False, errors
    
    for week_idx, week_groups in enumerate(schedule):
        # Check: all golfers appear exactly once per week
        all_golfers_in_week = set()
        for group in week_groups:
            all_golfers_in_week.update(group)
        
        expected_golfers = set(range(1, config.num_golfers + 1))
        if all_golfers_in_week != expected_golfers:
            missing = expected_golfers - all_golfers_in_week
            extra = all_golfers_in_week - expected_golfers
            error_msg = f"Week {week_idx + 1}: "
            if missing:
                error_msg += f"Missing golfers {sorted(missing)}. "
            if extra:
                error_msg += f"Extra golfers {sorted(extra)}. "
            errors.append(error_msg)
        
        # Check: each group has exactly S golfers
        for group_idx, group in enumerate(week_groups):
            if len(group) != config.golfers_per_group:
                errors.append(
                    f"Week {week_idx + 1}, Group {group_idx + 1}: "
                    f"Has {len(group)} golfers, expected {config.golfers_per_group}"
                )
        
        # Check: groups are disjoint within a week
        for i, g1 in enumerate(week_groups):
            for j, g2 in enumerate(week_groups):
                if i < j:
                    intersection = g1 & g2
                    if intersection:
                        errors.append(
                            f"Week {week_idx + 1}: Groups {i+1} and {j+1} "
                            f"share golfers {sorted(intersection)}"
                        )
        
        # Record pairs for this week (if no coverage errors)
        if all_golfers_in_week == expected_golfers:
            pair_tracker.record_week_pairs(week_groups, week_idx)
    
    # Check pair uniqueness across all weeks
    for (g1, g2), weeks in pair_tracker.pair_history.items():
        if len(weeks) > 1:
            errors.append(
                f"Golfers {g1} and {g2} played together in weeks {sorted(weeks)}, "
                f"which is more than once"
            )
    
    is_valid = len(errors) == 0
    return is_valid, errors


def has_repeated_pairs(schedule: List[List[Set[int]]], config: GolfersConfig) -> List[Tuple[int, int, List[int]]]:
    """
    Check if any pair of golfers has been repeated.
    
    Returns:
        List of (golfer1, golfer2, list of weeks) for repeated pairs.
        Empty list if no repeats.
    """
    pair_weeks: Dict[Tuple[int, int], List[int]] = {}
    
    for week_idx, week_groups in enumerate(schedule):
        for group in week_groups:
            golfers_list = sorted(group)
            for i in range(len(golfers_list)):
                for j in range(i + 1, len(golfers_list)):
                    key = (golfers_list[i], golfers_list[j])
                    if key not in pair_weeks:
                        pair_weeks[key] = []
                    pair_weeks[key].append(week_idx + 1)  # 1-indexed weeks
    
    repeats = [
        (g1, g2, weeks) 
        for (g1, g2), weeks in pair_weeks.items() 
        if len(weeks) > 1
    ]
    
    return repeats


# =============================================================================
# DFS WITH BACKTRACKING IMPLEMENTATION
# =============================================================================

class SocialGolfersDFS:
    """
    DFS with Backtracking solver for the Social Golfers Problem.
    
    This solver builds a schedule week by week, and within each week,
    builds groups one at a time. It uses backtracking when it hits
    a dead end.
    """
    
    def __init__(self, config: GolfersConfig):
        self.config = config
        self.all_golfers = set(range(1, config.num_golfers + 1))
        self.start_time = 0
        self.nodes_explored = 0
        self.found_solutions = []
        
    def generate_possible_groups(self, remaining_golfers: Set[int], 
                                  required_size: int) -> List[Set[int]]:
        """
        Generate all possible groups of the required size from remaining golfers.
        
        For efficiency, we generate combinations but may limit based on context.
        """
        golfers_list = sorted(remaining_golfers)
        if len(golfers_list) < required_size:
            return []
        
        # Generate all combinations of required size
        combinations = itertools.combinations(golfers_list, required_size)
        return [set(combo) for combo in combinations]
    
    def get_remaining_golfers_for_week(self, week_idx: int, 
                                         current_schedule: List[List[Set[int]]]) -> Set[int]:
        """Get golfers not yet assigned in the current week being built."""
        if not current_schedule:
            return self.all_golfers.copy()
        
        last_week = current_schedule[-1]
        assigned = set()
        for group in last_week:
            assigned.update(group)
        return self.all_golfers - assigned
    
    def is_week_complete(self, week_groups: List[Set[int]], config: GolfersConfig) -> bool:
        """Check if a week has all golfers assigned to groups."""
        all_assigned = set()
        for group in week_groups:
            all_assigned.update(group)
        return all_assigned == self.all_golfers
    
    def is_schedule_complete(self, schedule: List[List[Set[int]]]) -> bool:
        """Check if schedule has reached target number of weeks."""
        return len(schedule) >= self.config.max_weeks_to_attempt
    
    def search(self, schedule: List[List[Set[int]]], 
               pair_tracker: PairTracker,
               week_idx: int,
               group_idx: int,
               current_week_groups: List[Set[int]],
               remaining_in_week: Set[int],
               timeout: bool = False) -> Optional[List[List[Set[int]]]]:
        """
        DFS with backtracking to find a valid schedule.
        
        Args:
            schedule: Complete weeks so far (previous weeks)
            pair_tracker: Tracks pair co-occurrences
            week_idx: Index of week currently being built
            group_idx: Index of group currently being filled in current week
            current_week_groups: Groups built so far in current week
            remaining_in_week: Golfers not yet assigned this week
            timeout: Whether search timed out
            
        Returns:
            Complete schedule if found, None otherwise
        """
        self.nodes_explored += 1
        
        # Check timeout
        if timeout or (self.config.search_timeout_seconds > 0 and 
                       time.time() - self.start_time > self.config.search_timeout_seconds):
            return None
        
        # Check if current week is complete
        if self.is_week_complete(current_week_groups, self.config):
            # Week complete - record pairs and start next week
            pair_tracker.record_week_pairs(current_week_groups, week_idx)
            
            new_schedule = schedule + [current_week_groups]
            
            if self.is_schedule_complete(new_schedule):
                return new_schedule
            
            # Start next week - use SAME pair tracker (don't reset!)
            # The pair tracker maintains state across all weeks
            return self.search(
                schedule=new_schedule,
                pair_tracker=pair_tracker,  # IMPORTANT: Keep the same tracker
                week_idx=week_idx + 1,
                group_idx=0,
                current_week_groups=[],
                remaining_in_week=self.all_golfers.copy(),
                timeout=False
            )
        
        # Current week not complete - try to fill next group
        if group_idx >= self.config.groups_per_week:
            # Shouldn't happen if week not complete, but safety check
            return None
        
        # Check if we have enough golfers left for remaining groups
        groups_remaining = self.config.groups_per_week - group_idx
        golfers_needed = groups_remaining * self.config.golfers_per_group
        if len(remaining_in_week) < golfers_needed:
            return None  # Dead end - not enough golfers
        
        # Try each possible group from remaining golfers
        # For efficiency, we'll try combinations but limit to reasonable number
        possible_groups = self._get_ordered_possible_groups(
            remaining_in_week, 
            pair_tracker,
            week_idx,
            current_week_groups
        )
        
        # Sort groups to try more promising ones first (heuristic ordering)
        # This is still DFS - the ordering just affects which paths are tried first
        possible_groups.sort(key=lambda g: self._group_priority(g, pair_tracker))
        
        for group in possible_groups:
            # Check if this group violates any constraints
            # Note: Check against ALL previous weeks, not just current week
            if not self._can_add_group_any_week(group, pair_tracker):
                continue
            
            # Add group and recurse
            new_week_groups = current_week_groups + [group]
            new_remaining = remaining_in_week - group
            
            # Clone pair tracker for backtracking
            new_pair_tracker = pair_tracker.clone()
            
            result = self.search(
                schedule=schedule,
                pair_tracker=new_pair_tracker,
                week_idx=week_idx,
                group_idx=group_idx + 1,
                current_week_groups=new_week_groups,
                remaining_in_week=new_remaining,
                timeout=False
            )
            
            if result is not None:
                return result
        
        # No valid group found - backtrack
        return None
    
    def _get_ordered_possible_groups(self, remaining: Set[int], 
                                      pair_tracker: PairTracker,
                                      week_idx: int,
                                      current_week_groups: List[Set[int]]) -> List[Set[int]]:
        """
        Get possible groups ordered by heuristic priority.
        Limits to reasonable number for performance.
        """
        golfers_list = sorted(remaining)
        required_size = self.config.golfers_per_group
        
        if len(golfers_list) < required_size:
            return []
        
        # Generate all combinations
        all_combos = list(itertools.combinations(golfers_list, required_size))
        
        # Limit combinations for performance (for large problems)
        # For 32 golfers with 28 remaining, this could be C(28,4) = 20,475
        # We limit to first N for reasonable performance
        max_combinations = min(len(all_combos), 5000)
        selected_combos = all_combos[:max_combinations]
        
        return [set(combo) for combo in selected_combos]
    
    def _group_priority(self, group: Set[int], pair_tracker: PairTracker) -> int:
        """
        Heuristic priority for group ordering.
        Lower score = try first.
        Prefer groups with golfers who haven't played together.
        """
        golfers_list = list(group)
        priority = 0
        for i in range(len(golfers_list)):
            for j in range(i + 1, len(golfers_list)):
                # Count how many times this pair has played together
                key = pair_tracker.get_pair_key(golfers_list[i], golfers_list[j])
                if key in pair_tracker.pair_history:
                    priority += len(pair_tracker.pair_history[key]) * 100
        return priority
    
    def _can_add_group_any_week(self, group: Set[int], pair_tracker: PairTracker) -> bool:
        """Check if a group can be added without violating constraints.
        
        This checks if any pair in the group has EVER played together before,
        across ANY week. This is the key constraint for the Social Golfers Problem.
        """
        golfers_list = list(group)
        for i in range(len(golfers_list)):
            for j in range(i + 1, len(golfers_list)):
                # Check if these two golfers have EVER played together
                if pair_tracker.has_played_together(golfers_list[i], golfers_list[j]):
                    return False
        return True
    
    def solve(self) -> Tuple[Optional[List[List[Set[int]]]], Dict]:
        """
        Solve the Social Golfers Problem.
        
        Returns:
            (schedule, stats) where schedule is the found schedule or None,
            and stats contains search statistics.
        """
        self.start_time = time.time()
        self.nodes_explored = 0
        
        schedule: List[List[Set[int]]] = []
        pair_tracker = PairTracker()
        
        # Start search from week 0, group 0
        result = self.search(
            schedule=schedule,
            pair_tracker=pair_tracker,
            week_idx=0,
            group_idx=0,
            current_week_groups=[],
            remaining_in_week=self.all_golfers.copy(),
            timeout=False
        )
        
        elapsed = time.time() - self.start_time
        
        stats = {
            'nodes_explored': self.nodes_explored,
            'elapsed_time': elapsed,
            'weeks_attempted': self.config.max_weeks_to_attempt,
            'success': result is not None,
            'timeout': elapsed >= self.config.search_timeout_seconds
        }
        
        return result, stats


# =============================================================================
# HELPER FUNCTIONS FOR DISPLAY
# =============================================================================

def print_schedule(schedule: List[List[Set[int]]], config: GolfersConfig, 
                   title: str = "SCHEDULE"):
    """Print the schedule in a readable format."""
    print(f"\n{'='*70}")
    print(f"{title}")
    print(f"{'='*70}")
    print(f"Configuration: {config.num_golfers} golfers, "
          f"{config.groups_per_week} groups/week, "
          f"{config.golfers_per_group} golfers/group")
    print(f"Total weeks scheduled: {len(schedule)}")
    print(f"{'='*70}\n")
    
    for week_idx, week_groups in enumerate(schedule):
        print(f"WEEK {week_idx + 1}:")
        for group_idx, group in enumerate(week_groups):
            golfers_sorted = sorted(group)
            print(f"  Group {group_idx + 1}: {golfers_sorted}")
        print()
    
    print(f"{'='*70}\n")


def print_validation_results(is_valid: bool, errors: List[str], 
                              repeats: List[Tuple[int, int, List[int]]]):
    """Print validation results."""
    print("\n" + "="*70)
    print("VALIDATION RESULTS")
    print("="*70)
    
    if is_valid:
        print("[OK] Schedule is VALID - all constraints satisfied!")
    else:
        print("[FAIL] Schedule is INVALID - constraint violations found:")
        for error in errors:
            print(f"  - {error}")
    
    if repeats:
        print("\nRepeated pairs found:")
        for g1, g2, weeks in repeats:
            print(f"  Golfers {g1} and {g2} played together in weeks {weeks}")
    else:
        print("[OK] No repeated pairs found!")
    
    print("="*70 + "\n")


def print_search_stats(stats: Dict):
    """Print search statistics."""
    print("\n" + "="*70)
    print("SEARCH STATISTICS")
    print("="*70)
    print(f"Nodes explored: {stats['nodes_explored']:,}")
    print(f"Elapsed time: {stats['elapsed_time']:.3f} seconds")
    print(f"Weeks attempted: {stats['weeks_attempted']}")
    print(f"Search successful: {stats['success']}")
    if stats['timeout']:
        print("⚠ Search timed out - may not be optimal")
    print("="*70 + "\n")


# =============================================================================
# TEST FUNCTIONS
# =============================================================================

def create_test_schedule_small() -> List[List[Set[int]]]:
    """Create a small valid test schedule (4 golfers, 2 groups of 2, 2 weeks)."""
    # Week 1: [[1,2], [3,4]]
    # Week 2: [[1,3], [2,4]] or [[1,4], [2,3]]
    week1 = [{1, 2}, {3, 4}]
    week2 = [{1, 3}, {2, 4}]
    return [week1, week2]


def create_test_schedule_with_repeats() -> List[List[Set[int]]]:
    """Create an invalid test schedule with repeated pairs."""
    # Week 1: [[1,2], [3,4]]
    # Week 2: [[1,2], [3,4]] - same groups, repeat!
    week1 = [{1, 2}, {3, 4}]
    week2 = [{1, 2}, {3, 4}]
    return [week1, week2]


def create_small_config() -> GolfersConfig:
    """Create a small configuration for testing."""
    return GolfersConfig(
        num_golfers=8,
        groups_per_week=4,
        golfers_per_group=2,
        max_weeks_to_attempt=3,
        search_timeout_seconds=30.0,
        verbose=True
    )


def run_small_test():
    """Run tests with a small configuration."""
    print("\n" + "="*70)
    print("SMALL SCALE TEST (8 golfers, 4 groups of 2)")
    print("="*70 + "\n")
    
    config = create_small_config()
    solver = SocialGolfersDFS(config)
    
    print(f"Attempting to schedule {config.max_weeks_to_attempt} weeks...")
    print(f"Search space per week: C({config.num_golfers}, {config.golfers_per_group}) = "
          f"C({config.num_golfers}, {config.golfers_per_group}) = "
          f"{itertools.combinations(range(config.num_golfers), config.golfers_per_group)} combinations per group\n")
    
    result, stats = solver.solve()
    
    print_search_stats(stats)
    
    if result:
        print_schedule(result, config, "FOUND SCHEDULE (Small Test)")
        is_valid, errors = validate_schedule(result, config)
        repeats = has_repeated_pairs(result, config)
        print_validation_results(is_valid, errors, repeats)
    else:
        print("No schedule found for this configuration.\n")
        if stats['timeout']:
            print("Reason: Search timed out")
        else:
            print("Reason: No valid schedule exists for the given constraints")
    
    return result is not None


def run_validation_tests():
    """Run validation tests with pre-created schedules."""
    print("\n" + "="*70)
    print("VALIDATION TESTS")
    print("="*70 + "\n")
    
    # Test 1: Valid schedule
    print("Test 1: Valid Schedule (4 golfers, 2 weeks)")
    print("-" * 50)
    valid_schedule = create_test_schedule_small()
    config_valid = GolfersConfig(
        num_golfers=4,
        groups_per_week=2,
        golfers_per_group=2,
        max_weeks_to_attempt=2,
        verbose=False
    )
    
    print("Schedule:")
    print_schedule(valid_schedule, config_valid, "TEST SCHEDULE")
    
    is_valid, errors = validate_schedule(valid_schedule, config_valid)
    repeats = has_repeated_pairs(valid_schedule, config_valid)
    print_validation_results(is_valid, errors, repeats)
    
    # Test 2: Invalid schedule with repeated pairs
    print("\nTest 2: Invalid Schedule with Repeated Pairs")
    print("-" * 50)
    invalid_schedule = create_test_schedule_with_repeats()
    config_invalid = GolfersConfig(
        num_golfers=4,
        groups_per_week=2,
        golfers_per_group=2,
        max_weeks_to_attempt=2,
        verbose=False
    )
    
    print("Schedule (INTENTIONALLY INVALID):")
    print_schedule(invalid_schedule, config_invalid, "TEST SCHEDULE")
    
    is_valid, errors = validate_schedule(invalid_schedule, config_invalid)
    repeats = has_repeated_pairs(invalid_schedule, config_invalid)
    print_validation_results(is_valid, errors, repeats)
    
    # Test 3: Manually create a schedule that violates coverage
    print("\nTest 3: Invalid Schedule with Coverage Error")
    print("-" * 50)
    coverage_error_schedule = [
        [{1, 2}, {3, 4}],  # Week 1: OK
        [{1, 2}, {3}]       # Week 2: Missing golfer 4
    ]
    config_coverage = GolfersConfig(
        num_golfers=4,
        groups_per_week=2,
        golfers_per_group=2,
        max_weeks_to_attempt=2,
        verbose=False
    )
    
    print("Schedule (INTENTIONALLY INVALID - missing golfer):")
    print_schedule(coverage_error_schedule, config_coverage, "TEST SCHEDULE")
    
    is_valid, errors = validate_schedule(coverage_error_schedule, config_coverage)
    repeats = has_repeated_pairs(coverage_error_schedule, config_coverage)
    print_validation_results(is_valid, errors, repeats)
    
    print("\n" + "="*70)
    print("VALIDATION TESTS COMPLETE")
    print("="*70 + "\n")


def run_full_problem(max_weeks: int = 5, timeout: float = 120.0):
    """
    Run the solver on the full 32-golfer problem.
    
    Args:
        max_weeks: Number of weeks to attempt to schedule
        timeout: Maximum search time in seconds
    """
    print("\n" + "="*70)
    print("FULL PROBLEM: 32 GOLFERS, 8 GROUPS OF 4")
    print("="*70 + "\n")
    
    config = GolfersConfig(
        num_golfers=32,
        groups_per_week=8,
        golfers_per_group=4,
        max_weeks_to_attempt=max_weeks,
        search_timeout_seconds=timeout,
        verbose=True
    )
    
    # Calculate search space estimate
    from math import comb
    pairs_per_week = config.groups_per_week * comb(config.golfers_per_group, 2)
    total_pairs = comb(config.num_golfers, 2)
    max_theoretical_weeks = total_pairs // pairs_per_week
    
    print(f"Problem Parameters:")
    print(f"  - Total golfers: {config.num_golfers}")
    print(f"  - Groups per week: {config.groups_per_week}")
    print(f"  - Golfers per group: {config.golfers_per_group}")
    print(f"")
    print(f"Pair Analysis:")
    print(f"  - Pairs per week (new pairs created): {pairs_per_week}")
    print(f"  - Total unique pairs possible: {total_pairs}")
    print(f"  - Theoretical max weeks (upper bound): {max_theoretical_weeks}")
    print(f"")
    print(f"Note: The actual maximum number of weeks is NOT known to be {max_theoretical_weeks}.")
    print(f"This is an upper bound based on pair counting only.")
    print(f"Additional constraints (each golfer once per week) may reduce this further.")
    print(f"")
    print(f"Searching for a schedule with {max_weeks} weeks...")
    print(f"Search timeout: {timeout} seconds\n")
    
    solver = SocialGolfersDFS(config)
    result, stats = solver.solve()
    
    print_search_stats(stats)
    
    if result:
        print_schedule(result, config, "FOUND SCHEDULE")
        
        # Validate
        is_valid, errors = validate_schedule(result, config)
        repeats = has_repeated_pairs(result, config)
        print_validation_results(is_valid, errors, repeats)
        
        # Show pair statistics
        pair_tracker = PairTracker()
        for week_idx, week_groups in enumerate(result):
            pair_tracker.record_week_pairs(week_groups, week_idx)
        
        print("Pair Statistics:")
        print(f"  - Total unique pairs that played together: {pair_tracker.get_pairs_with_history()}")
        print(f"  - Total possible pairs: {total_pairs}")
        print(f"  - Percentage of pairs used: {100 * pair_tracker.get_pairs_with_history() / total_pairs:.2f}%")
        print(f"  - Pairs that never played together: {total_pairs - pair_tracker.get_pairs_with_history()}")
        print()
        
        print("IMPORTANT NOTE:")
        print(f"  This schedule has {len(result)} weeks.")
        print(f"  Finding {len(result)} weeks does NOT prove this is optimal.")
        print(f"  It only shows that {len(result)} weeks is achievable.")
        print(f"  The actual maximum may be higher (if search didn't find it)")
        print(f"  or this may already be optimal.")
        print()
        
    else:
        print("No schedule found.\n")
        if stats['timeout']:
            print("Reason: Search timed out after {:.1f} seconds".format(timeout))
            print("The problem may have a solution, but DFS couldn't find it in time.")
            print("Try:")
            print("  - Reducing the number of weeks to attempt")
            print("  - Increasing the timeout")
            print("  - Using a more sophisticated search algorithm")
        else:
            print("Reason: No valid schedule found within search space")
            print("This could mean:")
            print("  - The requested number of weeks is not achievable")
            print("  - The search space was too limited (try increasing combination limit)")
        print()
    
    return result is not None


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main entry point with demonstration and tests.
    
    Run this module directly to execute all tests and demonstrations.
    The theoretical explanation is in report.md.
    """
    
    print("="*70)
    print("SOCIAL GOLFERS PROBLEM - DFS WITH BACKTRACKING")
    print("University AI Project: Uninformed Search Techniques")
    print("="*70)
    print()
    print("Theoretical background: see report.md")
    print()
    
    # Run validation tests with pre-created schedules
    print("\n" + "="*70)
    print("RUNNING VALIDATION TESTS")
    print("="*70 + "\n")
    run_validation_tests()
    
    # Run small scale test to verify algorithm works
    small_success = run_small_test()
    
    if small_success:
        print("[OK] Small scale test PASSED - algorithm is working correctly\n")
    else:
        print("[FAIL] Small scale test FAILED - algorithm may have issues\n")
    
    # Run full problem with configurable weeks
    # You can change these parameters as needed
    full_success = run_full_problem(max_weeks=5, timeout=120.0)
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Small scale test: {'PASSED' if small_success else 'FAILED'}")
    print(f"Full problem test: {'PASSED' if full_success else 'FAILED or TIMEOUT'}")
    print()
    print("Key Points:")
    print("1. This implementation uses DFS with Backtracking (uninformed search)")
    print("2. Finding a schedule for N weeks does NOT prove N is optimal")
    print("3. The search space grows exponentially - full solution may be infeasible")
    print("4. For 32 golfers, theoretical upper bound is ~10 weeks")
    print("="*70)
    
    return 0


if __name__ == "__main__":
    exit(main())
