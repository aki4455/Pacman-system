import heapq
import logging
import traceback


logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

roads = {
    "Home":       [(2, "Bazar"), (6, "Cafe")],
    "Bazaar":     [(2, "Home"), (3, "Cafe"), (7, "Park")],
    "Cafe":       [(6, "Home"), (3, "Bazaar"), (1, "Park"), (8, "University")],
    "Park":       [(7, "Bazaar"), (1, "Cafe"), (2, "University")],
    "University": [(8, "Cafe"), (2, "Park")],
}




def djikstra(start, goal):
    passed_locations = [goal]
    current_position = goal
    path = [goal]
    cn= 1
    while True:
        
        if current_position == start:
            break
        print(f"main iteration: {cn}")
        print(f"Choosing the smallest from current: {roads[current_position]}")
        smallest_curr_time = float("inf")
        pp = None
        for tt, pl in roads[current_position]:
            if tt < smallest_curr_time:
                smallest_curr_time = tt
                pp = pl
        pos = roads[current_position].index((smallest_curr_time, pp))
        time, next_location = roads[current_position][pos]
        
        print(f"Chosen: {next_location}-{time}")
        
        for t, place in roads[next_location]:
            print(f"Next location's possible ways: {place, t}")
            if place in passed_locations:
                print(f"Removing the place from next location: {place}--{time}")
                roads[next_location].remove((t, place))
        
        passed_locations.append(next_location)
        print(f"Passed locations: {passed_locations}")
        current_position = next_location
        path.append(current_position)
        
        cn += 1
    print(f"\nPath: {path[::-1]}")        
djikstra("Home", "University")        
