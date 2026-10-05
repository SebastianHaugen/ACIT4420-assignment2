
Readme · MD
# Smart Fitness Session Analyzer (Assignment II)
 
**Student name:** Sebastian Skrøvseth Haugen
**Student number:** 409883
 
## What this project does
 
This is the continuation of my Assignment I fitness analyzer, but now it works off real CSV files instead of the data generator. It loads the participant profiles and the session files (both the valid one and the one that's intentionally full of bad rows), checks every row it reads, and keeps going instead of crashing when a row turns out to be broken.
 
Rows that pass validation get grouped by session id and matched up to an existing participant. Each session then goes through the same kind of analysis as Assignment I, summaries, a comparison to the participant's baseline, a classification (resting, moderate activity, high activity, recovering or insufficient data) and a short explanation for the result. At the end the program writes three report files into an output folder and prints a short summary of how many rows it accepted and rejected.

## Package and module design
 
Everything lives in a package called `fitness_analyzer`. `main.py` in the root is only the entry point, it reads the command line arguments and calls into the package.
 
`exceptions.py` has the two custom exceptions, `InvalidIdentifierError` and `InvalidRecordError`. Both inherit from `ValueError` like in the assignment, and both get raised and caught for real in the loader. I also gave them a `field` attribute so the loader can log which column caused the problem and not just that the row was bad.
 
`validation.py` has the two regular expressions and the shared limits. Participant ids use `^P\d{3}$` and session ids use `^FIT-\d{4}-\d{3}$`. Normal number checks like heart rate or activity level are plain comparisons, not regex, since the assignment says not to use regex for that.
 
`models.py` has `Observation`, `Participant` and `Session` carried over from Assignment I. Composition is still the main idea, a session has a participant and a list of observations instead of being one. The baseline values are still protected behind `_reference` and a property. `Observation.from_dict` and `Participant.from_row` are class methods that build objects from already converted values, and `Observation.is_within_range` is a static method since it doesn't need any instance data.
 
`loader.py` reads the CSV files with `pathlib` and the `csv` module, using `open(..., encoding="utf-8", newline="")`. It converts values to the right types, checks row lengths and sends every bad row to the rejection log with filename, row number, field and reason.
 
`analysis.py` has `SessionAnalyzer` and the calculation functions from Assignment I, cleaned up a bit. It returns one result dictionary per session.
 
`reports.py` creates the output folder if it's missing and writes the three report files.
 
## How the loader works
 
I split the checking of each session row into two steps. First it checks the identifiers (the row length, then the session id and participant id formats, then that the participant actually exists in the profiles file). Only after that does it look at the measurements (missing values, converting to numbers, ranges, signal quality).
 
The reason for the split is that a session gets registered as soon as its identifiers are fine, even if every measurement row in it is rejected later. I first had it the other way around and the session with only bad signal quality just vanished from the reports. Now it shows up as insufficient data, which is what it should be.
 
## Error handling
 
I only catch errors where I can add something useful or recover. A missing or unreadable file (`FileNotFoundError`, `PermissionError`) is caught in the loader, turned into a message with the file path, and `main.py` carries on with the next file. A bad row raises `InvalidRecordError` or `InvalidIdentifierError` and the loader catches those two specifically, logs the row and moves on to the next one. Values that can't be converted to numbers raise `ValueError`, which gets turned into an `InvalidRecordError` with the field name. A missing baseline column in the profiles file is caught as a `KeyError` in the same way. If the csv module itself can't parse the file (`csv.Error`), the loader logs where it stopped and keeps the rows it already read.
 
There's no `except Exception` and no empty except block anywhere, so a real bug in the code still crashes normally instead of getting hidden.
 
## Assumptions and classification rules
 
A row gets rejected if a required field is missing, the row has the wrong number of columns, a value can't be converted to its type, the participant id or session id has the wrong format, the participant id isn't in the profiles file, or a measurement is impossible. The limits I used are heart rate 30 to 220 bpm, temperature 25 to 42 degrees, activity level and signal quality between 0 and 1, and timestamp and skin response not negative. The data dictionary doesn't give numbers for heart rate or temperature so those two ranges are my own choice.
 
Poor signal quality counts as a data quality problem, so any row with signal quality below 0.6 is rejected for that reason. The 0.6 is my own rule, the data dictionary only says signal quality is between 0 and 1.
 
Each rejected row only gets one reason logged, the first check it fails.
 
A session needs at least 3 usable rows before it gets classified, otherwise it is insufficient data. That way a session that lost most of its rows never gets mixed up with a real resting or active result.
 
The classification itself is the same as Assignment I. Resting means the average heart rate is close to baseline with low activity, moderate and high activity depend on how far the average heart rate and activity are from baseline, and recovering means heart rate and activity clearly drop in the second half of the session compared to the first half.
 
## Project structure
 
```
ACIT4420-assignment2/
├── .gitignore
├── README.md
├── DATA_DESCRIPTION.md
├── DATA_DICTIONARY.txt
├── main.py
├── requirements.txt
├── data/
│   ├── participants.csv
│   ├── fitness_sessions.csv
│   └── fitness_sessions_invalid.csv
├── fitness_analyzer/
│   ├── __init__.py
│   ├── exceptions.py
│   ├── validation.py
│   ├── models.py
│   ├── loader.py
│   ├── analysis.py
│   └── reports.py
├── tests/
│   ├── __init__.py
│   └── test_analysis.py
└── output/   (created when the program runs, not committed)
```
 
## Installation and running instructions
 
Nothing to install, it only uses the standard library.
 
```bash
git clone https://github.com/SebastianHaugen/ACIT4420-assignment2.git
cd ACIT4420-assignment2
python main.py --profiles data/participants.csv --sessions data/fitness_sessions.csv data/fitness_sessions_invalid.csv --output output
```
 
`--sessions` takes one or more files, so the valid and the invalid file can be run together like above. On my machine it's `python` or `py`, not `python3`, so use whichever one works for you.
 
To run the tests:
 
```bash
python -m unittest discover tests
```
 
## Output files
 
Every run creates the `output` folder if it doesn't exist and overwrites the old files, so running it twice gives the same result and nothing has to be cleaned up by hand.
 
`analysis_summary.csv` has one row per session. `analysis_report.txt` explains each result in plain text. `rejected_records.txt` lists every rejected row with the source filename, row number, field and reason.
 
## Example output
 
```
=== Completion summary ===
Participants loaded: 3
Sessions processed: 7
Accepted rows: 25
Rejected rows: 15
Reports written to: output/
```
 
Part of `analysis_summary.csv` from that run:
 
```
session_id,participant_id,classification,recovery_detected,usable_observations,rejected_observations,heart_rate_vs_reference
FIT-2026-001,P001,resting,False,6,0,0.83
FIT-2026-004,P001,recovering,True,6,0,45.17
FIT-2026-005,P002,insufficient_data,False,0,0,
```
 
## Tests
 
`tests/test_analysis.py` has 17 tests. They cover valid files, invalid rows (bad id formats, values that can't be converted, unknown participant, wrong row length), a missing file, a csv parsing error, a session where every row gets rejected, and boundary values like a heart rate or signal quality sitting exactly on the limit. They also check the classifications (resting, recovering and insufficient data).
 
## Known limitations
 
The classification thresholds are just numbers that seemed reasonable to me, not based on real fitness research, and they're the same for every participant apart from their own baseline. Skin response and temperature are validated but don't affect the classification, only heart rate and activity level do. Recovery detection is a first half versus second half comparison, so it doesn't look at how fast the drop happens. It also means a session that peaks in the middle is not flagged as recovering. For example `FIT-2026-002` rises and falls back down, but the second half average is still higher than the first half, so it is classified as moderate activity.
  
Bad rows are rejected while the files are being loaded, before they ever reach a session. That means the `rejected_observations` column in `analysis_summary.csv` is always 0, and the real rejections can only be found in `rejected_records.txt`. And if a csv file is broken badly enough that the csv module gives up, everything after that point in the file is skipped.