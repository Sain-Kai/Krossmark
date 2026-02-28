import threading, queue

class HTSATWorker:
    def __init__(self, model):
        self.model = model
        self.req_q = queue.Queue(maxsize=2)
        self.res_q = queue.Queue(maxsize=8)
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def submit(self, audio_3s):
        if not self.req_q.full():
            self.req_q.put(audio_3s)

    def _loop(self):
        while True:
            audio = self.req_q.get()
            out = self.model.infer(audio)
            # expected: {"metallic":0..1, "shout":0..1, "impact":0..1, "confidence":0..1}
            self.res_q.put(out)

    def poll(self):
        outs = []
        while not self.res_q.empty():
            outs.append(self.res_q.get())
        return outs