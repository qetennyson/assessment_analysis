import streamlit as st
import pandas as pd

st.set_page_config(layout='wide')

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

def find_question_columns(df, suffix):
    """
    Scans a Pandas DataFrame for columns that end with "[Score]".
    It then returns a list of the *base* question names.

    For example:
    If it finds "Question 1 [Score]", it will return "Question 1".

    Args:
        df (pd.DataFrame): The DataFrame loaded from the user's CSV.

    Returns:
        list: A list of strings, where each string is a base
              question name that has a corresponding score column.
    """
    all_columns = df.columns
    question_names = []
    for col in all_columns:
        if col.endswith(suffix):
            base_name = col[:-len(suffix)]
            question_names.append(base_name)
    return question_names


def pre_process_scores(raw_df, question_list, prefix, suffix):
    processed_df = raw_df.copy()

    for question in question_list:
        score_col_name = f'{question}{suffix}'

        # this applies a lambda operation to each cell in the target column.
        processed_df[score_col_name] = processed_df[score_col_name].apply(
            lambda x: 1 if str(x).startswith(prefix) else 0
        )

    return processed_df 


def run_mastery_analysis(processed_df, target_groups):
    """
    The core analysis function.
    
    Calculates, for each group, how many students
    met the required 'N' (threshold) of correct answers.
    
    Args:
        processed_df (pd.DataFrame): The cleaned DF with 1s/0s.
        target_groups (list): Our list of group dictionaries
                              from st.session_state.
                              
    Returns:
        list: A list of result dictionaries, one for each group.
    """
    
    total_students = len(processed_df)
    results = []
    
    if total_students == 0:
        return []
    
    for group in target_groups:
        group_name = group["name"]
        group_questions = group["questions"]
        threshold = group["threshold"]
        
        # Find the [Score] column names for this group
        score_cols_to_sum = [f"{q} [Score]" for q in group_questions]
        
        # A vectorized operation .sum() axis 1 identifies the columns
        # to sum in the dataframe, and then immediately calls NumPy 
        # code to do a highly efficient sum vs. nested loops.
        # It produces a Series object (a column) of student's summed scores
        # for the range.
        student_scores = processed_df[score_cols_to_sum].sum(axis=1)
        
        # Two vector operations are used here in a chain.
        # 1. student_scores >= threshold evalutes to T/F based on 
        # our Series and the current threshold.
        # 2. It uses .sum() to convert booleans to 1/0 and sum.
        students_who_met_threshold = (student_scores >= threshold).sum()
        
        # Calculate percentage
        percent_met = (students_who_met_threshold / total_students) * 100
        
        results.append({
            "name": group_name,
            "count": students_who_met_threshold,
            "total": total_students,
            "percent": f"{percent_met:.1f}%" # Format to 1 decimal
        })
        
    return results


# --- APP LAYOUT ---
# These commands build the visual parts of your web app.

# st.title() puts a large title at the top of the page.
st.title("Assessment Analyzer")

# st.write() is a "magic" command. It can display text,
# data, charts, and more. Here, we're just adding a subtitle.
st.write("""Upload your CSV export to get started\n\nIf your CSV format
        doesn't match the image, adjust the delimiters below (or chat with Quincy)""")

# --- INTERACTIVE WIDGET ---
# Here we create our first "widget". A widget is an interactive
# element like a button, a slider, or, in this case, a file uploader.

# We tell Streamlit to create a file uploader with a label.
# When a user uploads a file, Streamlit stores it in the
# 'uploaded_file' variable.

uploaded_file = st.file_uploader(
    label="Choose a CSV file from your computer",
    type="csv"  # We can restrict the file type to only allow CSVs
)

# --- COMMON PATTERN: "INITIALIZING SESSION STATE" ---
#
# We need to create our "memory" (st.session_state)
# before the user interacts with it.
#
# This 'if' statement checks if we've already created
# 'target_groups' in our session state. If not,
# we create it as an empty list.
#
# This ensures our list exists and persists across re-runs.
if 'target_groups' not in st.session_state:
    st.session_state.target_groups = []



