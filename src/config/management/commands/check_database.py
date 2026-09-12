"""Deployment/operator readiness check, deliberately separate from process liveness."""
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, connection
from django.db.migrations.executor import MigrationExecutor


class Command(BaseCommand):
    help = "Check PostgreSQL connectivity and pending migrations without exposing connection details."

    def handle(self, *args, **options):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            executor = MigrationExecutor(connection)
            if executor.migration_plan(executor.loader.graph.leaf_nodes()):
                raise CommandError("Database migrations are pending.")
        except DatabaseError:
            raise CommandError("Database unavailable.") from None
        self.stdout.write('{"database": "ok", "migrations": "applied"}')
