import sys
import queue as Q
import datetime
import copy


# Constants
ME = 1
FOE = 0
NEUTRAL = -1
END_GAME = False

# Limits
spawn_recycle_prio_limit = -20
spawn_recycle_prio_limit_increment = -2
foe_cell_multiplier = 2
vertical_attack = ""
horizontal_attack = ""
init = True

# Game input
width, height = [int(i) for i in input().split()]
print(f"width: {width}, height: {height}", file=sys.stderr)


# Functions
def find_base(a, b, c, d):
    """Finds and returns the middle point of 4 coordinate pairs."""
    x = (a[0] + b[0] + c[0] + d[0]) / 4
    y = (a[1] + b[1] + c[1] + d[1]) / 4

    return (int(x), int(y))

def find_angle_of_attack(my_tanks, foe_tanks):
    """Finds the angle of attack of the enemy base relative to my base."""
    my_base = find_base(*my_tanks)
    foe_base = find_base(*foe_tanks)

    if my_base[0] < foe_base[0]:
        horizontal_attack = "right"
    else:
        horizontal_attack = "left"
    
    if my_base[1] < height/2:
        vertical_attack = "down"
    else:
        vertical_attack = "up"

    return horizontal_attack, vertical_attack


def get_neighbors(cell, get_diagonals=False):
    """Returns the neighbors of a given cell. If get_diagonals=True it will also return the diagonal neighbors as well."""

    cols = width - 1
    rows = height - 1

    col, row = cell
    up = (col, row - 1)
    down = (col, row + 1)
    left = (col - 1, row)
    right = (col + 1, row)

    if vertical_attack == "left" and horizontal_attack == "up":
        moves = [left, up, right, down]
    elif vertical_attack == "right" and horizontal_attack == "up":
       moves = [right, up, left, down]
    elif vertical_attack == "left" and horizontal_attack == "down":
       moves = [left, down, right, up]
    elif vertical_attack == "right" and horizontal_attack == "down":
       moves = [right, down, left, up]
    else:
        print("Error at get_neighbor()", file=sys.stderr)
        moves = []

    if get_diagonals:
        moves = [(col + 1, row + 1), (col - 1, row + 1), (col + 1, row - 1), (col - 1, row - 1)]
    neighbors = []

    for c, r in moves:
        if 0 <= r <= rows and 0 <= c <= cols and (c, r) != cell:
            neighbors.append((c, r))

    return neighbors


def get_avaliable_neighbors(cell, matrix, get_diagonals=False):
    """Returns the neighbors of a given cell that are movable. If get_diagonals=True it will also return the diagonal neighbors as well."""

    avaliable_neighbors = []
    neighbors = get_neighbors(cell)

    for neighbor in neighbors:
        if check_cell_movability(neighbor, matrix):
            avaliable_neighbors.append(neighbor)

    if get_diagonals:
        diagonal_neighbors = get_neighbors(cell, get_diagonals=True)
        for diagonal_neighbor in diagonal_neighbors:
            c,r = diagonal_neighbor
            diagonal_set = set([(c, r-1), (c, r+1), (c+1, r), (c-1,r)])
            if len(diagonal_set.intersection(set(avaliable_neighbors))) > 0 and check_cell_movability(diagonal_neighbor, matrix):
                avaliable_neighbors.append(diagonal_neighbor)

    return avaliable_neighbors


def check_cell_movability(cell, matrix):
    """Checks cell movability."""
    to_be_recycled_cond = matrix[cell]["scrap_amount"] > 1 if matrix[cell]["in_range_of_recycler"] == 1 else True
    return (matrix[cell]["scrap_amount"] != 0) and (matrix[cell]["recycler"] != 1) and to_be_recycled_cond


def get_manhattan_distance(cell_1, cell_2):
    """Manhattan distance between two cells."""
    x = abs(cell_1[0] - cell_2[0])
    y = abs(cell_1[1] - cell_2[1])
    return x + y


