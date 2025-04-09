import numpy as np
import streamlit as st
import pandas as pd
import calendar

final_columns = [
    "Year",
    "Month",
    "Nights",
    "Room fee",
    "Cleaning fee",
    "Service fee",
    "Gross earning",
    "Tax collected",
    "Paid out",
    "Bookings",
    "ADR",
    "Occupancy rate",
]

def stnadard_columns(df):
    df["Room fee"] = df["Gross earning"] - df["Cleaning fee"] - df["Service fee"]
    df["Days in Month"] = df.apply(
        lambda row: pd.Period(
            year=row["Year"], month=row["Month_Num"], freq="M"
        ).days_in_month,
        axis=1,
    )
    df["ADR"] = (df["Room fee"] / df["Nights"]).round(0)
    df["Occupancy rate"] = (100 * df["Nights"] / df["Days in Month"]).round(0)
    df["Occupancy rate"] = df["Occupancy rate"].astype(str) + "%"
    df = df.sort_values(by=["Year", "Month_Num"], ascending=[False, False])
    return df[final_columns]


def airbnb(df):
    df["Date"] = pd.to_datetime(df["Date"])
    df["Month_Num"] = df["Date"].dt.month
    df["Month"] = df["Month_Num"].apply(lambda x: calendar.month_abbr[x])
    df["Year"] = df["Date"].dt.year

    payout = df[df["Type"] == "Payout"]
    reservations = df[df["Type"] == "Reservation"]
    resolutions = df[df["Type"].str.startswith("Resolution")]
    pass_through = df[df["Type"] == "Pass Through Tot"]

    payout_agg = (
        payout.groupby(["Year", "Month_Num", "Month"])
        .agg({"Paid out": "sum"})
        .reset_index()
    )

    reservations_agg = (
        reservations.groupby(["Year", "Month_Num", "Month"])
        .agg(
            {
                "Nights": "sum",
                "Amount": "sum",
                "Cleaning fee": "sum",
                "Service fee": "sum",
                "Confirmation code": "count",
            }
        )
        .rename(columns={"Amount": "Gross earning", "Confirmation code": "Bookings"})
        .reset_index()
    )

    resolutions_agg = (
        resolutions.groupby(["Year", "Month_Num", "Month"])
        .agg(
            {
                "Amount": "sum",
            }
        )
        .rename(columns={"Amount": "Resolution amount"})
        .reset_index()
    )

    pass_through_agg = (
        pass_through.groupby(["Year", "Month_Num", "Month"])
        .agg({"Amount": "sum"})
        .rename(columns={"Amount": "Tax collected"})
        .reset_index()
    )

    temp_merge = pd.merge(
        payout_agg, reservations_agg, on=["Year", "Month_Num", "Month"], how="outer"
    ).fillna(0)

    temp_merge = pd.merge(
        temp_merge, resolutions_agg, on=["Year", "Month_Num", "Month"], how="outer"
    ).fillna(0)

    monthly_data = pd.merge(
        temp_merge, pass_through_agg, on=["Year", "Month_Num", "Month"], how="outer"
    ).fillna(0)

    monthly_data["Gross earning"] = (
        monthly_data["Gross earning"]
        + monthly_data["Resolution amount"]
        + monthly_data["Service fee"]
    )

    monthly_data["Computed Paid out"] = (
        monthly_data["Gross earning"]
        + monthly_data["Tax collected"]
        - monthly_data["Service fee"]
    )

    discrepancy = monthly_data[
        ~np.isclose(monthly_data["Paid out"], monthly_data["Computed Paid out"])
    ]

    if not discrepancy.empty:
        print("WARNING: Discrepancies found in 'Paid out':")
        print(
            discrepancy[
                [
                    "Year",
                    "Month",
                    "Paid out",
                    "Computed Paid out",
                    "Gross earning",
                    "Tax collected",
                ]
            ]
        )

    final_df = stnadard_columns(monthly_data)

    return final_df


def vrbo(df):
    df["Payout date"] = pd.to_datetime(df["Payout date"])
    df["Month_Num"] = df["Payout date"].dt.month
    df["Month"] = df["Month_Num"].apply(lambda x: calendar.month_abbr[x])
    df["Year"] = df["Payout date"].dt.year

    aggregation = (
        df.groupby(["Year", "Month_Num", "Month"])
        .agg(
            {
                "Nights": "sum",
                "Payout": "sum",
                "Deductions": "sum",
                "Lodging Tax Owner Remits": "sum",
                "Tax Withheld": "sum",
                "Reservation ID": "count",
            }
        )
        .rename(
            columns={
                "Reservation ID": "Bookings",
                "Payout": "Paid out",
                "Deductions": "Service Fee",
            }
        )
        .reset_index()
    )

    aggregation["Tax collected"] = (
        aggregation["Lodging Tax Owner Remits"] + aggregation["Tax Withheld"]
    )
    aggregation["Days in Month"] = aggregation.apply(
        lambda row: pd.Period(
            year=row["Year"], month=row["Month_Num"], freq="M"
        ).days_in_month,
        axis=1,
    )

    aggregation["Cleaning fee"] = aggregation["Bookings"] * 245
    aggregation["Gross earning"] = (
        aggregation["Paid out"] - aggregation["Tax collected"]
    )

    final_df = stnadard_columns(aggregation)

    return final_df


