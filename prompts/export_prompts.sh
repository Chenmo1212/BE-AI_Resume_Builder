#!/usr/bin/env bash
# export_prompts.sh
# Concatenates all five prompt YAML files into a single clipboard-ready file.
# Usage: bash prompts/export_prompts.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT="$SCRIPT_DIR/all_prompts_export.txt"

FILES=(
  "section_highlighter.yaml"
  "skills_matcher.yaml"
  "reviewer.yaml"
  "improver.yaml"
  "summary_writer.yaml"
)

> "$OUTPUT"

for FILE in "${FILES[@]}"; do
  PATH_TO_FILE="$SCRIPT_DIR/$FILE"
  echo "================================================================" >> "$OUTPUT"
  echo "PROMPT: $FILE" >> "$OUTPUT"
  echo "================================================================" >> "$OUTPUT"
  echo "" >> "$OUTPUT"
  cat "$PATH_TO_FILE" >> "$OUTPUT"
  echo "" >> "$OUTPUT"
  echo "" >> "$OUTPUT"
done

echo "✅ Exported to: $OUTPUT"

# Copy to clipboard if pbcopy (macOS) is available
if command -v pbcopy &>/dev/null; then
  pbcopy < "$OUTPUT"
  echo "📋 Copied to clipboard — paste directly into your AI chat."
fi
