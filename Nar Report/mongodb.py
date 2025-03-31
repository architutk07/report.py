import streamlit as st
import pandas as pd
from pymongo import MongoClient
from datetime import datetime
import base64
import random
from sshtunnel import SSHTunnelForwarder
from collections import Counter
from utils2 import plot_piecharts

DB_NAME = "nar"  
COLLECTION_NAME = "candidate_call_reports"  

st.set_page_config(
        page_title="📞 NAR Calling Report",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="collapsed",  # Collapsed sidebar for more space
        menu_items={
            'Get Help': 'https://your-help-link.com',  # Replace with your support link
            'Report a bug': 'https://your-bug-report-link.com',  # Replace with your bug report link
            'About': """
                ## 📊 NAR Calling Report
                This dashboard provides insightful visualizations and analytics for call records.
                Developed by [patio digital](https://your-link.com).
            """
        }
    )

MONGO_URI = "mongodb://localhost:27017/"

# Function to fetch data 
def fetch_mongo_data_and_form_types(start_date, end_date):
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]

        # Convert selected dates to MongoDB format (ISODate)
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)

        # MongoDB Aggregation Pipeline
        pipeline = [
            {
                "$lookup": {
                    "from": "call-logs",
                    "localField": "callLog",
                    "foreignField": "_id",
                    "as": "callLog"
                }
            },
            {"$unwind": "$callLog"},
            {
                "$replaceRoot": { 
                    "newRoot": {
                        "$mergeObjects": [
                            "$$ROOT",
                            "$callLog",
                            "$callLog.candidate-response",
                            "$callLog.candidate-response.question"
                        ]
                    }
                }
            },
            {
                "$match": {
                    "date": {"$gte": start_date, "$lte": end_date}  # Filter by date range
                }
            },
            {
                "$project": {
                    "callLog": 0,
                    "candidate-response": 0,
                    "question": 0,
                    "_id": 0,
                    "__v": 0
                }
            },
            {
                "$addFields": {
                    "updatedDate": {
                        "$add": ["$date", 19800000]  # Convert UTC to IST (5:30 hrs)
                    }
                }
            },
            {
                "$addFields": {
                    "dateUpdate": {
                        "$dateToString": {"format": "%Y-%m-%d", "date": "$updatedDate"}
                    },
                    "time": {
                        "$dateToString": {"format": "%H:%M:%S", "date": "$updatedDate"}
                    }
                }
            }
        ]

        # Fetch data using aggregation
        data = list(collection.aggregate(pipeline))
        if not data:
            return [], pd.DataFrame()

        # Separate data based on `formType`
        separated_data = {}
        for record in data:
            form_type = record.get('formType', 'default-form')
            separated_data.setdefault(form_type, []).append(record)

        # Convert separated data into DataFrames
        df_list = [pd.DataFrame(value) for key, value in separated_data.items()]

        # Fetch distinct formType values
        form_type_df = pd.DataFrame({"Form Type": list(separated_data.keys())})  

        return df_list, form_type_df  

    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return [], pd.DataFrame()

def fetch_form_questions(form_name):
    try:    
        client = MongoClient(MONGO_URI)  # Connect to MongoDB
        db = client[DB_NAME]
        collection = db['forms']

        # Define the aggregation pipeline
        form_pipeline = [
            {
                "$match": {
                    "formName": form_name  # Filter for the specific form
                }
            },
            {
                "$unwind": {
                    "path": "$fields"
                }
            },
            {
                "$project": {
                    "question": "$fields.label"
                }
            }
        ]

        # Execute the pipeline and fetch data
        data = list(collection.aggregate(form_pipeline))

        client.close()  # Close the MongoDB connection

        # Extract only questions
        questions = [record.get("question") for record in data]

        return questions  # Returns only questions for the specified form

    except Exception as e:
        print(f"Error fetching questions: {e}")  # Print error for debugging
        return []  # Return an empty list in case of failure

def get_base64_of_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()
    
logo_left = get_base64_of_image("./Patio-logo.png")
logo_right = get_base64_of_image("./NAR logo2.png")

st.sidebar.subheader("📅 Select Date Range")

