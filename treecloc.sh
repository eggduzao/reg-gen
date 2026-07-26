#!/bin/bash
# Create Project's tree and cloc - number of lines
# of written code per file.

set -euo pipefail

echo "✨ Creating tree... ✨"
tree -L 6 --charset utf-8 --noreport > tree.txt
LC_ALL=UTF-8 sed -i '' $'s/   /\t\t/g' tree.txt

echo "✨ Creating cloc... ✨"
find . -maxdepth 4 -type f > filelist.txt
cloc --by-file --file-encoding='UTF-8' --list-file=filelist.txt > cloc.txt
rm filelist.txt
# [-f ./_legacy/ & mv tree.txt cloc.txt ./_legacy/]

echo "✅ Everything Done Under the Sun."

