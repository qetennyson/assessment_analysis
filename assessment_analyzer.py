"""Assessment Analyzer: Mastery Analysis Tool for Google Form Assessments.

A Streamlit application that helps educators analyze assessment data exported
from Google Forms, focusing on student mastery of custom-defined learning targets.
"""

import re
import streamlit as st
import pandas as pd

st.set_page_config(layout='wide')

# --- PII PATTERNS ---
# Allow Student Assessment ID variants; block common PII indicators.
PII_ALLOWLIST_PATTERN = re.compile(
    r"\b(student[_\s]*assess(ment)?[_\s]*id|student[_\s]*id|studentid|sid)\b",
    re.IGNORECASE,
)

PII_BLOCKLIST_PATTERNS = [
    re.compile(r"\bemail\b", re.IGNORECASE),
    re.compile(r"\b(phone|mobile|cell)\b", re.IGNORECASE),
    re.compile(r"\b(ssn|social\s+security)\b", re.IGNORECASE),
    re.compile(r"\b(address|street|st\.?|ave|road|rd\.?|apartment|apt\.?|unit)\b", re.IGNORECASE),
    re.compile(r"\b(first\s+name|last\s+name|full\s+name|student\s+name|guardian)\b", re.IGNORECASE),
    re.compile(r"\b(dob|date\s+of\s+birth|birth\s+date)\b", re.IGNORECASE),
]

# --- SIDEBAR ---
st.sidebar.title("How to Use The App")
st.sidebar.info(
    """
    **Welcome, colleagues!**

    This app is designed to analyze CSV exports from your assessments.
    For it to work, your CSV must follow two rules:

    **1. Score Columns:** The column for a question's score
       *must* end with ` [Score]`.
       *(Note the space before the bracket!)*

    **2. Correct Answers:** A correct answer in that score
       column *must* start with `1.00`.
       *(e.g., "1.00 / 1")*

    **Following these steps will provide you with a file meeting the above criteria.**
    1. Go to your assessment's Google Form results.
    2. Locate the 3-dot Menu next to "View in Sheets".
    3. Select "Download Responses (.csv)"
    4. Un-zip that file. This is the CSV you'll upload to this site.

    **Lastly**, this app is designed to be useful for right or wrong
    MC-questions which all have the same point value, e.g. 1.00 / 1, 2.00 / 2, etc.

    At present, problems that can have partial credit 
    or result in essay responses are not ideal candidates for analysis.

    Upload your file, define your learning targets, and
    click "Run Analysis" to see the results!
    """
)
st.sidebar.title("File Format Settings")
score_suffix = st.sidebar.text_input(
    label="Enter Score Suffix Label",
    value=" [Score]",
)
correct_notation = st.sidebar.text_input(
    label="Score Notation",
    value="1.00",
)

def find_question_columns(df: pd.DataFrame, suffix: str) -> list[str]:
    """Identify score columns in a DataFrame.

    Scans the DataFrame for columns ending with the specified suffix
    and returns the base question names (without the suffix).

    Args:
        df: The DataFrame loaded from the user's CSV.
        suffix: The column suffix to search for (e.g., " [Score]").

    Returns:
        Base question names that have corresponding score columns.
    """
    all_columns = df.columns
    question_names = []
    for col in all_columns:
        if col.endswith(suffix):
            base_name = col[:-len(suffix)]
            question_names.append(base_name)
    return question_names


def validate_pii(columns: list[str]) -> tuple[bool, list[str]]:
    """Detect likely PII columns while allowing student assessment IDs.

    Args:
        columns: List of column names from the uploaded CSV.

    Returns:
        A tuple of (is_valid, offending_columns). is_valid is False when any
        column matches a PII blocklist pattern (unless it matches the allowlist).
    """
    offending: list[str] = []

    for col in columns:
        normalized = re.sub(r"\s+", " ", col.strip().lower().replace("_", " "))

        # Skip allowed student assessment ID variants
        if PII_ALLOWLIST_PATTERN.search(normalized):
            continue

        for pattern in PII_BLOCKLIST_PATTERNS:
            if pattern.search(normalized):
                offending.append(col)
                break

    return len(offending) == 0, offending


