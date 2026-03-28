from django.apps import AppConfig


class SearchConfig(AppConfig):
    name = 'search'

    def ready(self):
        from django.conf import settings
        from . import engine
        engine.muat_database(settings.CHROMA_DB_PATH)