# Sidebar Date Selection
start_date = st.sidebar.date_input("Start Date", datetime.today())
end_date = st.sidebar.date_input("End Date", datetime.today())

# Convert to string format
start_date_str = start_date.strftime("%Y-%m-%d")
end_date_str = end_date.strftime("%Y-%m-%d")

data_df_list = []  # Store DataFrames from MongoDB
form_type_df = None  # Store Form Type DataFrame

if st.sidebar.button("Fetch Data"):
    # Fetch data and store in session state
    data_df_list, form_type_df = fetch_mongo_data_and_form_types(start_date_str, end_date_str)
    st.session_state["data_df_list"] = data_df_list  # Store data in session state

    # Extract unique form types
    form_types = sorted({
        df["formType"].iloc[0] if "formType" in df.columns and not df["formType"].isna().all() else "default-form"
        for df in data_df_list if not df.empty
    })

    # Store form types in session state
    st.session_state["form_types"] = form_types

# Check if data is available in session state
if "data_df_list" in st.session_state and "form_types" in st.session_state:
    data_df_list = st.session_state["data_df_list"]
    form_types = st.session_state["form_types"]

    # Sidebar dropdown for selecting a specific form type
    selected_form = st.sidebar.selectbox("Select Form Type", ["All Forms"] + form_types)
    
form_count = 0
previous_form_type = None 

