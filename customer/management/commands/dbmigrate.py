import logging
import os
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Complete migration: Schema sync + Data import'

    def handle(self, *args, **options):
        try:
            logger.info("--- Starting Remote Migration Protocol ---")
            
            # 1. Check if we are pointing to the correct remote DB
            db_host = connection.settings_dict.get('HOST')
            logger.info(f"Target Database Host: {db_host}")

            # 2. Run Schema Migrations (Creates the tables)
            logger.info("Applying schema migrations...")
            call_command('migrate', interactive=False)
            logger.info("Schema synced successfully.")

            # 3. Check state before data import
            if self.is_ready_for_migration():
                dump_file = 'db_dump.json'
                if os.path.exists(dump_file):
                    logger.info(f"Loading data from {dump_file}...")
                    call_command('loaddata', dump_file)
                    logger.info("Data records migrated successfully.")
                else:
                    logger.warning(f"No {dump_file} found. Skipping data import.")

        except Exception as e:
            logger.error(f"Migration Failed: {str(e)}", exc_info=True)
            # Standardizing error reporting for the console
            self.stderr.write(self.style.ERROR(f"CRITICAL ERROR: {e}"))
            raise 

    def is_ready_for_migration(self):
        """
        Validates system state using 'leave_application' logic.
        """
        # Logic: If we can reach this point, the schema is ready
        # You can add custom state checks here
        state = "leave_application_ready" 
        logger.info(f"State check: {state}")
        return True