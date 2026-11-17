import pyglet
import random
import math
from pyglet.math import Vec2
window = pyglet.window.Window(800, 600)

class Boid: 
    def __init__(self, shape: pyglet.shapes.Circle, direction:Vec2): 
        self.shape = shape
        self.direction = direction
        self.turn_speed = 0.0
        self.wait = True
        self.has_turned = False


def draw_boid(pos_x, pos_y, radius): 
    direction = Vec2(random.randint(2,5), random.randint(2,5)).normalize()
    return Boid(pyglet.shapes.Circle(pos_x,pos_y, radius,segments =3), direction)

def raycast_wall(dot, direction, distance=20):
    # Starting position of the ray
    start = Vec2(dot.x, dot.y)

    # Endpoint of the ray
    end = start + direction.normalize() * distance

    # Keep the ray endpoint at least 20 pixels inside the boid's wall boundary.
    clearance = dot.radius + 20
    hit = (
        end.x <= clearance or
        end.x >= window.width - clearance or
        end.y <= clearance or
        end.y >= window.height - clearance
    )

    return hit

def raycast_boid(dot, direction, boids, distance =1, margin = 20): 
    # Starting position of the ray
    start = Vec2(dot.x, dot.y)
    ray = direction.normalize()
    # Endpoint of the ray

    for boid in boids: 
        boid = boid.shape
        if boid is dot:
            continue
        target = Vec2(boid.x, boid.y)
        # vector from target boid to this boid
        offset = target - start
        # 
        projection = offset.dot(ray)

        if 0 <= projection <= distance: 
            # Closest point on ray to target
            closest = start + ray * projection

            # Check if ray intersects the target's hitbox
            if (target - closest).length() <= boid.radius + margin:
                return boid

    return None

def boid_in_radius(dot,boids, distance = 20): 
    start = Vec2(dot.x, dot.y)
    for boid in boids: 
        
        boid = boid.shape
        if boid is dot:
            continue
        target = Vec2(boid.x, boid.y)
        if (start - target).length() <= distance: 
            return target

speed = 100 
boid_list = []
for i in range(100):
    boid_list.append(draw_boid(100,100,10))

cohesion_mode = "conga"  # "conga" follows one boid; "flock" seeks the neighbor center.
flock_radius = 90  # Pixels within which neighbors contribute to flock cohesion.
cohesion_margin = 5    
cohesion_angle = math.radians(20)
distance = 600
separation_distance = 30
push_speed = 40  # Pixels per second
alignment_distance = 20

wall_range = 60  # Pixels from the boid's edge to start turning.
max_wall_turn_speed = 360  # Degrees per second.
turn_smoothing_time = 0.15  # Seconds for steering changes to settle.


def smooth_direction(boid, previous_direction, dt):
    # Smooth the signed turn across the -pi/pi boundary, not the vector itself.
    angle = math.atan2(
        previous_direction.x * boid.direction.y - previous_direction.y * boid.direction.x,
        previous_direction.dot(boid.direction),
    )
    blend = -math.expm1(-dt / turn_smoothing_time)
    boid.turn_speed += (angle / dt - boid.turn_speed) * blend
    boid.direction = previous_direction.rotate(boid.turn_speed * dt)

