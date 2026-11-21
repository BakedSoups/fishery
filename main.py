import pyglet
import random
import math
from pyglet.math import Vec2
window = pyglet.window.Window(800, 600)

class Boid: 
    def __init__(self, shape: pyglet.shapes.Circle, direction:Vec2): 
        self.shape = shape
        self.direction = direction
        self.is_leader = False
        self.follow_target = None
        self.turn_speed = 0.0
        self.has_turned = False
        self.pause_timer = 0.0
        self.pause_cooldown = random.uniform(1.0, 4.0)
        self.pause_turn_remaining = 0.0
        self.slow_timer = 0.0
        self.wave_delay = 0.0
        self.wave_kind = None


speed = 100
cohesion_margin = 20  # Width of the ray corridor around a fish.
ray_distance = 600
follow_distance = 28  # How far behind the fish ahead a follower aims.
leader_fraction = 0.12
separation_distance = 20
leader_separation_distance = 36
push_speed = 40  # Pixels per second
leader_push_speed = 90
follow_speed = 80
follow_steer_strength = 10.0  # How quickly followers turn toward their target.
pause_chance_per_second = 0.08
pause_duration = (3.0, 5.0)  # Seconds each fish remains stopped and rotating.
pause_turn_speed = math.radians(240)
slow_move_chance = 0.45
slow_move_duration = (3.0, 5.0)
slow_speed_factor = 0.3
wave_follow_delay = 0.35
leader_shift_interval = 8

wall_range = 60  # Pixels from the boid's edge to start turning.
max_wall_turn_speed = 360  # Degrees per second.
leader_wall_turn_factor = 0.35  # Leaders are less affected by wall steering.
turn_smoothing_time = 0.15  # Seconds for steering changes to settle.



def draw_boid(pos_x, pos_y, radius): 
    direction = Vec2(random.randint(2,5), random.randint(2,5)).normalize()
    return Boid(pyglet.shapes.Circle(pos_x,pos_y, radius,segments =3), direction)

def raycast_wall(dot, direction, ray_distance=20):
    # Starting position of the ray
    start = Vec2(dot.x, dot.y)

    # Endpoint of the ray
    end = start + direction.normalize() * ray_distance

    # Keep the ray endpoint at least 20 pixels inside the boid's wall boundary.
    clearance = dot.radius + 20
    hit = (
        end.x <= clearance or
        end.x >= window.width - clearance or
        end.y <= clearance or
        end.y >= window.height - clearance
    )

    return hit

def raycast_boid(dot, direction, boids, ray_distance=1, margin=20):
    # Starting position of the ray
    start = Vec2(dot.x, dot.y)
    ray = direction.normalize()
    # Endpoint of the ray

    closest_boid = None
    closest_projection = ray_distance
    for candidate in boids:
        boid = candidate.shape
        if boid is dot:
            continue
        target = Vec2(boid.x, boid.y)
        # vector from target boid to this boid
        offset = target - start
        # 
        projection = offset.dot(ray)

        if 0 <= projection <= ray_distance and projection < closest_projection:
            # Closest point on ray to target
            closest = start + ray * projection

            # Check if ray intersects the target's hitbox
            if (target - closest).length() <= boid.radius + margin:
                closest_boid = candidate
                closest_projection = projection

    return closest_boid

def boid_in_radius(dot,boids, ray_distance = 20): 
    start = Vec2(dot.x, dot.y)
    for boid in boids: 
        
        boid = boid.shape
        if boid is dot:
            continue
        target = Vec2(boid.x, boid.y)
        if (start - target).length() <= ray_distance: 
            return target

def smooth_direction(boid, previous_direction, dt):
    # Smooth the signed turn across the -pi/pi boundary, not the vector itself.
    angle = math.atan2(
        previous_direction.x * boid.direction.y - previous_direction.y * boid.direction.x,
        previous_direction.dot(boid.direction),
    )
    blend = -math.expm1(-dt / turn_smoothing_time)
    boid.turn_speed += (angle / dt - boid.turn_speed) * blend
    boid.direction = previous_direction.rotate(boid.turn_speed * dt)

def reset_flag(delta):
    # Leaders are selected occasionally, but remain leaders until the next
    # reset. Every other fish is a follower.
    leader_count = max(1, round(len(boid_list) * leader_fraction))
    leaders = set(random.sample(boid_list, leader_count))
    for boid in boid_list:
        boid.is_leader = boid in leaders
        boid.follow_target = None
        boid.wave_delay = 0.0
        boid.wave_kind = None
        boid.has_turned = False


def get_conga_target(dot, boids):
    if dot.is_leader:
        return None

    # Keep following the same fish instead of selecting a new fish every
    # frame. Reacquire only after the current target is clearly lost.
    target = dot.follow_target
    if target is not None:
        offset = Vec2(target.shape.x, target.shape.y) - Vec2(dot.shape.x, dot.shape.y)
        projection = offset.dot(dot.direction)
        lateral = abs(offset.x * dot.direction.y - offset.y * dot.direction.x)
        target_lost = (
            offset.length() > ray_distance * 1.2 or
            projection < -follow_distance or
            lateral > target.shape.radius + cohesion_margin * 2
        )
        if target_lost:
            target = None

    if target is None:
        target = raycast_boid(dot.shape, dot.direction, boids, ray_distance, cohesion_margin)
        dot.follow_target = target
    if target is None:
        return None

    # Aim behind the fish so the follower settles into a line.
    return Vec2(target.shape.x, target.shape.y) - target.direction * follow_distance


