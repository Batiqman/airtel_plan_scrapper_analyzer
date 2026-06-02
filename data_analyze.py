import pandas as pd
import re

# Load CSV
df = pd.read_csv('airtel_plans.csv')

# --- Data Cleaning ---

def clean_price(price_str):
    if pd.isna(price_str):
        return 0
    price_str = str(price_str).replace("₹", "").replace(",", "").strip()
    try:
        return int(price_str)
    except:
        return 0

def parse_data_amount(data_str):
    if pd.isna(data_str):
        return 0
    data_str = data_str.lower().replace(" ", "")
    match = re.search(r"([\d\.]+)(gb|mb)", data_str)
    if not match:
        return 0
    amount = float(match.group(1))
    unit = match.group(2)
    if unit == "mb":
        amount /= 1024
    return amount

def parse_validity(validity_str):
    if pd.isna(validity_str):
        return 0
    validity_str = validity_str.lower()
    match = re.search(r"(\d+)", validity_str)
    if match:
        return int(match.group(1))
    return 0

def safe_divide(numerator, denominator, fallback=9999):
    try:
        if denominator == 0:
            return fallback
        return numerator / denominator
    except:
        return fallback

# --- Derived Columns ---

df['Price'] = df['Price'].apply(clean_price)
df['Data_GB'] = df['Data'].apply(parse_data_amount)
df['Validity_Days'] = df['Validity'].apply(parse_validity)
df['Is_Per_Day'] = df['Data'].str.lower().str.contains("/day")
df['Total_Data_GB'] = df.apply(
    lambda row: row['Data_GB'] * row['Validity_Days'] if row['Is_Per_Day'] else row['Data_GB'],
    axis=1
)

# Daily usage assumption: Only some portion of daily data is usable (e.g., 60%)
DAILY_USAGE_FACTOR = 0.6

def get_effective_data_score(row):
    if row['Is_Per_Day']:
        return row['Data_GB'] * row['Validity_Days'] * DAILY_USAGE_FACTOR
    else:
        return row['Total_Data_GB']

df['Effective_Data_Score'] = df.apply(get_effective_data_score, axis=1)
df['Price_per_GB'] = df.apply(lambda row: safe_divide(row['Price'], row['Total_Data_GB']), axis=1)
df['Price_per_Day'] = df.apply(lambda row: safe_divide(row['Price'], row['Validity_Days']), axis=1)

# --- Filter-based Recommendation ---

def recommend_plans(category=None, max_price=None, min_data_gb=None, min_validity_days=None, top_n=5):
    filtered = df.copy()
    if category:
        filtered = filtered[filtered['Category'].str.lower() == category.lower()]
    if max_price is not None:
        filtered = filtered[filtered['Price'] <= max_price]
    if min_data_gb is not None:
        filtered = filtered[filtered['Total_Data_GB'] >= min_data_gb]
    if min_validity_days is not None:
        filtered = filtered[filtered['Validity_Days'] >= min_validity_days]
    filtered = filtered.sort_values(by=['Price', 'Total_Data_GB'], ascending=[True, False])
    return filtered.head(top_n)

# --- Weighted/Fuzzy Recommendation ---

def compute_score(row, weights):
    return (
        weights.get('data', 0) * row['Effective_Data_Score'] -
        weights.get('price_per_gb', 0) * row['Price_per_GB'] -
        weights.get('price_per_day', 0) * row['Price_per_Day'] +
        weights.get('validity', 0) * row['Validity_Days']
    )

def recommend_weighted(category=None, max_price=None, weights=None, top_n=35):
    filtered = df.copy()
    if category:
        filtered = filtered[filtered['Category'].str.lower() == category.lower()]
    if max_price is not None:
        filtered = filtered[filtered['Price'] <= max_price]
    filtered['Score'] = filtered.apply(lambda row: compute_score(row, weights), axis=1)
    return filtered.sort_values(by='Score', ascending=False).head(top_n)

# --- Example Usage ---

print("=== Strict Filtered Plans ===")
recommended = recommend_plans(category='Data', max_price=500, min_data_gb=5, min_validity_days=7)
print(recommended[['Category', 'Plan Name', 'Price', 'Data', 'Validity', 'Total_Data_GB']])

print("\n=== Weighted Plans (User prefers data over price) ===")
user_weights_data_pref = {
    'data': 0.6,
    'validity': 0.2,
    'price_per_gb': 0.1,
    'price_per_day': 0.1
}
recommended_data_pref = recommend_weighted(category='Truly Unlimited', max_price=2500, weights=user_weights_data_pref)
print(recommended_data_pref[['Category', 'Plan Name', 'Price', 'Data', 'Validity', 'Total_Data_GB', 'Effective_Data_Score', 'Price_per_GB', 'Price_per_Day', 'Score']])

print("\n=== Weighted Plans (User prefers price over data) ===")
user_weights_price_pref = {
    'data': 0.0,
    'validity': 0.2,
    'price_per_gb': 0,
    'price_per_day': 0.7
}
recommended_price_pref = recommend_weighted(category='Truly Unlimited', max_price=2500, weights=user_weights_price_pref)
print(recommended_price_pref[['Category', 'Plan Name', 'Price', 'Data', 'Validity', 'Total_Data_GB', 'Effective_Data_Score', 'Price_per_GB', 'Price_per_Day', 'Score']])
