import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np
import openai
import warnings

# Ignore warnings
warnings.filterwarnings("ignore")

# Set page config
st.set_page_config(page_title="BEM&T CPK", page_icon="📊", layout="wide")
st.title("📊 BEM&T CPK")

# ✅ Initialize session state for chat messages
if "messages" not in st.session_state:
    st.session_state.messages = []

# ✅ Fix Sidebar and Prevent Minimization
st.markdown(
    """
    <style>
        /* Hide the hamburger menu (≡) */
        [data-testid="stSidebarNavCollapse"] {
            display: none !important;
        }

        /* Keep sidebar expanded */
        section[data-testid="stSidebar"] {
            width: 300px !important;
            min-width: 300px !important;
        }
        
        /* Style the chat container */
        .scrollable-container {
            height: 400px;  
            overflow-y: auto;
            border: 1px solid #ddd;
            padding: 10px;
            border-radius: 10px;
            background-color: #f9f9f9;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# File uploader
fl = st.file_uploader("📂 Upload a CSV or Excel file", type=["csv", "xlsx"])
df = None

if fl is not None:
    try:
        if fl.name.endswith(".csv"):
            df = pd.read_csv(fl)
        else:
            df = pd.read_excel(fl)

        st.session_state["df"] = df  # Store file in session state
        st.success("File uploaded successfully!")

    except Exception as e:
        st.error(f"Error reading file: {e}")

# Create layout with two columns (Graph on Left, Chat on Right)
col1, col2 = st.columns([2, 1])

if df is not None:
    with col1:
        # Sidebar for graph selection
        st.sidebar.header("Customize Your Graph")

        # ---- Graph Type Selection (Using Buttons) ----
        st.sidebar.markdown("### Select Graph Type:")
        graph_type = st.sidebar.radio("", ["Bar", "Line", "Scatter", "Pie"], horizontal=True)

        # ---- X-axis Selection (Dropdown) ----
        st.sidebar.markdown("### Select X-axis:")
        x_axis = st.sidebar.selectbox("Choose X-axis:", df.columns)

        # ---- Y-axis Selection (Dropdown) ----
        st.sidebar.markdown("### Select Y-axis:")
        y_axis = st.sidebar.multiselect("Choose Y-axis:", df.columns)

        # ---- Filtering Section (Multi-Select) ----
        st.sidebar.markdown("### Filter by Columns (Optional)")
        selected_filters = st.sidebar.multiselect("Select Columns to Filter:", df.columns)

        # Dictionary to store filter conditions
        filter_conditions = {}

        for column in selected_filters:
            unique_values = df[column].unique()
            selected_values = st.sidebar.multiselect(f"Filter {column}:", unique_values)
            if selected_values:
                filter_conditions[column] = selected_values

        # Apply filters dynamically
        filtered_df = df.copy()
        for column, values in filter_conditions.items():
            filtered_df = filtered_df[filtered_df[column].isin(values)]

        # Ensure X-axis is sorted in ascending order
        filtered_df = filtered_df.sort_values(by=x_axis, ascending=True)

        # Visualization
        st.markdown("### 📊 Data Visualization")

        if graph_type == "Bar":
            fig = px.bar(filtered_df, x=x_axis, y=y_axis, title="Bar Chart")

        elif graph_type == "Line":
            fig = px.line(filtered_df, x=x_axis, y=y_axis, title="Line Chart")

        elif graph_type == "Scatter":
            fig = px.scatter(filtered_df, x=x_axis, y=y_axis, title="Scatter Plot")

        elif graph_type == "Pie":
            fig = px.pie(filtered_df, names=x_axis, values=y_axis[0] if y_axis else None, title="Pie Chart")

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # ---- CHAT ASSISTANT ----
        st.markdown("## 🤖 AI Chat Assistant")

        # Create a scrollable chat history container
        chat_container = st.container()
        with chat_container:
            st.markdown(
                """
                <div style="height: 400px; overflow-y: auto; border: 1px solid #ddd; padding: 10px; border-radius: 10px; background-color: #f9f9f9;">
                """,
                unsafe_allow_html=True
            )

            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            st.markdown("</div>", unsafe_allow_html=True)

        # ---- Chat Input ----
        user_input = st.chat_input("Ask me about the data or graph...")
        if user_input:
            st.session_state.messages.append({"role": "user", "content": user_input})

            with chat_container:
                with st.chat_message("user"):
                    st.markdown(user_input)

            # ---- AI Response Handling ----
            prompt_lower = user_input.lower()
            full_response = ""

            # Answering "total count for BSK and STS"
            if "total count" in prompt_lower:
                plant_names = ["BSK", "STS"]  # Add more if needed
                matched_plants = [p for p in plant_names if p.lower() in prompt_lower]

                if matched_plants and "Plant" in df.columns and "|" in df.columns:
                    total_count = df[df["Plant"].isin(matched_plants)]["|"].sum()
                    full_response = f"The total count for {', '.join(matched_plants)} is **{total_count}**."
                else:
                    full_response = "Error: Could not find the specified plants or required columns in the dataset."

            # Handling "highest count" queries
            elif "highest count" in prompt_lower or "most frequent" in prompt_lower:
                if "ch_id" in prompt_lower:
                    ch_id_counts = df["CH_ID"].value_counts()
                    most_frequent_ch_id = ch_id_counts.idxmax()
                    highest_count = ch_id_counts.max()
                    full_response = f"The CH_ID with the highest count is **{most_frequent_ch_id}**, appearing **{highest_count}** times."
                else:
                    full_response = "It looks like you're asking about a count, but I couldn't find the correct column. Please specify CH_ID or another column."

            # Handling "highest value" queries
            elif "highest" in prompt_lower and "value" in prompt_lower:
                column_name = None
                for col in df.columns:
                    if col.lower() in prompt_lower:
                        column_name = col
                        break
                
                if column_name:
                    max_value = df[column_name].max()
                    max_rows = df[df[column_name] == max_value]
                    full_response = f"The highest value in **{column_name}** is **{max_value}**.\nDetails: {max_rows.to_dict(orient='records')}"
                else:
                    full_response = "Error: No matching column found in the dataset. Please specify a valid column name."

            else:
                full_response = "I'm still learning to process more types of queries. Please refine your question."

            # Display AI response inside chat container
            with chat_container:
                with st.chat_message("assistant"):
                    st.markdown(full_response)

            st.session_state.messages.append({"role": "assistant", "content": full_response})

else:
    st.warning("Please upload a file to proceed.")