def find_next_position(used_x, step=540):
    x = 540
    while True:
        if x not in used_x:
            used_x.append(x)
            return x
        x += step