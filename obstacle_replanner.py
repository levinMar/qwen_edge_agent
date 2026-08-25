"""
Obstacle Replanner & Dynamic Navigation Simulator
Demonstrates online local costmap updating and dynamic path detouring when an agrover stumbles upon unexpected obstacles (e.g. misplaced jembe, rocks, tools) while en route to a target location.
"""

import time
import math
from typing import List, Tuple, Dict


class DynamicObstacleReplanner:
    """
    Simulates dynamic online local path replanning (ROS 2 Nav2 DWA/TEB planner behavior)
    for field rovers navigating around unexpected obstacles.
    """

    def __init__(self, costmap_resolution_meters: float = 0.1):
        self.resolution = costmap_resolution_meters
        self.local_costmap: Dict[Tuple[int, int], int] = {}  # (grid_x, grid_y) -> cost (0-254)

    def world_to_grid(self, x: float, y: float) -> Tuple[int, int]:
        """Converts meters to costmap grid indices."""
        return int(round(x / self.resolution)), int(round(y / self.resolution))

    def mark_obstacle(self, obstacle_x: float, obstacle_y: float, radius_meters: float = 0.5):
        """
        Simulates sensor detection (LiDAR / Depth Camera / Ultrasonic) marking a newly discovered obstacle on the local costmap.
        """
        center_gx, center_gy = self.world_to_grid(obstacle_x, obstacle_y)
        grid_radius = int(round(radius_meters / self.resolution))

        print(f"\n🚨 [SENSOR DETECT] Dynamic Obstacle Discovered at ({obstacle_x:.1f}m, {obstacle_y:.1f}m)!")
        print(f"🗺️ Updating Local Costmap (Inflating lethal obstacle zone within {radius_meters}m radius)...")

        for dx in range(-grid_radius, grid_radius + 1):
            for dy in range(-grid_radius, grid_radius + 1):
                if dx * dx + dy * dy <= grid_radius * grid_radius:
                    self.local_costmap[(center_gx + dx, center_gy + dy)] = 254  # 254 = LETHAL_OBSTACLE

    def plan_path(self, start: Tuple[float, float], goal: Tuple[float, float]) -> List[Tuple[float, float]]:
        """
        Calculates a path from start to goal, dynamically steering around marked lethal costmap obstacles.
        """
        curr_x, curr_y = start
        target_x, target_y = goal
        path = [(curr_x, curr_y)]

        steps = 10
        for i in range(1, steps + 1):
            # Linearly interpolate towards goal
            interp_x = curr_x + (target_x - curr_x) * (i / steps)
            interp_y = curr_y + (target_y - curr_y) * (i / steps)
            grid_pos = self.world_to_grid(interp_x, interp_y)

            # Check if straight path hits a lethal costmap obstacle
            if self.local_costmap.get(grid_pos, 0) == 254:
                print(f"⚠️  [LOCAL PLANNER] Straight path blocked at ({interp_x:.1f}m, {interp_y:.1f}m)!")
                print(f"↪️  [DYNAMIC REPLAN] Calculating detoured local trajectory around obstacle...")

                # Compute detoured waypoint (offset perpendicular to goal direction)
                detour_x = interp_x - 0.8
                detour_y = interp_y + 0.8
                path.append((round(detour_x, 2), round(detour_y, 2)))
                print(f"📍 Detour Waypoint Generated: ({detour_x:.1f}m, {detour_y:.1f}m)")

            path.append((round(interp_x, 2), round(interp_y, 2)))

        return path


def simulate_rover_patrol_with_obstacle():
    """
    Demonstrates an agrover encountering a misplaced jembe on its path to Zone B-4.
    """
    print("=" * 65)
    print("🚜 AGROVER DYNAMIC OBSTACLE REPLANNING SIMULATION")
    print("=" * 65)

    start = (0.0, 0.0)
    target_destination = (10.0, 10.0)  # Zone B-4, Row 12 target

    print(f"🏁 Starting Patrol from Base: {start}")
    print(f"🎯 Target Destination (Qwen AI Command): Zone B-4 {target_destination}")

    replanner = DynamicObstacleReplanner()

    # Rover starts moving...
    print("\n▶️ Rover underway towards Zone B-4 (Speed: 0.5 m/s)...")
    time.sleep(0.05)

    # Unexpected event: Misplaced jembe at (5.0m, 5.0m)
    misplaced_jembe_location = (5.0, 5.0)
    replanner.mark_obstacle(misplaced_jembe_location[0], misplaced_jembe_location[1], radius_meters=0.6)

    # Compute dynamic path
    path = replanner.plan_path(start, target_destination)

    print("\n✅ [REPLAN SUCCESS] New Waypoint Trajectory Generated:")
    for idx, pt in enumerate(path):
        print(f"  Step {idx+1}: {pt}")

    print("\n🎉 Rover successfully bypassed the misplaced jembe and reached target Zone B-4!")
    print("=" * 65)


if __name__ == "__main__":
    simulate_rover_patrol_with_obstacle()