def reset_flag(dt):
    for boid in boid_list:
        boid.wait = True
    for boid in random.sample(boid_list, len(boid_list) // random.randint(3,20 )):
        boid.wait = False


def get_cohesion_target(dot, boids):
    if cohesion_mode == "conga":
        if dot.wait:
            return None
        return raycast_boid(dot.shape, dot.direction, boids, distance, cohesion_margin)
    if cohesion_mode != "flock":
        raise ValueError('cohesion_mode must be "conga" or "flock"')

    # Every boid participates in flock cohesion, regardless of its wait flag.
    position = Vec2(dot.shape.x, dot.shape.y)
    # Accumulate neighbor positions first; divide later to find their average.
    center = Vec2(0, 0)
    count = 0
    # Check every boid to see whether it belongs to this boid's local group.
    for neighbor in boids:
        # Skip this boid itself so it does not contribute to its own target.
        if neighbor is dot:
            continue
        neighbor_position = Vec2(neighbor.shape.x, neighbor.shape.y)
        # Subtract positions to get the offset; its length is the distance.
        # Only include neighbors at or inside flock_radius, in any direction.
        if (neighbor_position - position).length() <= flock_radius:
            center += neighbor_position
            count += 1
    # Average the included positions. With no neighbors, return no target
    # instead of dividing by zero.
    return center / count if count else None


def get_cohesion_angle(dot, dt, target):
    offset = Vec2(target.x, target.y) - Vec2(dot.shape.x, dot.shape.y)
    if offset.length() < 1e-8:
        return 0.0
    target_direction = offset.normalize()
    angle = math.atan2(
        dot.direction.x * target_direction.y - dot.direction.y * target_direction.x,
        dot.direction.dot(target_direction)
    )

    # Limit cohesion to the configured turn rate.
    max_turn = cohesion_angle * dt
    turn = max(-max_turn, min(max_turn, angle))
    return turn

def get_alignment_angle(dot, dt, target):
    desired = target.direction
    angle = math.atan2(
        dot.direction.x * desired.y - dot.direction.y * desired.x,
        dot.direction.dot(desired),
    )
    max_turn = math.radians(90) * dt
    return max(-max_turn, min(max_turn, angle))


def get_seperation_force(dot, dt, target): 
    # Return the displacement; update() applies it to the boid.
    away = Vec2(dot.shape.x, dot.shape.y) - target
    if away.length() == 0:
        away = Vec2(1, 0)
    gap = away.length()
    # pushes the boid instead 
    if 0 < gap < separation_distance:
        push = min(separation_distance - gap, push_speed * dt)
        return away.normalize() * push
    return Vec2(0, 0)
    
def update(dt):
    if dt <= 0:
        return
    for dot in boid_list:
        if not dot.wait:
            # Allow another random turn next time this boid starts waiting.
            dot.has_turned = False
        elif not dot.has_turned:
            dot.direction = dot.direction.rotate(math.radians(random.randint(-180, 180)))
            dot.turn_speed = 0.0
            dot.has_turned = True

        # Capture the new heading so smoothing does not undo the random turn.
        previous_direction = dot.direction
        boid_speed = speed if dot.wait else 10
        
        dot.shape.position += dot.direction * boid_speed * dt
        # Follow one boid or steer toward the local flock's center.
        target = get_cohesion_target(dot, boid_list) if not dot.wait else None
        
        if target is not None: 
            turn = get_cohesion_angle(dot, dt, target)
            dot.direction = dot.direction.rotate(turn)

        # make sure they are seperated
        target_boid = boid_in_radius(dot.shape, boid_list, separation_distance)
        if target_boid is not None:
            push = get_seperation_force(dot, dt, target_boid)
            dot.shape.position += push
            dot.shape.x = max(dot.shape.radius, min(dot.shape.x, window.width - dot.shape.radius))
            dot.shape.y = max(dot.shape.radius, min(dot.shape.y, window.height - dot.shape.radius))

        # Match the direction of the first other boid within range.
        for nearby_boid in boid_list:
            # Waiting boids keep their heading instead of matching neighbors.
            if dot.wait:
                break
            if nearby_boid is dot:
                continue
            offset = Vec2(nearby_boid.shape.x, nearby_boid.shape.y) - Vec2(dot.shape.x, dot.shape.y)
            if offset.length() <= alignment_distance:
                turn = get_alignment_angle(dot, dt, nearby_boid)
                dot.direction = dot.direction.rotate(turn)
                break

        # Turn inward faster as the boid's edge approaches a wall.
        walls = (
            (dot.shape.x - dot.shape.radius, Vec2(1, 0)),
            (window.width - dot.shape.radius - dot.shape.x, Vec2(-1, 0)),
            (dot.shape.y - dot.shape.radius, Vec2(0, 1)),
            (window.height - dot.shape.radius - dot.shape.y, Vec2(0, -1)),
        )
        inward = Vec2(0, 0)
        proximity = 0
        for gap, normal in walls:
            strength = max(0, min(1, 1 - gap / wall_range))
            inward += normal * strength
            proximity = max(proximity, strength)

        if inward.length() > 0:
            desired = inward.normalize()
            angle = math.atan2(
                dot.direction.x * desired.y - dot.direction.y * desired.x,
                dot.direction.dot(desired),
            )
            max_turn = math.radians(max_wall_turn_speed) * proximity * dt
            turn = max(-max_turn, min(max_turn, angle))
            dot.direction = dot.direction.rotate(turn)

        # Ease into the combined steering requested by neighbors and walls.
        smooth_direction(dot, previous_direction, dt)

    # if its at a border stop
        dot.shape.x = max(dot.shape.radius, min(dot.shape.x, window.width - dot.shape.radius))
        dot.shape.y = max(dot.shape.radius, min(dot.shape.y, window.height - dot.shape.radius))
                

        

@window.event
def on_draw():
    window.clear()
    # dot.draw()
    # dot2.draw()
    for dot in boid_list: 
        # Pyglet uses clockwise degrees; atan2 gives counterclockwise radians.
        dot.shape.rotation = -math.degrees(math.atan2(dot.direction.y, dot.direction.x))
        dot.shape.draw()

# Update movement 60 times per second
reset_flag(0)
pyglet.clock.schedule_interval(reset_flag, 3)
pyglet.clock.schedule_interval(update, 1 / 60)

pyglet.app.run()