def get_all_reachable_cells_with_path(start, matrix):
    """ Returns a dictionary of reachable cells from the start position. Keys of the dictionary are the cells, their value refers to their closest path.
    It uses BFS algorithm."""

    frontier = []
    frontier.append(start)
    came_from_dict = dict()
    came_from_dict[start] = None

    while frontier:
        current = frontier.pop(0)
        for next_neighbor in get_avaliable_neighbors(current, matrix):
            if next_neighbor not in came_from_dict:
                frontier.append(next_neighbor)
                came_from_dict[next_neighbor] = current

    return came_from_dict


def find_path_to_goal(start, goal, came_from_dict):
    """ Creates a path from start to goal using a came_from_dict. Returns an empty list if goal is not reachable from start position.  """

    current = goal
    path = []

    if goal not in came_from_dict:
        return path

    while current != start:
        path.append(current)
        current = came_from_dict[current]
    path.reverse()
    return path


def has_movable_cell_in_reach(cell, matrix):
    """Checks if a cell has a cell that is movable in its reach."""
    came_from_dict = get_all_reachable_cells_with_path(cell, matrix)

    for cell, came_from in came_from_dict.items():
        if matrix[cell]["owner"] != ME:
            return True
        else:
            continue
    return False

def has_movable_cell_in_reach_2(cell, matrix):
    """
    Checks if a cell has a cell that is movable in its reach more efficiently. It doesn't start out with all the reachable cells,
    but starts with the neighbors of the cells. If a cell found is reachable, stops the iteration.
    Returns the bool value and also the came_from_dict.
    """
    frontier = []
    frontier.append(cell)
    came_from_dict = dict()
    came_from_dict[cell] = None

    while frontier:
        current = frontier.pop(0)
        for next_neighbor in get_avaliable_neighbors(current, matrix):
            if next_neighbor not in came_from_dict:
                frontier.append(next_neighbor)
                came_from_dict[next_neighbor] = current
                if matrix[next_neighbor]["owner"] != ME: 
                    return True, came_from_dict

    return False, came_from_dict


def count_movable_cells_around_cell(cell, matrix, cond, value):
    """Counting movable cells around a given cell. Direct contact cells (one step from the initial cell) count as 2, diagonal neighbors count as 1."""

    # TODO: it is delayed by one round. should find a way to fix this

    count = 0
    neighbors = get_avaliable_neighbors(cell, matrix, get_diagonals=True)

    for neighbor in neighbors:
        to_be_recycled_cond = matrix[neighbor]["scrap_amount"] > 1 if matrix[neighbor][
                                                                          "in_range_of_recycler"] == 1 else True
        if matrix[neighbor][cond] == value and to_be_recycled_cond:

            # if neighbor is diagonal neighbor
            if get_manhattan_distance(cell, neighbor) > 1:
                count += 1
            # 1 step movement reachable
            else:
                count += 2

    return count


def find_path_to_closest_empty_cell(cell, matrix):
    """Finds a path to the closest empty cell (not owned by me)."""
    came_from_dict = get_all_reachable_cells_with_path(cell, matrix)

    # TODO: find the closest
    for came_from in came_from_dict.keys():
        if matrix[came_from]["owner"] != ME:
            return find_path_to_goal(cell, came_from, came_from_dict)