# MAIN
if uploaded_file is not None:

    try:
        df = pd.read_csv(uploaded_file)

        # 1. Find the questions
        question_list = find_question_columns(df, score_suffix)

        if not question_list:
            st.warning(f"File read, however, there were no columns clearly labeled: {score_suffix}.")
            st.session_state.clear()
        else:
            # --- INTERACTIVE UI FOR CREATING GROUPS ---
            
            # 2. convert '1.00' column to 1s and 0s
            processed_df = pre_process_scores(df, question_list, correct_notation, score_suffix)
            
            st.session_state.processed_df = processed_df
            st.session_state.question_list = question_list

            st.success(f"Successfully read and processed CSV file: {uploaded_file.name[:35]}")

            # We calculate the *overall* correctness to help
            # the user spot a bad 'Correct Answer Prefix'.

            all_score_cols = [f"{q} [Score]" for q in question_list]

            scores_only_df = processed_df[all_score_cols]

            # 3. Get total number of 1s (sum of all cells)
            # .sum() first sums vertically (per question)
            # .sum() a second time sums *those* totals.
            total_ones = scores_only_df.sum().sum()

            # 4. Get total number of cells (.size is rows * cols)
            total_cells = scores_only_df.size

            # 5. Calculate percentage
            percent_correct = (total_ones / total_cells) * 100 if total_cells > 0 else 0

            # 6. Display the feedback
            if percent_correct <= 20:
                st.warning(f"""Sanity Check: Using a Score Notation of '{correct_notation}', 
                        I found that {percent_correct:.1f}% of all answers were marked correct. 
                        \nIf this seems wrong, check your 'Score Notation' in the sidebar.""")

            # --- END NEW BLOCK ---

            st.subheader("Create a Learning Target Group")

            with st.form(key='target_form'):
                # st.text_input creates a text box.
                # The "key" is a unique ID we can use to
                # access its value.
                target_name = st.text_input(
                    label="Learning Target Name",
                    key="new_target_name"
                )
                
                st.write("Choose Questions")
                with st.container(height=300, border=True):
                    checkbox_states = {}
                    for question in st.session_state.question_list:
                        checkbox_states[question] = st.checkbox(label=question, key=f'check_{question}')
                
                st.write("Select Correctness Threshold")
                threshold_n = st.number_input(
                    label="Num. Correct Answers",
                    min_value=1,
                    value=1,
                    step=1,
                    key='new_target_threshold',
                )

                # An 'Add' button.
                submit_button = st.form_submit_button("Add Learning Target")

                            # --- This logic now runs *only* if the submit_button was clicked ---
            if submit_button:
                # --- COMMON PATTERN: "FORM VALIDATION" ---

                selected_questions = []
                for q in st.session_state.question_list:
                    # We check session_state directly for the key
                    if st.session_state[f"check_{q}"]:
                        selected_questions.append(q)

                if not target_name:
                    st.warning("Enter a good name/label for the target.")
                elif not selected_questions:
                    st.warning("Select at least one question.")
                # We add this validation back in!
                elif threshold_n > len(selected_questions):
                    st.error(f"Threshold ({threshold_n}) cannot be larger than the number of questions selected ({len(selected_questions)}).")
                else:
                    # Input is valid! Add it to our "memory".
                    new_group = {
                        "name": target_name,
                        "questions": selected_questions,
                        "threshold": threshold_n,
                    }
                    st.session_state.target_groups.append(new_group)
                    st.success(f"Added group: {target_name}")


    except Exception as e:
        # If anything in our 'try' block fails, this code
        # will run. 'e' is the error message.
        # st.error() displays a red error box.
        st.error(f"An error occurred while processing the file: {e}")
        st.write("Please ensure this is a valid CSV file and try again.")

if st.session_state.target_groups:
    st.subheader("Your Defined Learning Targets")
    
    for i, group in enumerate(st.session_state.target_groups):
        # Updated expander to show the threshold
        with st.expander(f"**{group['name']}** ({len(group['questions'])} questions, threshold: {group['threshold']})"):
            st.write("Questions in this group:")
            for q in group['questions']:
                st.markdown(f"- {q}")
    
    st.markdown("---") # Adds a horizontal line
    
    # --- FINAL "RUN" BUTTON ---
    # We use type="primary" to make it blue and stand out.
    col1, col2 = st.columns([2, 1]) # Make 'Run' button wider
    
    with col1:
        if st.button("Run Mastery Analysis", type="primary", use_container_width=True):
            if st.session_state.processed_df is None:
                st.error("Please upload a file first.")
            else:
                # Call our main analysis function!
                analysis_results = run_mastery_analysis(
                    st.session_state.processed_df,
                    st.session_state.target_groups
                )
                
                st.subheader("Analysis Results")
                st.write("Students who met the 'at least N' threshold for each target:")
                
                # --- COMMON PATTERN: "DISPLAYING RESULTS" ---
                # We loop through our 'results' list and display
                # each one clearly.
                for res in analysis_results:
                    st.metric(
                        label=res["name"],
                        value=f"{res['count']} / {res['total']} students",
                        delta=f"{res['percent']} met threshold"
                    )

    with col2:
        if st.button("Clear All Targets", use_container_width=True):
            st.session_state.target_groups = []
            st.rerun() # Force an immediate re-run