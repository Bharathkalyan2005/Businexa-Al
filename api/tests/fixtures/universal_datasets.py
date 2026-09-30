"""
Test fixtures for Stage 1 universal profiler.

Dataset A — Business/Sales shaped:
    OrderID, Date, Product, Category, Region, Quantity, UnitPrice,
    Revenue, Discount, CustomerType, Churn

Dataset B — Clinical/Records shaped:
    PatientID, Age, Gender, BloodPressure, Cholesterol, Glucose,
    BMI, HeartRate, Smoker, HeartDisease, AdmissionDate, LengthOfStay
"""

from __future__ import annotations

import pandas as pd
import numpy as np


def make_sales_df() -> pd.DataFrame:
    """Deterministic 200-row business/sales dataset."""
    rng = np.random.default_rng(42)
    n = 200

    categories = ["Electronics", "Clothing", "Food", "Books", "Sports"]
    products = {
        "Electronics": ["Laptop", "Phone", "Tablet", "Headphones"],
        "Clothing": ["T-Shirt", "Jeans", "Jacket", "Shoes"],
        "Food": ["Coffee", "Tea", "Snacks", "Juice"],
        "Books": ["Fiction", "Non-Fiction", "Textbook", "Comics"],
        "Sports": ["Yoga Mat", "Dumbbell", "Running Shoes", "Water Bottle"],
    }
    regions = ["North", "South", "East", "West"]
    customer_types = ["Retail", "Wholesale"]
    churn_values = ["Active", "Churned"]

    cat_arr = rng.choice(categories, n)
    product_arr = [
        rng.choice(products[c]) for c in cat_arr
    ]
    region_arr = rng.choice(regions, n)
    customer_type_arr = rng.choice(customer_types, n)
    churn_arr = rng.choice(churn_values, n, p=[0.75, 0.25])

    quantity = rng.integers(1, 20, n).astype(float)
    unit_price = rng.uniform(5, 500, n).round(2)
    discount = rng.uniform(0, 0.3, n).round(3)
    revenue = (quantity * unit_price * (1 - discount)).round(2)

    # Introduce some nulls
    null_mask_discount = rng.random(n) < 0.05
    discount[null_mask_discount] = np.nan

    # Date column — weekly orders over ~4 years
    base_date = pd.Timestamp("2021-01-04")
    dates = [base_date + pd.Timedelta(days=int(i * 7 + rng.integers(0, 7))) for i in range(n)]

    order_ids = [f"ORD-{10000 + i}" for i in range(n)]

    return pd.DataFrame({
        "OrderID": order_ids,
        "Date": dates,
        "Product": product_arr,
        "Category": cat_arr,
        "Region": region_arr,
        "Quantity": quantity,
        "UnitPrice": unit_price,
        "Revenue": revenue,
        "Discount": discount,
        "CustomerType": customer_type_arr,
        "Churn": churn_arr,
    })


def make_clinical_df() -> pd.DataFrame:
    """Deterministic 300-row clinical/records dataset."""
    rng = np.random.default_rng(99)
    n = 300

    genders = ["Male", "Female"]
    bp_categories = ["Normal", "Elevated", "High Stage 1", "High Stage 2"]
    cholesterol_cats = ["Desirable", "Borderline", "High"]
    smoker_vals = ["Yes", "No"]

    age = rng.integers(25, 85, n).astype(float)
    bmi = rng.uniform(17.5, 42.0, n).round(1)
    glucose = rng.uniform(70, 200, n).round(1)
    heart_rate = rng.integers(55, 110, n).astype(float)
    length_of_stay = rng.integers(1, 21, n).astype(float)

    gender_arr = rng.choice(genders, n)
    bp_arr = rng.choice(bp_categories, n, p=[0.35, 0.25, 0.25, 0.15])
    chol_arr = rng.choice(cholesterol_cats, n, p=[0.45, 0.30, 0.25])
    smoker_arr = rng.choice(smoker_vals, n, p=[0.30, 0.70])

    # Heart disease: correlated with age, bmi, smoking
    base_prob = (
        0.05
        + (age - 25) / 60 * 0.3
        + (bmi - 17.5) / 24.5 * 0.15
        + np.where(smoker_arr == "Yes", 0.15, 0.0)
    )
    heart_disease = (rng.random(n) < base_prob).astype(int)

    # Introduce some nulls
    glucose[rng.random(n) < 0.04] = np.nan
    bmi[rng.random(n) < 0.03] = np.nan

    # Admission dates
    base_date = pd.Timestamp("2020-01-01")
    admission_dates = [
        base_date + pd.Timedelta(days=int(rng.integers(0, 365 * 4)))
        for _ in range(n)
    ]

    patient_ids = [f"PT-{50000 + i}" for i in range(n)]

    return pd.DataFrame({
        "PatientID": patient_ids,
        "Age": age,
        "Gender": gender_arr,
        "BloodPressure": bp_arr,
        "Cholesterol": chol_arr,
        "Glucose": glucose,
        "BMI": bmi,
        "HeartRate": heart_rate,
        "Smoker": smoker_arr,
        "HeartDisease": heart_disease,
        "AdmissionDate": admission_dates,
        "LengthOfStay": length_of_stay,
    })
