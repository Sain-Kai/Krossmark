class BurstAnalyzer:
    def __init__(self, yolo, tracker, pose, vlm, htsat, evidence):
        self.yolo = yolo
        self.tracker = tracker
        self.pose = pose
        self.vlm = vlm
        self.htsat = htsat
        self.evidence = evidence

    def analyze(self, frames, audio_3s):
        per_frame_evidence = []

        # Submit audio once
        self.htsat.submit(audio_3s)

        for frame in frames:
            dets = self.yolo.detect(frame)
            tracks = self.tracker.update(dets)

            for t in tracks:
                kp = self.pose.estimate(frame, t.bbox)
                feats = pose_features(kp)

                # dynamic wrist crops
                crops = []
                if kp:
                    crops.append(crop_around_point(frame, kp["left_wrist"]))
                    crops.append(crop_around_point(frame, kp["right_wrist"]))

                # choose best non-empty crops
                crops = [c for c in crops if c is not None]

                vlm_out = None
                if crops:
                    # pick the sharpest / largest crop or just first two
                    text = self.vlm.infer(crops[0], HAND_CROP_PROMPT)
                    parsed = parse_vlm_json(text)
                    if parsed:
                        vlm_out = parsed
                        self.evidence.update(t.id, parsed)

                per_frame_evidence.append({
                    "track_id": t.id,
                    "pose_feats": feats,
                    "vlm": vlm_out
                })

        audio_events = self.htsat.poll()
        return {
            "frames": per_frame_evidence,
            "audio": audio_events
        }