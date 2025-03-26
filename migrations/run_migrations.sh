#!/bin/bash

# Display script execution
set -x

# Change to the migrations directory
cd /app/migrations

# Run the migration script
python3 apply_migrations.py

# Return the exit code
exit $? 