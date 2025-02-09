#!/bin/bash
#
# Script Name: mp32faba.sh
# Description: This script creates a Faba+ compatible folder starting from .mp3 files and a custom tag id.
#              The newly created folder can be directly copied to the Faba+ storage and accessed using a character with the provided ID.
# Usage:       ./mp32faba.sh <folder> <id> [start]
#
# Author:      60ne https://github.com/60ne/
# Date:        2025-02-01
#
# This script is provided "as is" without warranty of any kind.
#

# Validate input
if [[ $# -lt 2 || $# -gt 3 ]]; then
    echo "Usage: $0 <folder> <id> [start]"
    echo "  options:"
    echo "    <folder>     Folder whith .mp3 files to convert .faba"
    echo "    <id>         Four digits id of the tag (folder) to be used"
    echo "    [start]      Number to start numbering .faba (default: 0 [00.faba])"
    echo ""
    echo "Example: $0 ./mp3 0195"
    echo ""
    exit 1
fi

FOLDER="$1"
ID="$2"

# Ensure ID is a 4-digit number
if [[ ! "$ID" =~ ^[0-9]{4}$ ]]; then
    echo "Error: ID must be a 4-digit number"
    exit 1
fi

# Check if eyeD3 is installed
if ! command -v eyeD3 &> /dev/null; then
    echo "Error: eyeD3 not found"
    exit 1
fi

# Create new subfolder
NEW_FOLDER="$FOLDER/K$ID"
mkdir -p "$NEW_FOLDER"

# Copy all mp3 files to the new folder
cp "$FOLDER"/*.mp3 "$NEW_FOLDER/"

# Initialize track list file
#TRACK_LIST_FILE="$NEW_FOLDER/track_list.txt"
#> "$TRACK_LIST_FILE"

# Process copied files
if [[ -z "$3" || "$3" -le 0 ]]; then
    count=1
else
    count=$(("$3" + 1))
fi

IFS=$'\n'
for file in $(find "$NEW_FOLDER" -maxdepth 1 -type f -name "*.mp3" | sort); do
    # Remove ID3 tags
    eyeD3 --remove-all "$file" >/dev/null 2>&1
    
    # Generate title string
    TRACK_NUM=$(printf "%02d" "$count")
    TITLE="K${ID}CP${TRACK_NUM}"
    
    # Set new title with UTF-16 encoding
    eyeD3 --encoding utf16 --title "$TITLE" "$file" >/dev/null 2>&1
    
    # Generate new filename
    NEW_FILENAME="$(printf "%02d" $((count-1))).faba"
    
    # Save original filename in track list
    #echo "$NEW_FILENAME - $(basename "$file")" | tee -a "$TRACK_LIST_FILE"
    echo "$NEW_FILENAME - $(basename "$file")"
    
    # Rename file to sequential numbering
    mv "$file" "$NEW_FOLDER/$NEW_FILENAME"
    
    ((count++))
done
unset IFS

# Create info file
TOTAL_TRACKS=$((count-1))
CHARACTER_DIR="02190530${ID}00"
INFO_JSON="{\"totalTracks\":$TOTAL_TRACKS,\"characterDir\":\"$CHARACTER_DIR\"}"
echo "$INFO_JSON" > "$NEW_FOLDER/info"

echo "Processing complete"
