#!/bin/bash

# This script creates symbolic links for HTML files instead of copies
# This helps nginx properly recognize the content types

echo "Creating SPA-friendly HTML symlinks..."

# Get all HTML files in the current directory
HTML_FILES=$(find . -maxdepth 1 -type f -name "*.html")

# Remove existing symlinks first to prevent issues
find . -maxdepth 1 -type l -delete

# Create symbolic links without .html extension
for file in $HTML_FILES; do
    base_name=$(basename "$file" .html)
    echo "Creating symlink $file -> $base_name"
    
    # Symbolically link the .html file
    ln -sf "$file" "$base_name"
done

echo "Done! Created HTML symlinks for clean URLs." 