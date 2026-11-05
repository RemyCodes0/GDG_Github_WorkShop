from django.apps import AppConfig
from django.utils.module_loading import autodiscover_modules


class JobsConfig(AppConfig):
    name = "jobs"
    verbose_name = "Background jobs"

    def ready(self):
        # Import every installed app's tasks.py so its @task functions are registered
        # before a worker looks them up by name.
        autodiscover_modules("tasks")
