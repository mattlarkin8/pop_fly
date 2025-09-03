
# core.py

def calculate_distance(lat1, lon1, lat2, lon2):
    # Simplified calculation without elevation
    # Assuming a flat Earth for simplicity
    from math import radians, cos, sin, sqrt
    R = 6371  # Radius of the Earth in km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2) * sin(dlat/2) + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2) * sin(dlon/2)
    c = 2 * sqrt(a)
    distance = R * c
    return distance

# Other functions that previously used elevation have been updated or removed.