def pre_process_scores(
    raw_df: pd.DataFrame,
    question_list: list[str],
    prefix: str,
    suffix: str,
) -> pd.DataFrame:
    """Convert score columns to binary (1/0) based on correctness.

    For each question's score column, convert responses to binary:
    1 if the response starts with the correct prefix, 0 otherwise.
    See README for details on why binary conversion is used.

    Args:
        raw_df: The DataFrame loaded from the user's CSV.
        question_list: List of base question names to process.
        prefix: The prefix indicating a correct answer (e.g., "1.00").
        suffix: The score column suffix (e.g., " [Score]").

    Returns:
        A copy of raw_df with score columns converted to binary values.
    """
    processed_df = raw_df.copy()

    for question in question_list:
        score_col_name = f'{question}{suffix}'

        processed_df[score_col_name] = processed_df[score_col_name].apply(
            lambda x: 1 if str(x).startswith(prefix) else 0
        )

    return processed_df 


def run_mastery_analysis(
    processed_df: pd.DataFrame,
    target_groups: list[dict],
    suffix: str,
) -> list[dict]:
    """Calculate mastery percentage for each learning target.

    For each target group, counts how many students met the correctness
    threshold and returns results with percentages. Uses vectorized pandas
    operations for efficiency. See README for algorithmic details.

    Args:
        processed_df: DataFrame with score columns converted to binary (1/0).
        target_groups: List of group dictionaries with keys: name, questions,
                      min_correct, max_correct.
        suffix: The score column suffix (e.g., " [Score]").

    Returns:
        List of result dictionaries, one per target group, containing:
        name, count (students meeting threshold), total (all students),
        and percent (formatted percentage string).
    """
    total_students = len(processed_df)
    results = []

    if total_students == 0:
        return []

    for group in target_groups:
        group_name = group["name"]
        group_questions = group["questions"]
        min_c = group["min_correct"]
        max_c = group["max_correct"]

        # Construct score column names for this group
        score_cols_to_sum = [f"{q}{suffix}" for q in group_questions]

        # Use vectorized operations: sum binary scores across selected questions
        # for each student (axis=1), then count students in the threshold range.
        student_scores = processed_df[score_cols_to_sum].sum(axis=1)
        students_in_range = ((student_scores >= min_c) & (student_scores <= max_c)).sum()

        # Calculate percentage
        percent_met = (students_in_range / total_students) * 100

        results.append({
            "name": group_name,
            "count": students_in_range,
            "total": total_students,
            "percent": f"{percent_met:.1f}%",
        })

    return results

def delete_target(index: int) -> None:
    """Remove a target group from session state.

    Args:
        index: The index of the target group to delete.
    """
    st.session_state.target_groups.pop(index)
    st.rerun()

# --- HEADER ---
st.title("Assessment Analyzer")

st.write("""Upload your CSV export to get started.\n\nIf your CSV format
        doesn't match the image, adjust the delimiters below (or chat with Quincy).""")

st.write("""**Please read the sidebar for some additional information on best use!**""")

# --- APP SETUP ---

uploaded_file = st.file_uploader(
    label="Choose a CSV file from your computer",
    type="csv"  # We can restrict the file type to only allow CSVs
)

# Initialize session state for persistent data across reruns.
# See README and preferences.md for session state patterns.
if 'target_groups' not in st.session_state:
    st.session_state.target_groups = []
if 'processed_df' not in st.session_state:
    st.session_state.processed_df = None
if 'question_list' not in st.session_state:
    st.session_state.question_list = []