for df in data_df_list:
    if df.empty:
        continue
    
    form_type = df["formType"].iloc[0] if "formType" in df.columns and not df["formType"].isna().all() else "default-form"

    if selected_form != "All Forms" and form_type != selected_form:
        continue

    if form_count == 0 or form_type != previous_form_type:
        print(form_count)
    # Use a styled div for page break
        st.markdown(
            f"""
            <div style="page-break-before: always;"></div>
            <style>
                .logo-container {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 20px;
                    margin: -50px 0px;
                }}
                .logo-container img {{
                    width: 120px;
                }}
                .page-break {{
                    page-break-before: always;
                    display: block;
                }}
            </style>
            <div class="logo-container">
                <img src="data:image/png;base64,{logo_left}">
                <img src="data:image/png;base64,{logo_right}">
            </div>
            """,
            unsafe_allow_html=True
    )
    st.markdown(
        f"""
        <div style="
            text-align: center; 
            padding: 5px; 
            background: linear-gradient(to right, #87CEEB, #4682B4); 
            border-radius: 12px; 
            border: 2px solid #1C2833;
            box-shadow: 2px 2px 10px rgba(0, 0, 0, 0.25);
        ">
            <h1 style="
                font-size: 30px; 
                font-family: 'Playfair Display', sans-serif; 
                font-weight: 800; 
                color: white; 
                text-transform: uppercase;
                letter-spacing: 1.5px;
                margin-top: -10px;
                margin-bottom: -10px;
                text-shadow: 1px 1px 4px rgba(0, 0, 0, 0.3);
            ">
                <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="#6B8E23">
                <path d="M6.62 10.79a15.91 15.91 0 0 0 6.59 6.59l2.2-2.2a1.5 1.5 0 0 1 1.49-.39c1.6.4 3.31.61 5.1.61a1.5 1.5 0 0 1 1.5 1.5V21a1.5 1.5 0 0 1-1.5 1.5c-10.49 0-19-8.51-19-19A1.5 1.5 0 0 1 3 3h3.5a1.5 1.5 0 0 1 1.5 1.5c0 1.79.21 3.5.61 5.1a1.5 1.5 0 0 1-.39 1.49l-2.2 2.2z"/>
                </svg>
                Nar Calling Report
            </h1>
            <h3 style="
                color: white; 
                font-family: 'Playfair Display', serif; 
                font-weight: 700; 
                font-size: 28px; 
                letter-spacing: 1.2px; 
                text-transform: capitalize; 
                margin-top: -20px
                margin-bottom: 3px; 
                opacity: 1; 
                text-shadow: 2px 2px 5px rgba(0, 0, 0, 0.3);
            ">
                {start_date_str} to {end_date_str}
            </h3>
        </div>
        """, 
        unsafe_allow_html=True
    )
    st.markdown(
        f"""
        <div style="
            margin: 5px auto;  /* Adds spacing around the box */
            padding: 15px; 
            background: linear-gradient(135deg, #1E3A8A, #4682B4); 
            border-radius: 12px;  
            border: 3px solid black;  /* Bold black border */
            box-shadow: 5px 5px 20px rgba(0, 0, 0, 0.3);
            text-align: center;
            color: white;
            max-width: 80%;
        ">
            <h2 style="
                font-size: 26px; 
                font-weight: 800; 
                text-transform: uppercase;
                letter-spacing: 1.2px;
                font-family: 'Arial', sans-serif;
                text-shadow: 3px 3px 6px rgba(0, 0, 0, 0.3);
            ">
                📋 Report - {form_type}
            </h2>
        </div>
        """, 
        unsafe_allow_html=True
    )

    form_count += 1
    previous_form_type = form_type 

    # Fetch form questions
    form_questions = [ item.replace(' ', '-') for item in fetch_form_questions(form_type) ]
    
    columns_to_plot = ["call-answered"] + list(form_questions)
    
    valid_chart_count = 0 
    
    skip_columns = ["monthly_income_value", "Amount of Finance Availed", "What additional Help needed from RSETI?"]
    skip_columns = [col.replace(" ", "-") for col in skip_columns]

    for i, column in enumerate(columns_to_plot):
        
        if column in skip_columns:
            continue

        if column in df.columns:
            # Filter out None, NaN, and blank values
            filtered_values = df[column].dropna()
            filtered_values = filtered_values[filtered_values.astype(str).str.strip() != ""]

            if filtered_values.empty:
                continue  # Skip this column and move to the next one

            # Get value counts from filtered data
            value_counts = filtered_values.value_counts()

            if value_counts.empty:
                continue

            total_count = value_counts.sum()  # Get total count

            # Create labels with counts
            normalized_counts = Counter()
            original_labels = {}

            for label, count in value_counts.items():
                normalized_label = label.lower().replace('-', ' ')  # Normalize case and replace '-'
                if normalized_label in normalized_counts:
                    normalized_counts[normalized_label] += count
                else:
                    normalized_counts[normalized_label] = count
                    original_labels[normalized_label] = label  # Keep one of the original styles

            # Create formatted labels
            labels_counts = [
                f"{' '.join([word.capitalize() for word in original_labels[label].replace('-', ' ').split()])} ({count})"
                for label, count in normalized_counts.items()
            ]
            # # Create Pie Chart
            fig= plot_piecharts(labels_counts,value_counts,total_count)

            # Styled title box
            if valid_chart_count % 3 == 0:
                chart_cols = st.columns(3)
                
            with chart_cols[valid_chart_count % 3]:  # Ensures correct column placement
                st.markdown(
                    f"""
                    <div style="
                        background: linear-gradient(to right, #2F4F7F, #2F4F7F);
                        padding: 8px;
                        border-radius: 8px;
                        text-align: center;
                        font-weight: bold;
                        color: white;
                        font-size: 18px;
                        text-transform: uppercase;
                        box-shadow: 2px 2px 5px rgba(0, 0, 0, 0.2);
                        margin-bottom: -10px;
                    ">
                        {column.replace("_", " ").replace("-", " ")}
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                # Display Pie Chart
                st.plotly_chart(fig, use_container_width=True,key=random.randint(1, 1000000))

            valid_chart_count += 1

            # Insert page break only if there were charts on this page
            if valid_chart_count % 3 == 0 and valid_chart_count != 0: 
                st.markdown(
                    f"""
                    <div style="page-break-before: always;"></div>
                    <style>
                        .logo-container {{
                            display: flex;
                            justify-content: space-between;
                            align-items: center;
                            padding: 20px;
                            
                        }}
                        .logo-container img {{
                            width: 120px;
                        }}
                        .page-break {{
                            page-break-before: always;
                            display: block;
                            height: 1px;
                        }}
                    </style>
                    <div class="logo-container">
                        <img src="data:image/png;base64,{logo_left}">
                        <img src="data:image/png;base64,{logo_right}">
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                