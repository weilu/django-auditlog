from math import ceil

from django.conf import settings
from django.core.management import CommandError, CommandParser
from django.core.management.base import BaseCommand

from auditlog.models import LogEntry


class Command(BaseCommand):
    help = "Migrates changes from changes_text to json changes."
    requires_migrations_checks = True

    def add_arguments(self, parser: CommandParser):
        group = parser.add_argument_group()
        group.add_argument(
            "--check",
            action="store_true",
            help="Just check the status of the migration",
            dest="check",
        )
        group.add_argument(
            "-d",
            "--database",
            default=None,
            metavar="The database engine",
            help="If provided, the script will use native db operations. "
            "Otherwise, it will use LogEntry.objects.bulk_update",
            dest="db",
            type=str,
            choices=["postgres", "mysql", "oracle"],
        )
        group.add_argument(
            "-b",
            "--batch-size",
            default=500,
            help="Split the migration into multiple batches. If 0, then no batching will be done. "
            "When passing a -d/database, the batch value will be ignored.",
            dest="batch_size",
            type=int,
        )
        group.add_argument(
            "-m",
            "--migrate-m2m",
            action="store_true",
            help="Also migrate old patched version of m2m handling",
            dest="m2m",
        )

    def handle(self, *args, **options):
        database = options["db"]
        batch_size = options["batch_size"]
        check = options["check"]
        migrate_m2m = options["m2m"]

        if (not self.check_logs()) or check:
            return

        if database:
            result = self.migrate_using_sql(database)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Updated {result} records using native database operations."
                )
            )
        else:
            result = self.migrate_using_django(batch_size, migrate_m2m)
            self.stdout.write(
                self.style.SUCCESS(f"Updated {result} records using django operations.")
            )

        self.check_logs()

    def check_logs(self):
        count = self.get_logs().count()
        if count:
            self.stdout.write(f"There are {count} records that needs migration.")
            return True

        self.stdout.write(self.style.SUCCESS("All records have been migrated."))
        if settings.AUDITLOG_USE_TEXT_CHANGES_IF_JSON_IS_NOT_PRESENT:
            var_msg = self.style.WARNING(
                "AUDITLOG_USE_TEXT_CHANGES_IF_JSON_IS_NOT_PRESENT"
            )
            self.stdout.write(f"You can now set {var_msg} to False.")

        return False

    def get_logs(self):
        return LogEntry.objects.filter(
            changes_text__isnull=False, changes__isnull=True
        ).exclude(changes_text__exact="")

    def migrate_using_django(self, batch_size, migrate_m2m):
        def _apply_django_migration(_logs) -> int:
            import json

            updated = []
            errors = []
            for log in _logs:
                try:
                    changes = json.loads(log.changes_text)
                    if migrate_m2m and len(changes) == 1:
                        field_name = list(changes.keys())[0]
                        change = changes[field_name]
                        if 'Added' in change:
                            changes = {
                                field_name: {
                                    "type": "m2m",
                                    "operation": 'add',
                                    "objects": change['Added'],
                                }
                            }
                        elif 'Removed' in change:
                            changes = {
                                field_name: {
                                    "type": "m2m",
                                    "operation": 'delete',
                                    "objects": change['Removed'],
                                }
                            }
                    log.changes = changes
                except ValueError:
                    errors.append(log.id)
                else:
                    updated.append(log)

            LogEntry.objects.bulk_update(updated, fields=["changes"])
            if errors:
                self.stderr.write(
                    self.style.ERROR(
                        f"ValueError was raised while converting the logs with these ids into json."
                        f"They where not be included in this migration batch."
                        f"\n"
                        f"{errors}"
                    )
                )
            return len(updated)

        logs = self.get_logs()

        if not batch_size:
            return _apply_django_migration(logs)

        total_updated = 0
        for _ in range(ceil(logs.count() / batch_size)):
            total_updated += _apply_django_migration(self.get_logs()[:batch_size])
        return total_updated

    def migrate_using_sql(self, database):
        from django.db import connection

        def postgres():
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE auditlog_logentry
                    SET changes="changes_text"::jsonb
                    WHERE changes_text IS NOT NULL
                        AND changes_text <> ''
                        AND changes IS NULL
                    """
                )
                return cursor.cursor.rowcount

        if database == "postgres":
            return postgres()

        raise CommandError(
            f"Migrating the records using {database} is not implemented. "
            f"Run this management command without passing a -d/--database argument."
        )
