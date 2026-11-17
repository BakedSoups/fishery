CREATE TABLE fish ( 
    id INTEGER PRIMARY KEY, 
    name CHAR NOT NULL, 
    cohesion_mode CHAR NOT NULL, 
    flock_radius INTEGER NOT NULL, 
    cohesion_angle INTEGER NOT NULL CHECK (cohesion_angle >= 0 and cohesion_angle <= 360),
    ray_distance  INTEGER NOT NULL, 
    separation_distance  INTEGER NOT NULL, 
    push_speed  INTEGER NOT NULL, 
    alignment_distance  INTEGER NOT NULL, 
    wall_range  INTEGER NOT NULL, 
    max_wall_turn_speed  INTEGER NOT NULL, 
    turn_smoothing_time  INTEGER NOT NULL
)