def booking_com(df):
    for col in [
        "Price per night",
        "Room fee",
        "Cleaning fee",
        "Tax collected",
        "Service fee",
        "Paid out",
    ]:
        if col in df.columns:
            df[col] = df[col].str.replace("$", "").str.replace(",", "").astype(float)

    for col in ["Commission %", "Tax %"]:
        if col in df.columns:
            df[col] = df[col].str.replace("%", "").astype(float) / 100

    df["Arrival"] = pd.to_datetime(df["Arrival"])
    df["Departure"] = pd.to_datetime(df["Departure"])

    df["Month_Num"] = df["Arrival"].dt.month
    df["Month"] = df["Month_Num"].apply(lambda x: calendar.month_abbr[x])
    df["Year"] = df["Arrival"].dt.year

    aggregation = (
        df.groupby(["Year", "Month_Num", "Month"])
        .agg(
            {
                "Room nights": "sum",
                "Room fee": "sum",
                "Cleaning fee": "sum",
                "Tax collected": "sum",
                "Service fee": "sum",
                "Paid out": "sum",
                "Reservation number": "count",
            }
        )
        .rename(
            columns={
                "Room nights": "Nights",
                "Reservation number": "Bookings",
            }
        )
        .reset_index()
    )

    aggregation["Gross earning"] = (
        aggregation["Room fee"] + aggregation["Cleaning fee"] + aggregation["Service fee"]
    )
    print(aggregation.columns)
    print(aggregation)

    final_df = stnadard_columns(aggregation)

    return final_df


def monthly_aggregate(monthly_data):
    month_to_num = {calendar.month_abbr[i]: i for i in range(1, 13)}
    combined_df = pd.concat(monthly_data, ignore_index=True)
    
    if 'Month_Num' not in combined_df.columns:
        combined_df['Month_Num'] = combined_df['Month'].map(month_to_num)
    
    monthly_agg = combined_df.groupby(["Year", "Month_Num", "Month"]).sum().reset_index()
    
    if 'Month_Num' not in monthly_agg.columns:
        monthly_agg['Month_Num'] = monthly_agg['Month'].map(month_to_num)
    
    monthly_agg["ADR"] = (monthly_agg["Room fee"] / monthly_agg["Nights"]).round(0)
    
    monthly_agg["Days in Month"] = monthly_agg.apply(
        lambda row: pd.Period(
            year=row["Year"], month=row["Month_Num"], freq="M"
        ).days_in_month,
        axis=1,
    )
    
    monthly_agg["Occupancy rate"] = (100 * monthly_agg["Nights"] / monthly_agg["Days in Month"]).round(0)
    monthly_agg["Occupancy rate"] = monthly_agg["Occupancy rate"].astype(str) + "%"
    
    monthly_agg = monthly_agg.sort_values(by=["Year", "Month_Num"], ascending=[False, False])
    
    return monthly_agg[final_columns]



def annual_aggregate(monthly_data):
    combined_df = pd.concat(monthly_data, ignore_index=True)
    monthly_df = combined_df.groupby(["Year", "Month"]).sum().reset_index()
    annual_df = monthly_df.groupby("Year").sum().reset_index()
    annual_df["ADR"] = (annual_df["Room fee"] / annual_df["Nights"]).round(0)
    annual_df.drop(columns=["Month", "Occupancy rate"], inplace=True)
    return annual_df


uploaded_df = {}
uploaded_files = st.file_uploader("Choose a CSV file", accept_multiple_files=True)

if uploaded_files:
    for uploaded_file in uploaded_files:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)

            if "Guest" in df.columns:
                monthly_df = airbnb(df)
            elif "Traveler Last Name" in df.columns:
                monthly_df = vrbo(df)
            elif "Booker name" in df.columns:
                monthly_df = booking_com(df)
            else:
                st.error(f"Unknown CSV format in file: {uploaded_file.name}")
                continue
        else:
            st.error("Uploaded file is not a CSV: " + uploaded_file.name)
            continue

        uploaded_df[uploaded_file.name] = monthly_df

    monthly_data = [df for df in uploaded_df.values()]    
    annual_df = annual_aggregate(monthly_data)    
    st.header("Annual Aggregate")
    st.dataframe(annual_df)
    
    if len(uploaded_df) > 1:
        st.header("Monthly Aggregate")
        monthly_agg_df = monthly_aggregate(monthly_data)
        st.dataframe(monthly_agg_df)
    
    # Display individual files
    st.header("Individual Files")
    for name, df in uploaded_df.items():
        st.subheader(name)
        st.dataframe(df)

else:
    st.write("Please upload a CSV file.")
