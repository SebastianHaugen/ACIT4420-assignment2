
Readme · MD
# Smart Fitness Session Analyzer (Assignment II)
 
**Student name:** Sebastian Skrøvseth Haugen
**Student number:** 409883
 
## What this project does
 
This is the continuation of my Assignment I fitness analyzer, but now it works off real CSV files instead of the data generator. It loads the participant profiles and the session files (both the valid one and the one that's intentionally full of bad rows), checks every row it reads, and keeps going instead of crashing when a row turns out to be broken.
 
Rows that pass validation get grouped by session id and matched up to an existing participant. Each session then goes through the same kind of analysis as Assignment I, summaries, a comparison to the participant's baseline, a classification (resting, moderate activity, high activity, recovering or insufficient data), and a short explanation for the result. At the end the program writes three report files into an output folder and prints a short summary of how many rows it accepted and rejected.

## Package and module design

## Error handling

## Assumptions and classification rules

## Project structure

## Installation and running instructions

## Output files

## Example output

## Tests

## Known limitations