def create_spawn_point_queue(can_spawn_cells, matrix):
    #THIS
    """Creates a priority queue of the best spawns for new tanks."""

    spawn_queue = Q.PriorityQueue()
    dont_check_cells = set()

    for cell in can_spawn_cells:
        if cell in dont_check_cells:
            neutral_cells = count_movable_cells_around_cell(cell, matrix, "owner", NEUTRAL)
            foe_cells = count_movable_cells_around_cell(cell, matrix, "owner", FOE)
            #        me_cells = count_cond_cells_around_cell(cell, matrix, "owner", ME)

            prio = 24 - neutral_cells - (foe_cells * foe_cell_multiplier)
            spawn_queue.put((prio, cell, neutral_cells, foe_cells))
            continue

        cond, came_from_dict = has_movable_cell_in_reach_2(cell, matrix)
        dont_check_cells.update(list(came_from_dict.keys()))

        if cond:

            neutral_cells = count_movable_cells_around_cell(cell, matrix, "owner", NEUTRAL)
            foe_cells = count_movable_cells_around_cell(cell, matrix, "owner", FOE)
            #        me_cells = count_cond_cells_around_cell(cell, matrix, "owner", ME)

            prio = 24 - neutral_cells - (foe_cells * foe_cell_multiplier)
            spawn_queue.put((prio, cell, neutral_cells, foe_cells))


    return spawn_queue


def calculate_scrap_amount_for_cell(cell, matrix):
    """Calculates the scrap amount around the cell. Returns False if it is next to a neighbor."""

    scrap_amount = 0
    actual_cell_scrap_amount = matrix[cell]["scrap_amount"]
    _neighbors = get_neighbors(cell, get_diagonals=False)
    _neighbors += get_neighbors(cell, get_diagonals=True)
    recycler_neighbors = [n for n in _neighbors if matrix[n]["recycler"] == 1]

    # Avoid putting recyclers next to recyclers
    if len(recycler_neighbors) > 0:
        return False
    neighbors = get_neighbors(cell)
    for neighbor in neighbors:
        if matrix[neighbor]["scrap_amount"] >= actual_cell_scrap_amount:
            scrap_amount += actual_cell_scrap_amount
        else:
            scrap_amount += matrix[neighbor]["scrap_amount"]

    prio = -scrap_amount
    return prio


def create_build_recycle_queue(can_build_cells, matrix, attackable_foe_tanks):
    """Creates a queue for building new recyclers. If there is an attackable foe tank (meaning I can spawn a recycler next to an enemy tank) it gets 
    a very high priority. Other than this, it prioritizes cells with higher scrap amount."""

    # TODO: don't put next to my units

    recycler_queue = Q.PriorityQueue()
    for cell in can_build_cells:
        
        if cell in attackable_foe_tanks:
            edge_prio = -1000
            recycler_queue.put((edge_prio, cell))
            continue

        scrap_prio = calculate_scrap_amount_for_cell(cell, matrix)
        recycler_queue.put((scrap_prio, cell))

    return recycler_queue


def filter_recyclers_from_queue(recycler_queue):
    """Returns a list of positions to build a recycler on (to be used in a for loop)."""

    recycler_list = []
    for prio, pos in recycler_queue.queue:
        if prio < spawn_recycle_prio_limit:
            recycler_list.append(pos)

    return recycler_list


def find_attackable_foe_tanks(can_build_cells, matrix):
    """Finds tanks that can be attacked - a recycler can be built next to them."""

    attackable_foe_tanks = []
    for cell in can_build_cells:
        add_to_list = False
        neighbors = get_neighbors(cell)

        for neighbor in neighbors:
            if matrix[neighbor]["owner"] == FOE and matrix[neighbor]["units"] > 0:
                add_to_list = True

        # Avoid putting to many recyclers next to each other
        if matrix[cell]["in_range_of_recycler"] == 1:
            add_to_list = False

        if add_to_list:
            attackable_foe_tanks.append(cell)

    return attackable_foe_tanks



