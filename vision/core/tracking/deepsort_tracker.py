from deep_sort_realtime.deepsort_tracker import DeepSort

class DeepSortTracker:
    def __init__(self):
        self.tracker = DeepSort(
            max_age=15,
            n_init=2,
            nms_max_overlap=1.0,
            max_cosine_distance=0.2,
            nn_budget=None
        )

    def reset(self):
        # Reinitialize tracker for burst mode
        self.__init__()

    def update(self, detections, frame):
        """
        detections: list of dicts with:
            {
                "bbox": (x1,y1,x2,y2),
                "conf": float
            }

        returns list of tracks with:
            id, bbox
        """

        ds_dets = []

        for d in detections:
            x1, y1, x2, y2 = d["bbox"]
            w = x2 - x1
            h = y2 - y1
            ds_dets.append(([x1, y1, w, h], d["conf"], "person"))

        tracks = self.tracker.update_tracks(ds_dets, frame=frame)

        final_tracks = []

        for t in tracks:
            if not t.is_confirmed():
                continue

            l, t_, w, h = t.to_ltrb()
            final_tracks.append({
                "id": t.track_id,
                "bbox": (int(l), int(t_), int(l + w), int(t_ + h))
            })

        return final_tracks