import threading
import queue
import time


class VLMWorker:
    def __init__(self, vlm):
        """
        Handles asynchronous VLM inference to prevent blocking the main perception loop.
        """
        self.vlm = vlm
        # Small request queue to ensure we only process the most recent/relevant crops
        self.req_q = queue.Queue(maxsize=4)
        # Larger response queue to store results until the next pipeline poll
        self.res_q = queue.Queue(maxsize=16)

        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def _loop(self):
        """Internal worker loop running in a background thread."""
        while True:
            try:
                # Blocks until an item is available
                item = self.req_q.get()
                if item is None:
                    time.sleep(0.1)
                    continue

                # Unpack the new 4-element item (includes 'kind')
                track_id, image, prompt, kind = item

                try:
                    # Execute the heavy VLM inference
                    text = self.vlm.infer(image, prompt)
                    # Pass the 'kind' back with the result so the pipeline knows context
                    self.res_q.put((track_id, kind, text))
                except Exception as e:
                    print(f"[VLM Worker] Inference Error on ID {track_id}: {e}")

                # Mark task as done in the queue
                self.req_q.task_done()

            except Exception as e:
                print(f"[VLM Worker] Critical Loop Error: {e}")
                time.sleep(0.5)  # Prevent aggressive looping on persistent errors

    def submit(self, track_id, image, prompt, kind="hand"):
        """
        Submits a new job to the VLM.
        'kind' should be 'full' (person context) or 'hand' (weapon detection).
        """
        if not self.req_q.full():
            self.req_q.put((track_id, image, prompt, kind))
        else:
            # Optionally log if we are dropping frames to keep the system real-time
            pass

    def poll_results(self):
        """
        Returns all completed VLM results since the last poll.
        Returns: List of tuples (track_id, kind, text)
        """
        results = []
        while not self.res_q.empty():
            try:
                results.append(self.res_q.get_nowait())
            except queue.Empty:
                break
        return results