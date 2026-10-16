# src/open_llm_vtuber/studio/speedrun_engine.py
"""
Autonomous Procedural Mini-Game Generation & Speedrun Racing Engine.

Generates seed-based procedural maze & platformer courses on demand during stream lulls.
Solves courses using A* pathfinding with stochastic human-like reaction jitter,
opens viewer prediction betting windows, and drives live speedrun commentary.
"""

import heapq
import random
import time
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from loguru import logger


@dataclass
class SpeedrunCourse:
    seed: int
    width: int
    height: int
    start: Tuple[int, int]
    goal: Tuple[int, int]
    walls: List[Tuple[int, int]]
    optimal_steps: int
    target_time_seconds: float
    betting_open: bool = True
    pool_win: int = 0
    pool_fail: int = 0


@dataclass
class SpeedrunRunResult:
    course_seed: int
    completed: bool
    actual_time_seconds: float
    target_time_seconds: float
    steps_taken: int
    commentary_prompt: str


class ProceduralSpeedrunEngine:
    """
    Sub-millisecond Procedural Level Generator and Speedrun Simulation Engine.
    """

    def __init__(self, default_dims: Tuple[int, int] = (15, 15)):
        self.width, self.height = default_dims
        self.active_course: Optional[SpeedrunCourse] = None

    def generate_course(self, seed: Optional[int] = None) -> SpeedrunCourse:
        """Generates a procedural maze/obstacle course using random seed."""
        s = seed or random.randint(1000, 9999)
        rng = random.Random(s)

        # Generate boundary walls + interior sparse obstacles
        walls = set()
        for x in range(self.width):
            walls.add((x, 0))
            walls.add((x, self.height - 1))
        for y in range(self.height):
            walls.add((0, y))
            walls.add((self.width - 1, y))

        # Add random inner pillars
        for _ in range(int(self.width * self.height * 0.18)):
            wx = rng.randint(2, self.width - 3)
            wy = rng.randint(2, self.height - 3)
            walls.add((wx, wy))

        start = (1, 1)
        goal = (self.width - 2, self.height - 2)
        walls.discard(start)
        walls.discard(goal)

        # Compute optimal path length via A*
        optimal_path = self._astar_solve(start, goal, walls)
        optimal_steps = len(optimal_path) if optimal_path else (self.width + self.height)

        # Target time: ~0.65s per step + baseline 12.0s
        target_time = round(12.0 + optimal_steps * 0.65, 1)

        course = SpeedrunCourse(
            seed=s,
            width=self.width,
            height=self.height,
            start=start,
            goal=goal,
            walls=list(walls),
            optimal_steps=optimal_steps,
            target_time_seconds=target_time,
        )
        self.active_course = course
        logger.info(f"Generated Procedural Speedrun Course #{s} ({self.width}x{self.height}, Target: {target_time}s)")
        return course

    def _astar_solve(
        self, start: Tuple[int, int], goal: Tuple[int, int], walls: Set[Tuple[int, int]]
    ) -> List[Tuple[int, int]]:
        """Finds the shortest obstacle-free path from start to goal."""
        frontier = []
        heapq.heappush(frontier, (0, start))
        came_from = {start: None}
        cost_so_far = {start: 0}

        while frontier:
            _, current = heapq.heappop(frontier)
            if current == goal:
                break

            for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                nxt = (current[0] + dx, current[1] + dy)
                if nxt in walls or not (0 <= nxt[0] < self.width and 0 <= nxt[1] < self.height):
                    continue

                new_cost = cost_so_far[current] + 1
                if nxt not in cost_so_far or new_cost < cost_so_far[nxt]:
                    cost_so_far[nxt] = new_cost
                    priority = new_cost + abs(goal[0] - nxt[0]) + abs(goal[1] - nxt[1])
                    heapq.heappush(frontier, (priority, nxt))
                    came_from[nxt] = current

        if goal not in came_from:
            return []

        # Reconstruct path
        curr = goal
        path = []
        while curr:
            path.append(curr)
            curr = came_from[curr]
        path.reverse()
        return path

    def execute_ai_speedrun(self) -> SpeedrunRunResult:
        """
        Simulates the AI VTuber playing the course with human-like stochastic jitter.
        """
        if not self.active_course:
            self.generate_course()

        course = self.active_course
        # Base run time: optimal steps * human step speed
        step_duration = random.uniform(0.55, 0.75)
        reaction_lag = random.uniform(1.2, 4.5)  # slight hesitation on corners
        actual_time = round((course.optimal_steps * step_duration) + reaction_lag, 2)

        won = actual_time <= course.target_time_seconds

        if won:
            margin = round(course.target_time_seconds - actual_time, 2)
            commentary = (
                f"[SPEEDRUN VICTORY] Beat Course #{course.seed} in {actual_time}s! "
                f"(Target: {course.target_time_seconds}s, beat by {margin}s)! "
                f"Celebrate the win and gloat to chatters who bet 'fail'!"
            )
        else:
            margin = round(actual_time - course.target_time_seconds, 2)
            commentary = (
                f"[SPEEDRUN CHOKE] Failed Course #{course.seed} by {margin}s! "
                f"(Time: {actual_time}s vs Target: {course.target_time_seconds}s)! "
                f"Express hilarious dramatic frustration and pay out chatters who bet 'fail'!"
            )

        return SpeedrunRunResult(
            course_seed=course.seed,
            completed=won,
            actual_time_seconds=actual_time,
            target_time_seconds=course.target_time_seconds,
            steps_taken=course.optimal_steps,
            commentary_prompt=commentary,
        )


if __name__ == "__main__":
    engine = ProceduralSpeedrunEngine()
    print("Testing Procedural Mini-Game & Speedrun Engine...")

    course = engine.generate_course(seed=4242)
    print(f"Course #{course.seed}: Start={course.start} -> Goal={course.goal}")
    print(f"Optimal Path: {course.optimal_steps} steps | Target Time: {course.target_time_seconds}s")

    result = engine.execute_ai_speedrun()
    print(f"\nSpeedrun Finished! Time: {result.actual_time_seconds}s (Target: {result.target_time_seconds}s)")
    print(f"Success: {result.completed}")
    print(f"\nAI Commentary Prompt:\n\"{result.commentary_prompt}\"")
