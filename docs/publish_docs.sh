#!/bin/bash

# Exit on error
set -e

# Move into the Sphinx HTML build directory
cd build/html

# Create a .nojekyll file to disable GitHub Pages' Jekyll processing
touch .nojekyll

# Initialize Git repo if not already initialized
if [ ! -d .git ]; then
  git init
fi

# Check if gh-pages branch already exists
if git show-ref --verify --quiet refs/heads/gh-pages; then
  git checkout gh-pages
else
  git checkout --orphan gh-pages
fi

# Add and commit all files
git add .
git commit -m "Publish new docs"

# Set remote if not already set
if ! git remote | grep -q origin; then
  git remote add origin https://github.com/<your-username>/<your-repo>.git
fi

# Force push to gh-pages branch
git push origin gh-pages --force

# Go back to project root
cd ../../../

echo "Documentation published to gh-pages branch!"
