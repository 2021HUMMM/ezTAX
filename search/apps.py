from django.apps import AppConfig


class SearchConfig(AppConfig):
    name = 'search'

    def ready(self):
        import os
        if os.getenv("QDRANT_URL"):
            from . import engine
            engine.muat_database()
