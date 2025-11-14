import streamlit as st
import pandas as pd


def find_question_columns(df):
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
        if col.endswith(" [Score]"):
            base_name = col[:-8]
            question_names.append(base_name)
    return question_names


def pre_process_scores(raw_df, question_list):
    processed_df = raw_df.copy()

    for question in question_list:
        score_col_name = f'{question} Score'

        # this applies a lambda operation to each cell in the target column.
        processed_df[score_col_name] = processed_df[score_col_name].apply(
            lambda x: 1 if str(x.startswith('1.00')) else 0
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
st.title("History Assessment Analyzer")

# st.write() is a "magic" command. It can display text,
# data, charts, and more. Here, we're just adding a subtitle.
st.write("Upload your CSV export to get started.")

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

    # For now, let's just show a success message and the filename
    # st.success() displays a green "success" box.
    st.success(f"Successfully uploaded: {uploaded_file.name}!")
    try:
        df = pd.read_csv(uploaded_file)

        st.session_state.df = df
        st.session_state.question_list = find_question_columns(df)
        
        st.success(f"Successfully read CSV file: {uploaded_file.name[:35]}")

        if not st.session_state.question_list:
            st.warning("File read, however, there were no columns clearly labeled: ' [Score]'.")
        else:
            # --- INTERACTIVE UI FOR CREATING GROUPS ---
            st.subheader("Create a Learning Target Group")
            
            # st.text_input creates a text box.
            # The "key" is a unique ID we can use to
            # access its value.
            target_name = st.text_input(
                label="Learning Target:",
                key="new_target_name"
            )
            
            # st.multiselect is the perfect widget for this.
            # It takes our 'question_list' as the options
            # and lets the user pick as many as they want.
            selected_questions = st.multiselect(
                label="Select questions for this learning target:",
                options=st.session_state.question_list,
                key="new_target_questions"
            )

            # An 'Add' button.
            if st.button("Add Learning Target"):
                # --- COMMON PATTERN: "FORM VALIDATION" ---
                # We check for input before processing.
                if not target_name:
                    st.warning("Please enter a name for the target.")
                elif not selected_questions:
                    st.warning("Please select at least one question.")
                else:
                    # Input is valid! Add it to our "memory".
                    new_group = {
                        "name": target_name,
                        "questions": selected_questions
                    }
                    st.session_state.target_groups.append(new_group)
                    
                    # We also manually clear the input widgets
                    # by resetting their values in session_state.
                    
                    # These names come from the keys created earlier.
                    st.session_state.new_target_name = ""  
                    st.session_state.new_target_questions = []
                    
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
        # st.expander is a great way to show a summary
        # while hiding the details until clicked.
        with st.expander(f"**{group['name']}** ({len(group['questions'])} questions)"):
            st.write("Questions in this group:")
            # We can use a bulleted list for clarity
            for q in group['questions']:
                st.markdown(f"- {q}")