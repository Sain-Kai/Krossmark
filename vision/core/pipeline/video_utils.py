import numpy as np

def sample_keyframes(frames, k=6):
    """
    Selects evenly spaced keyframes from a 3-second burst.
    """
    if len(frames) <= k:
        return frames

    idxs = np.linspace(0, len(frames) - 1, k).astype(int)
    return [frames[i] for i in idxs]