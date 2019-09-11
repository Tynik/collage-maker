import threading


class TasksList:
    def __init__(self):
        self._lists = []

    def add(self, **kwargs):
        task = threading.Thread(**kwargs, daemon=True)
        self._lists.append(task)
        return task

    def wait(self, **kwargs):
        for task in self._lists:
            task.join(**kwargs)
