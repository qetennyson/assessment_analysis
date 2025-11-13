"""
Our first Streamlit app for the History Department.

This script creates a simple web page with:
1. A title.
2. An interactive file uploader.

When a file is uploaded, it will display a success message.
"""

# --- IMPORTS ---
# We import our libraries and give them common "nicknames"
# 'st' is the standard nickname for streamlit
# 'pd' is the standard nickname for pandas
import streamlit as st
import pandas as pd

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

# --- COMMON PATTERN: "THE 'CHECK FOR INPUT' BLOCK" ---
#
# This 'if' statement is the most common and important pattern
# in Streamlit.
#
# HOW IT WORKS:
# A Streamlit app re-runs this entire script from top to bottom
# every time you interact with it (like uploading a file).
#
# 1. When the page first loads, 'uploaded_file' is `None` (empty),
#    so the code inside this 'if' block is SKIPPED.
#
# 2. When you drag and drop a file, Streamlit re-runs the script.
#    This time, 'uploaded_file' is NOT `None` (it contains your file!),
#    so the code inside this 'if' block RUNS.
#
# We will use this pattern to build our whole app.
if uploaded_file is not None:

    # For now, let's just show a success message and the filename
    # st.success() displays a green "success" box.
    st.success(f"Successfully uploaded: {uploaded_file.name}!")

    # In our next step, we will put the code to *read*
    # and *process* the file here.
    st.info("Next step: We'll read this file with Pandas.")