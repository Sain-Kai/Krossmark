import math

def group_tracks(tracks, dist_thresh=80):
    groups = []
    used = set()

    for i, t1 in enumerate(tracks):
        if i in used:
            continue
        group = [t1]
        used.add(i)

        cx1 = (t1.bbox[0] + t1.bbox[2]) / 2
        cy1 = (t1.bbox[1] + t1.bbox[3]) / 2

        for j, t2 in enumerate(tracks):
            if j in used:
                continue
            cx2 = (t2.bbox[0] + t2.bbox[2]) / 2
            cy2 = (t2.bbox[1] + t2.bbox[3]) / 2
            d = math.hypot(cx2 - cx1, cy2 - cy1)
            if d < dist_thresh:
                group.append(t2)
                used.add(j)

        groups.append(group)

    return groups