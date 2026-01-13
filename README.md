# Assessment Analyzer

A Streamlit-based web application for educators to analyze assessment data exported from Google Forms, providing insights into student mastery of custom-defined learning targets.

## Purpose

Teachers often need to quickly determine whether their students have mastered specific concepts or skills as measured by multiple-choice assessments. The Assessment Analyzer automates this process by:

1. **Ingesting CSV data** from Google Form assessment responses
2. **Grouping questions** into custom "learning targets" (e.g., "Causes of WWI", "Treaty of Versailles")
3. **Calculating mastery** — what percentage of students met a proficiency threshold per target
4. **Providing per-question analysis** — individual question success rates for item analysis

This approach allows teachers to move beyond overall score reporting and instead analyze **skill-specific mastery**, enabling data-driven instruction adjustments.

## Data Flow & Architecture

### Input: CSV Structure

The app expects a CSV exported directly from Google Forms responses (via "Download responses (.csv)"). Key requirements:

**Score Columns:**
- Must end with ` [Score]` (configurable, with leading space)
- Contain the raw score response (e.g., "1.00 / 1" for correct, "0.00 / 1" for incorrect)
- One per question

**Example CSV snippet:**
```
Timestamp,Email,Name,Question 1 [Score],Question 2 [Score],Question 3 [Score]
2024-01-10 10:00:00,student1@example.com,Student One,1.00 / 1,0.00 / 1,1.00 / 1
2024-01-10 10:01:00,student2@example.com,Student Two,1.00 / 1,1.00 / 1,0.00 / 1
```

**Constraints:**
- One row per student (no aggregation in source)
- Questions can have any point value (1.00, 2.00, etc.) — the app treats any response starting with `1.00` as correct, anything else as incorrect
- Non-score columns (timestamp, email, name) are preserved but not used in analysis
- **Future:** Student Assessment ID columns supported for optional tracking without exposing PII; PII-containing columns will be automatically blocked

### Processing: Binary Conversion

Upon upload, the app:
1. Reads CSV via `pd.read_csv()` into `raw_df`
2. Identifies all score columns using `find_question_columns()`
3. Converts score values to binary (1/0) in `pre_process_scores()`:
   - Responses starting with `1.00` → `1`
   - All others → `0`
4. Stores processed DataFrame in `st.session_state` for reuse across page reruns

This binary conversion simplifies downstream analysis and is why the exact point value doesn't matter.

### Analysis: Mastery Calculation

Teachers define learning targets by:
- **Naming** the target (e.g., "Identify Causes")
- **Selecting questions** that measure that target
- **Setting a threshold** (N) — minimum number of correct answers required

The `run_mastery_analysis()` function:
1. Sums binary scores across selected questions for each student (vectorized pandas `.sum(axis=1)`)
2. Counts how many students met the threshold
3. Calculates percentage: (students_met / total_students) × 100
4. Returns results as structured list of dictionaries

**Result Structure:**
```python
[
    {
        "name": "Learning Target Name",
        "count": 25,           # Students who met threshold
        "total": 30,           # Total students
        "percent": "83.3%"     # Percentage as formatted string
    },
    ...
]
```

### Display: Session State & Reruns

Streamlit reruns the entire script on every widget interaction. To prevent data loss:
- `raw_df` and `processed_df` stored in `st.session_state`
- Target group definitions stored in `st.session_state.target_groups`
- Results cached in session state after analysis runs
- Session state persists within a single browser session (cleared on refresh or new session)

## Design Decisions

### Why Single-File Architecture?

At current scope (~400 lines), a single file keeps the entire workflow visible and reduces import overhead. The app will modularize when it exceeds ~500 lines (expected after adding PII detection and visualization features).

### Why PEP 257 Docstrings?

Clear, concise docstrings aid readability without over-documenting. Complex algorithmic details (e.g., vectorized operations) reference this README rather than bloating docstrings.

### Why Vectorized Operations Over Loops?

Pandas vectorized operations (`.sum()`, boolean masking) are:
- **Dramatically faster** on large datasets (hundreds of students)
- **More readable** than nested loops for data manipulation
- **Standard practice** in data analysis workflows

See inline comments in `run_mastery_analysis()` for specific examples.

### Why Binary Conversion?

Converting all scores to binary (correct/incorrect) enables:
- Threshold-based mastery (e.g., "3 out of 5 correct" on a target)
- Comparison across different point values (e.g., 1.00/1 vs. 2.00/2 questions)
- Simple aggregation without weighting complexity

### Why Session State Instead of Database?

For current scope (single educator, small datasets, no persistence requirement), session state is sufficient. If persistence across sessions becomes necessary, a lightweight SQLite backend can be added without restructuring the analysis logic.

## Future Features (Architectural Readiness)

The app is architected to support three major feature additions. See `preferences.md` for implementation patterns.

### 1. Student Assessment ID Tracking

Teachers can optionally include a "Student Assessment ID" column (any unique identifier) to correlate results with their own systems **without storing PII**. Results will include lists of IDs for students who met/did not meet each target.

**Why:** Enables the teacher to follow up with specific students while keeping the app data anonymous.

### 2. PII Detection & Prevention

An automatic validator will block CSVs containing columns with names matching patterns like `email`, `name`, `phone`, `ssn`. Teachers upload only the score and ID columns they need.

**Why:** Prevents accidental exposure of sensitive student information.

### 3. Data Visualization & Exports

Current results display as plain tables/text. Future versions will add:
- Horizontal bar charts for mastery percentages
- Heatmaps for multiple targets
- Per-question difficulty rankings (item analysis)
- Downloadable CSV exports with full detail

**Why:** Teachers often work with visual dashboards and need artifacts to share with colleagues or keep in records.

## Running the App

```bash
streamlit run assessment_analyzer.py
```

The app will open at `http://localhost:8501` in your default browser.

For development with auto-reload:
```bash
streamlit run assessment_analyzer.py --logger.level=debug
```

## Testing

Use the sample CSV files in `sample_files/`:
- `example_sheet.csv` — Full dataset with multiple questions
- `sheet_points_only.csv` — Version with point variations

**Manual checklist before committing:**
- [ ] App runs without errors
- [ ] CSV upload accepts valid files and rejects invalid ones with clear error messages
- [ ] Learning target creation validates (prevents empty groups)
- [ ] Analysis produces correct counts (spot-check with sample data)
- [ ] Session state persists across interactions within one session

## Dependencies

- **streamlit** — Web UI framework
- **pandas** — Data manipulation and analysis

Both are minimal, stable libraries suitable for educational tools.

## Development Standards

See `preferences.md` for:
- Docstring format (PEP 257)
- Comment conventions
- Type hint requirements
- Code review checklist
- Architectural patterns for future features

## Notes

- This app assumes all questions have equal weight. If you need partial credit or essay scoring, pre-process your CSV offline.
- Performance is tested on datasets up to ~500 students. Larger datasets may require optimization (see roadmap).
- The app is designed for right/wrong MC questions. Questions with multiple correct answers are not currently supported.