while True:
    # Round changing variables
    start_time = datetime.datetime.now()
    map_info = {}
    my_tanks = []
    foe_tanks = []
    can_spawn_cells = []
    can_build_cells = []

    # Table info
    my_matter, opp_matter = [int(i) for i in input().split()]
    for i in range(height):
        for j in range(width):
            scrap_amount, owner, units, recycler, can_build, can_spawn, in_range_of_recycler = [int(k) for k in input().split()]

            cell_info = {"scrap_amount": scrap_amount,
                         "owner": owner,
                         "units": units,
                         "recycler": recycler,
                         "can_build": can_build,
                         "can_spawn": can_spawn,
                         "in_range_of_recycler": in_range_of_recycler}

            pos = j, i
            map_info[pos] = cell_info

            if owner == ME and units > 0:
                for _ in range(units):
                    my_tanks.append(pos)

            if owner == FOE and units > 0:
                foe_tanks.append(pos)

            if can_spawn == 1:
                can_spawn_cells.append(pos)

            if can_build == 1:
                can_build_cells.append(pos)

    elapsed = datetime.datetime.now() - start_time
    print(f"Elapsed time after reading in inputs: {elapsed.total_seconds()*1000}", file=sys.stderr)

    if init:
        vertical_attack, horizontal_attack = find_angle_of_attack(my_tanks, foe_tanks)

    
    msg = ""



    # MOVING TANKS
    print(f"number of tanks {len(my_tanks)}", file = sys.stderr)
    filtered_map = copy.deepcopy(map_info)
    moved_tanks = []
    for tank_pos in my_tanks:
        go_to = find_path_to_closest_empty_cell(tank_pos, filtered_map)

        if go_to:
            go_to_first = go_to[0]
            msg += f"MOVE {1} {tank_pos[0]} {tank_pos[1]} {go_to_first[0]} {go_to_first[1]};"
            filtered_map[go_to_first]["owner"] = ME

            moved_tanks.append(go_to_first)



    # BUILDING RECYCLERS
    attackable_foe_tanks = find_attackable_foe_tanks(can_build_cells, map_info)
    print(f"Attackable foe tanks: {attackable_foe_tanks}", file=sys.stderr)

    build_recycle_queue = create_build_recycle_queue(can_build_cells, map_info, attackable_foe_tanks)
    print(f"recycle queue: {build_recycle_queue.queue}", file=sys.stderr)
    elapsed = datetime.datetime.now() - start_time
    print(f"Elapsed time after recycle queue: {elapsed.total_seconds()*1000}", file=sys.stderr)

    # End game started (only build recyclers based on scrap amount until enemy is reached. After that it is ued only for attacking)
    if len(attackable_foe_tanks) > 0:
        spawn_recycle_prio_limit = -500

    recycler_list = filter_recyclers_from_queue(build_recycle_queue)
    spawn_recycle_prio_limit += spawn_recycle_prio_limit_increment
    print(f"spawn_recycle_prio_limit: {spawn_recycle_prio_limit}", file=sys.stderr)

    for recycler in recycler_list:
        if not build_recycle_queue.empty() and my_matter >= 10:
            
            best_recycler = build_recycle_queue.get()
            msg += f"BUILD {best_recycler[1][0]} {best_recycler[1][1]};"
            
            my_matter -= 10



    # SPAWNING NEW TANKS
    print(f"number of can spawn cells: {len(can_spawn_cells)}", file = sys.stderr)
    best_pos_to_spawn_queue = create_spawn_point_queue(can_spawn_cells, map_info)

    print(f"spawn queue: {best_pos_to_spawn_queue.queue[:10]}", file=sys.stderr)
    number_of_spawnable_tanks = my_matter // 10

    elapsed = datetime.datetime.now() - start_time
    print(f"Elapsed time after spawn queue: {elapsed.total_seconds()*1000}", file=sys.stderr)

    if not best_pos_to_spawn_queue.empty() and number_of_spawnable_tanks > 0:
        best_pos_to_spawn = best_pos_to_spawn_queue.get()[1]
        msg += f"SPAWN {number_of_spawnable_tanks} {best_pos_to_spawn[0]} {best_pos_to_spawn[1]};"



    if msg == "":
        msg += f"WAIT;"
    msg += f"MESSAGE Yeet"

    print(f"About to print: {msg}", file=sys.stderr)
    print(msg)

    init = False