def apply_follow_steering(dot, target, dt):
    """Apply a seek force toward the point behind the fish ahead."""
    offset = Vec2(target.x, target.y) - Vec2(dot.shape.x, dot.shape.y)
    if offset.length() < 1e-8:
        return

    desired_direction = offset.normalize()
    steering = desired_direction - dot.direction
    # Integrate the steering force and normalize it back into a heading.
    # This is stronger and more responsive than applying a tiny fixed turn.
    response = min(1.0, follow_steer_strength * dt)
    dot.direction = (dot.direction + steering * response).normalize()

def get_seperation_force(dot, dt, target): 
    # Return the displacement; update() applies it to the boid.
    away = Vec2(dot.shape.x, dot.shape.y) - target
    if away.length() == 0:
        away = Vec2(1, 0)
    gap = away.length()
    # pushes the boid instead 
    separation_limit = leader_separation_distance if dot.is_leader else separation_distance
    if 0 < gap < separation_limit:
        max_push_speed = leader_push_speed if dot.is_leader else push_speed
        push = min(separation_limit - gap, max_push_speed * dt)
        return away.normalize() * push
    return Vec2(0, 0)
    
def update(dt):
    if dt <= 0:
        return
    for dot in boid_list:
        dot.pause_cooldown = max(0.0, dot.pause_cooldown - dt)

        # Propagate a leader's stop/slow state down the chain. The delay makes
        # the behavior travel backward through the line instead of happening
        # to every fish on the same frame.
        if not dot.is_leader and dot.wave_delay <= 0 and dot.pause_timer <= 0 and dot.slow_timer <= 0:
            target = dot.follow_target
            if target is not None:
                if target.pause_timer > 0:
                    dot.wave_kind = "pause"
                    dot.wave_delay = wave_follow_delay
                elif target.slow_timer > 0:
                    dot.wave_kind = "slow"
                    dot.wave_delay = wave_follow_delay

        if dot.wave_delay > 0:
            dot.wave_delay -= dt
            if dot.wave_delay <= 0:
                if dot.wave_kind == "pause":
                    dot.pause_timer = random.uniform(*pause_duration)
                    dot.pause_turn_remaining = random.choice((-1, 1)) * math.radians(random.uniform(120, 220))
                elif dot.wave_kind == "slow":
                    dot.slow_timer = random.uniform(*slow_move_duration)
                dot.wave_kind = None
                dot.pause_cooldown = random.uniform(2.0, 6.0)

        # Occasionally stop and rotate away before continuing. This gives the
        # school some independent motion without changing the follow target.
        if dot.pause_timer > 0:
            turn = max(-pause_turn_speed * dt, min(pause_turn_speed * dt, dot.pause_turn_remaining))
            dot.direction = dot.direction.rotate(turn)
            dot.pause_turn_remaining -= turn
            dot.pause_timer -= dt
            if dot.pause_timer <= 0:
                dot.pause_timer = 0.0
                dot.pause_turn_remaining = 0.0
                dot.pause_cooldown = random.uniform(2.0, 6.0)
            continue

        if dot.wave_delay <= 0 and dot.pause_cooldown <= 0 and random.random() < pause_chance_per_second * dt:
            if random.random() < slow_move_chance:
                dot.slow_timer = random.uniform(*slow_move_duration)
            else:
                dot.pause_timer = random.uniform(*pause_duration)
                dot.pause_turn_remaining = random.choice((-1, 1)) * math.radians(random.uniform(120, 220))
                continue

        if not dot.is_leader:
            # Followers are free to pause and turn again later.
            dot.has_turned = False
        elif not dot.has_turned:
            # Leaders keep their current heading when the leader set resets.
            # Their initial direction and wall avoidance provide the motion.
            dot.has_turned = True

        # Capture the new heading so smoothing does not undo the random turn.
        previous_direction = dot.direction
        boid_speed = speed if dot.is_leader else follow_speed
        if dot.slow_timer > 0:
            boid_speed *= slow_speed_factor
            dot.slow_timer -= dt
            if dot.slow_timer <= 0:
                dot.slow_timer = 0.0
                dot.pause_cooldown = random.uniform(2.0, 6.0)
        
        dot.shape.position += dot.direction * boid_speed * dt
        # Follow the latched fish ahead when this fish is not a leader.
        target = get_conga_target(dot, boid_list) if not dot.is_leader else None
        
        if target is not None:
            apply_follow_steering(dot, target, dt)

        # make sure they are seperated
        separation_radius = leader_separation_distance if dot.is_leader else separation_distance
        target_boid = boid_in_radius(dot.shape, boid_list, separation_radius)
        if target_boid is not None:
            push = get_seperation_force(dot, dt, target_boid)
            dot.shape.position += push
            dot.shape.x = max(dot.shape.radius, min(dot.shape.x, window.width - dot.shape.radius))
            dot.shape.y = max(dot.shape.radius, min(dot.shape.y, window.height - dot.shape.radius))

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
            wall_turn_factor = leader_wall_turn_factor if dot.is_leader else 1.0
            max_turn = math.radians(max_wall_turn_speed) * wall_turn_factor * proximity * dt
            turn = max(-max_turn, min(max_turn, angle))
            dot.direction = dot.direction.rotate(turn)

        # Generic smoothing would damp the seek force above, so only use it
        # for leaders.
        if dot.is_leader:
            smooth_direction(dot, previous_direction, dt)

    # if its at a border stop
        dot.shape.x = max(dot.shape.radius, min(dot.shape.x, window.width - dot.shape.radius))
        dot.shape.y = max(dot.shape.radius, min(dot.shape.y, window.height - dot.shape.radius))
                
boid_list = []
for i in range(100):
    boid_list.append(draw_boid(
        random.randint(30, window.width - 30),
        random.randint(30, window.height - 30),
        10,
    ))
        

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
pyglet.clock.schedule_interval(reset_flag, leader_shift_interval)
pyglet.clock.schedule_interval(update, 1 / 60)

pyglet.app.run()