# MAIN
if uploaded_file is not None:

    try:
        df = pd.read_csv(uploaded_file)

        # Block uploads containing likely PII columns before any processing.
        is_valid, offending_columns = validate_pii(list(df.columns))
        if not is_valid:
            st.error(
                "Upload blocked: possible PII detected in columns: "
                + ", ".join(offending_columns)
            )
            st.session_state.clear()
            st.stop()

        # Find the questions
        question_list = find_question_columns(df, score_suffix)

        if not question_list:
            st.warning(
                f"File read, however, there were no columns clearly labeled: {score_suffix}."
            )
            st.session_state.clear()
        else:
            # Convert score columns to binary (1/0) representation.
            processed_df = pre_process_scores(df, question_list, correct_notation, score_suffix)
            
            st.session_state.processed_df = processed_df
            st.session_state.question_list = question_list

            st.success(f"Successfully read and processed CSV file: {uploaded_file.name[:35]}")

            # Sanity check: display overall correctness percentage to help users
            # detect if the 'Correct Answer Prefix' setting is wrong.
            all_score_cols = [f"{q}{score_suffix}" for q in question_list]
            scores_only_df = processed_df[all_score_cols]
            total_ones = scores_only_df.sum().sum()
            total_cells = scores_only_df.size
            percent_correct = (total_ones / total_cells) * 100 if total_cells > 0 else 0

            if percent_correct <= 20:
                st.warning(
                    f"Sanity Check: Using a Score Notation of '{correct_notation}', "
                    f"I found that {percent_correct:.1f}% of all answers were marked correct. "
                    f"\nIf this seems wrong, check your 'Score Notation' in the sidebar."
                )

            st.subheader("Create a Learning Target Group")

            with st.form(key='target_form', clear_on_submit=True):
                # The "key" is a unique ID we can use to access its value.
                target_name = st.text_input(
                    label="Learning Target Name",
                    key="new_target_name",
                    value="Ex: Revolutions - MET TARGET or Revolutions - ALMOST MET TARGET",
                )
                
                st.write("Choose Questions")
                with st.container(height=300, border=True):
                    for question in st.session_state.question_list:
                        st.checkbox(label=question, key=f'check_{question}')

                st.write("Select Range of Correct Answers")
                st.caption("Students are counted ONLY if their score falls strictly within this range.")

                len_questions = len(st.session_state.question_list)

                correctness_range = st.slider(
                    label="Min / Max Correct Answers",
                    min_value=0,
                    max_value=len_questions,
                    value=(0, len_questions),
                    step=1,
                    key='new_target_range',
                )
                submit_button = st.form_submit_button("Add Learning Target")

            # Form validation runs only when submit button is clicked.
            if submit_button:
                selected_questions = []
                for q in st.session_state.question_list:
                    if st.session_state[f"check_{q}"]:
                        selected_questions.append(q)

                min_selected, max_selected = correctness_range

                if not target_name:
                    st.warning("Enter a good name/label for the target.")
                elif not selected_questions:
                    st.warning("Select at least one question.")
                elif max_selected > len(selected_questions):
                    st.error(
                        f"Threshold ({max_selected}) cannot be larger than the number of "
                        f"questions selected ({len(selected_questions)})."
                    )
                else:
                    # Input is valid. Store in session state.
                    new_group = {
                        "name": target_name,
                        "questions": selected_questions,
                        "min_correct": min_selected,
                        "max_correct": max_selected,
                    }
                    st.session_state.target_groups.append(new_group)
                    st.success(f"Added group: {target_name}")


    except Exception as e:
        st.error(f"An error occurred while processing the file: {e}")
        st.write("Please ensure this is a valid CSV file and try again.")

if st.session_state.target_groups:
    st.subheader("Your Defined Learning Targets")

    for i, group in enumerate(st.session_state.target_groups):
        col_exp, col_btn = st.columns([10, 1])
        with col_exp:
            with st.expander(
                f"**{group['name']}** ({len(group['questions'])} questions, "
                f"Range: {group['min_correct']}-{group['max_correct']}))"
            ):
                st.write("Questions in this group:")
                for q in group['questions']:
                    st.markdown(f"- {q}")

        with col_btn:
            st.button(
                "❌",
                key=f'del_{i}',
                on_click=delete_target,
                args=(i,),
                help="Delete this learning target.",
            )
    st.markdown("---")
    
    col1, col2 = st.columns([2, 1])

    with col1:
        if st.button("Run Mastery Analysis", type="primary", use_container_width=True):
            if st.session_state.processed_df is None:
                st.error("Please upload a file first.")
            else:
                analysis_results = run_mastery_analysis(
                    st.session_state.processed_df,
                    st.session_state.target_groups,
                    score_suffix,
                )

                st.subheader("Analysis Results")
                st.write("Students who met the threshold for each target:")

                for res in analysis_results:
                    st.metric(
                        label=res["name"],
                        value=f"{res['count']} / {res['total']} students",
                        delta=f"{res['percent']} met threshold",
                    )

    with col2:
        if st.button("Clear All Targets", use_container_width=True):
            st.session_state.target_groups = []
            st.rerun()