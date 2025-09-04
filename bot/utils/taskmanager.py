import asyncio

class TaskManager:
    def __init__(self):
        self.tasks = {}  # Dictionary: case_number -> asyncio.Task

    def schedule(self, case_number, coro):
        # Cancel old task if already scheduled
        if case_number in self.tasks:
            self.tasks[case_number].cancel()

        # Create new asyncio task
        task = asyncio.create_task(coro)
        self.tasks[case_number] = task

        # Clean up finished tasks automatically
        def cleanup(_):
            self.tasks.pop(case_number, None)

        task.add_done_callback(cleanup)

    def cancel(self, case_number):
        if case_number in self.tasks:
            self.tasks[case_number].cancel()
            del self.tasks[case_number]

    def get_task(self, case_number):
        return self.tasks.get(case_number)

    def list_tasks(self):
        return list(self.tasks.keys())

# ✅ Export singleton task manager
task_manager = TaskManager()
