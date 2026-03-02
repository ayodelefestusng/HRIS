import pandas as pd
import numpy as np
import json
import logging 
logger = logging.getLogger(__name__)

# --- 1. Global Constants (AMENDED) ---
EMPLOYEE_ID_COL = 'employeeID._id' 
FINANCIAL_COMPONENTS = {
    'gross': 'Gross Salary', 'net': 'Net Salary', 'charge': 'Charge', 
    'amount': 'Amount', 'Basic': 'Basic Pay', 'Transport': 'Transport Allowance', 
    'Housing': 'Housing Allowance', 'NHF': 'NHF Deduction', 'NHIS': 'NHIS Deduction', 
    'NSITF': 'NSITF Deduction', 'tax': 'Total Tax', 'pension': 'Employee Pension', 
    'employerPension': 'Employer Pension', 'deduction': 'Other Deductions', 
    'OtherAllowance': 'Other Allowance', 
    'meta.annualGross': 'Annual Gross (Meta)', 'meta.sumBasicHousingTransport': 'B/H/T Sum (Meta)', 
    'meta.earnedIncome': 'Earned Income (Meta)', 'meta.earnedIncomeAfterRelief': 'Earned Income A/R (Meta)', 
    'meta.sumRelief': 'Sum Relief (Meta)'
}
NON_FINANCIAL_COMPONENTS = {
    # 'fullname': 'Full Name', # Removed 'fullname'
    'employeeID.firstName': 'First Name', # Added
    'employeeID.lastName': 'Last Name',   # Added
    'employeeID.phone': 'Phone Number',
    'employeeID.accountNumber': 'Account Number', 
    'employeeID.accountName': 'Account Name',
    'employeeID.pencomID': 'Pencom ID', 
    'employeeID.jobRole.name': 'Job Role',
    'employeeID.annualSalary': 'Annual Salary (Profile)' 
}
ALL_COMPONENTS = list(FINANCIAL_COMPONENTS.keys()) + list(NON_FINANCIAL_COMPONENTS.keys())

LLM_SUMMARY_KEY_MAPPING = {
    "Number_of_Payslips": "Total Selections",
    "Gross": "Total Gross Salary",
    "Net": "Total Net Salary",
    "NHIS": "Total NHIS",
    "Tax": "Total Tax",
    "Pension": "Employee Pension",
    "Employer_Pension": "Employer Pension",
    "NHF": "Total NHF",
    "NSITF": "Total NSITF",
}

# --- 2. Utility Function (User's provided definition) ---
def safe_to_string(raw_val, default="N/A"):
    """
    Safely converts a raw value (which might be a string, None, a list, or a Series) 
    into a clean, stripped string. Prevents the "'list' object has no attribute 'strip'" error.
    """
    # 1. Handle None/NaN values
    if pd.isna(raw_val) or raw_val is None:
        return default
    
    # 2. CRITICAL FIX: Handle list-like objects (the source of your intermittent error)
    if isinstance(raw_val, (list, pd.Series, np.ndarray)) and not isinstance(raw_val, (str, bytes)):
        try:
            # Try to extract the first non-null, non-empty element
            non_empty_item = next((item for item in raw_val if item not in (None, '', np.nan)), None)
            if non_empty_item is not None:
                # Recursively call safe_to_string on the extracted item
                return safe_to_string(non_empty_item, default)
            else:
                return default
        except:
            return default

    # 3. Standard conversion and cleaning
    try:
        s = str(raw_val).strip()
        # Clean up Pandas/Numpy artifacts
        if s.lower() in ('nan', 'none', ''):
            return default
        return s
    except Exception:
        return default


# --- 3. Name Lookup Helper (AMENDED) ---
def get_employee_name(df, emp_id):
    """
    Safely retrieves the combined firstName and lastName for a given employee ID 
    from a DataFrame indexed by ID.
    """
    FIRST_NAME_COL = 'employeeID.firstName'
    LAST_NAME_COL = 'employeeID.lastName'
    
    try:
        if FIRST_NAME_COL in df.columns and LAST_NAME_COL in df.columns:
            
            # Use .loc to look up the row by ID
            row = df.loc[emp_id]
            
            # Safely get and clean the name parts
            first_name = safe_to_string(row.get(FIRST_NAME_COL), default="").strip()
            last_name = safe_to_string(row.get(LAST_NAME_COL), default="").strip()
            
            full_name = f"{first_name} {last_name}".strip()
            return full_name if full_name else f"Unknown Employee {emp_id}"
            
    except KeyError:
        # ID not found in this specific DataFrame
        pass
    except Exception as e:
        logger.error(f"Error during name lookup for ID {emp_id}: {e}")

    return f"Unknown Employee {emp_id}"


# --- 4. Core Payroll Functions (AMENDED FOR NAME LOOKUPS) ---

def compute_payroll_metrics(df):
    """
    Calculates summary totals for key payroll components from the input DataFrame.
    (No change needed here, as it doesn't use name fields)
    """
    return {
        "Number_of_Payslips": int(len(df)),
        "Number_of_Employees": int(df[EMPLOYEE_ID_COL].nunique()) if EMPLOYEE_ID_COL in df.columns else 0,
        "Basic": float(df["Basic"].sum()) if "Basic" in df.columns else 0.0,
        "NHF": float(df["NHF"].sum()) if "NHF" in df.columns else 0.0,
        "NHIS": float(df["NHIS"].sum()) if "NHIS" in df.columns else 0.0,
        "NSITF": float(df["NSITF"].sum()) if "NSITF" in df.columns else 0.0, # Included NSITF
        "Gross": float(df["gross"].sum()) if "gross" in df.columns else 0.0,
        "Tax": float(df["tax"].sum()) if "tax" in df.columns else 0.0,
        "Pension": float(df["pension"].sum()) if "pension" in df.columns else 0.0,
        "Employer_Pension": float(df["employerPension"].sum()) if "employerPension" in df.columns else 0.0,
        "Net": float(df["net"].sum()) if "net" in df.columns else 0.0,
    }




def calculate_variance(old_metrics, new_metrics):
    """
    Calculates the percentage change between old and new metrics.
    (No change needed here)
    """
    variance = {}
    # Ensures both dictionaries are aligned by iterating over the old keys
    for key in old_metrics.keys():
        old_val = old_metrics[key]
        new_val = new_metrics.get(key, 0) 
        
        if old_val == 0:
            variance[key] = None if new_val == 0 else 100.0
        else:
            variance[key] = float(round(((new_val - old_val) / old_val) * 100, 2))
    return variance


def get_detailed_employee_changes(df_old, df_new, continuing_ids):
    """
    Compares all financial and non-financial fields for continuing employees.
    AMENDED to construct the fullname from firstName and lastName.
    """
    # 1. Prepare DataFrames: Set Index and Select Columns
    df_old_indexed = df_old.set_index(EMPLOYEE_ID_COL, drop=False).copy()
    df_new_indexed = df_new.set_index(EMPLOYEE_ID_COL, drop=False).copy()

    
    # 2. Identify continuing employees and merge their data (unmodified)
    df_old_cont = df_old_indexed.loc[continuing_ids, [c for c in ALL_COMPONENTS if c in df_old_indexed.columns]]
    df_new_cont = df_new_indexed.loc[continuing_ids, [c for c in ALL_COMPONENTS if c in df_new_indexed.columns]]

    df_merged_cont = pd.merge(
        df_old_cont, df_new_cont, left_index=True, right_index=True, suffixes=('_old', '_new'), how='outer'
    )
    
    detailed_changes_list = []

    for emp_id, row in df_merged_cont.iterrows():
        employee_changes = []
        has_change = False

        # 3. Check FINANCIAL changes (No change needed)
        for key, name in FINANCIAL_COMPONENTS.items():
            
            old_val_raw = row.get(f'{key}_old', 0)
            new_val_raw = row.get(f'{key}_new', 0)
            
            old_val = pd.to_numeric(old_val_raw, errors='coerce')
            new_val = pd.to_numeric(new_val_raw, errors='coerce')

            old_val = 0.0 if pd.isna(old_val) else float(old_val)
            new_val = 0.0 if pd.isna(new_val) else float(new_val)
            
            variance = new_val - old_val
            
            if abs(variance) > 0.01: 
                has_change = True
                employee_changes.append({
                    "item": name,
                    "impact": f"₦{variance:,.2f}",
                    "is_positive": variance > 0
                })
        
        # 4. Check NON-FINANCIAL changes (Uses updated NON_FINANCIAL_COMPONENTS keys)
        for key, name in NON_FINANCIAL_COMPONENTS.items():
            
            raw_old_val = row.get(f'{key}_old', '')
            raw_new_val = row.get(f'{key}_new', '')
            
            old_val = safe_to_string(raw_old_val)
            new_val = safe_to_string(raw_new_val)

            if old_val != new_val:
                has_change = True
                employee_changes.append({
                    "item": name,
                    "old_value": old_val,
                    "new_value": new_val
                })

        
        if has_change:
            # AMENDMENT: Construct fullname from firstName and lastName fields in the merged row
            first_name = safe_to_string(row.get('employeeID.firstName_new', row.get('employeeID.firstName_old', '')), default="").strip()
            last_name = safe_to_string(row.get('employeeID.lastName_new', row.get('employeeID.lastName_old', '')), default="").strip()
            
            # Combine the parts
            fullname = f"{first_name} {last_name}".strip() or f"Employee {emp_id}"
            
            detailed_changes_list.append({
                "name": fullname,
                "id": emp_id,
                "changes": employee_changes
            })

    return detailed_changes_list


def calculate_gross_pay_reconciliation(df_old, df_new, old_metrics, new_metrics):
    """
    Calculates New Hires, Departures, Pay Changes, and Suspicious Anomalies for Gross Pay.
    AMENDED to include actual employee names via the new helper function.
    """
    # AMENDMENT: Updated required_cols
    required_cols = ['gross', 'employeeID.firstName', 'employeeID.lastName', EMPLOYEE_ID_COL]
    
    # 1. Prepare DataFrames for reconciliation and name lookup
    df_old_temp = df_old.set_index(EMPLOYEE_ID_COL, drop=False)[[c for c in required_cols if c in df_old.columns]]
    df_new_temp = df_new.set_index(EMPLOYEE_ID_COL, drop=False)[[c for c in required_cols if c in df_new.columns]]
    
    df_merged = pd.merge(
        df_old_temp[['gross']], df_new_temp[['gross']], 
        left_index=True, right_index=True, 
        suffixes=('_old', '_new'), how='outer'
    ).fillna(0.0)
    
    old_ids = set(df_old_temp.index)
    new_ids = set(df_new_temp.index)

    new_employees = list(new_ids - old_ids)
    departed_employees = list(old_ids - new_ids)
    
    continuing_ids = list(old_ids & new_ids) 
    
    # --- Reconciliation Calculations (impacts) ---
    impact_new_hires = df_merged.loc[new_employees, 'gross_new'].sum()
    impact_departed = df_merged.loc[departed_employees, 'gross_old'].sum()
    
    df_continuing = df_merged.loc[continuing_ids].copy()
    df_continuing['GrossPay_Variance'] = df_continuing['gross_new'] - df_continuing['gross_old']
    df_pay_changes = df_continuing[abs(df_continuing['GrossPay_Variance']) > 0.01].copy()
    impact_pay_changes = df_pay_changes['GrossPay_Variance'].sum()
    
    new_gross_total = new_metrics.get('Gross', 0.0)
    old_gross_total = old_metrics.get('Gross', 0.0)

    total_calculated_variance = new_gross_total - old_gross_total
    total_impact_categorized = impact_new_hires - impact_departed + impact_pay_changes
    suspicious_anomaly_impact = total_calculated_variance - total_impact_categorized
    
    ANOMALY_THRESHOLD = 0.10 
    df_continuing['GrossPay_PChange'] = np.where(df_continuing['gross_old'] != 0, 
                                                 df_continuing['GrossPay_Variance'] / df_continuing['gross_old'], 
                                                 0)
    df_anomalies = df_continuing[abs(df_continuing['GrossPay_PChange']) >= ANOMALY_THRESHOLD].copy()
    
    # --- AMENDMENT: Retrieve actual names for Anomalies (Uses new get_employee_name) ---
    anomalies_list = []
    for idx, row in df_anomalies.iterrows():
        # Prefer new DF for name, fall back to old DF, then default
        emp_name = get_employee_name(df_new_temp, idx)
        if 'Unknown' in emp_name:
            emp_name = get_employee_name(df_old_temp, idx)

        anomalies_list.append({
             "name": emp_name, 
             "id": idx, 
             "variance": f"₦{row['GrossPay_Variance']:,.2f}", 
             "notes": f"Gross Pay change of {row['GrossPay_PChange']:.2%}"
        })

    reconciliation = {
        "NewHires": {"count": len(new_employees), "impact": f"₦{impact_new_hires:,.2f}"},
        "Departures": {"count": len(departed_employees), "impact": f"₦{impact_departed:,.2f}"},
        "PayChanges": {"count": len(df_pay_changes), "impact": f"₦{impact_pay_changes:,.2f}"},
        "SuspiciousAnomalies": {"count": len(df_anomalies), "impact": f"₦{suspicious_anomaly_impact:,.2f}"},
        "TotalVariance": f"₦{total_calculated_variance:,.2f}"
    }

    # --- AMENDMENT: Retrieve actual names for New/Departed Employees (Uses new get_employee_name) ---
    insights = {
        "NewEmployees": [
            {"name": get_employee_name(df_new_temp, emp_id), "id": emp_id, "impact": f"₦{df_merged.loc[emp_id, 'gross_new']:,.2f}"} 
            for emp_id in new_employees
        ],
        "DepartedEmployees": [
            {"name": get_employee_name(df_old_temp, emp_id), "id": emp_id, "impact": f"₦{-df_merged.loc[emp_id, 'gross_old']:,.2f}"} # Impact is negative
            for emp_id in departed_employees
        ]
    }
    
    return reconciliation, anomalies_list, insights


def get_headcount_changes(old_df, new_df):
    """
    Identifies new, departed, and continuing employees using set difference on IDs.
    AMENDED to construct fullname from firstName and lastName.
    """
    FIRST_NAME_COL = 'employeeID.firstName'
    LAST_NAME_COL = 'employeeID.lastName'

    # 1. Get unique IDs as sets
    old_ids = set(old_df[EMPLOYEE_ID_COL].dropna().astype(str))
    new_ids = set(new_df[EMPLOYEE_ID_COL].dropna().astype(str))

    # 2. Calculate set differences
    new_employee_ids = list(new_ids - old_ids)
    departed_employee_ids = list(old_ids - new_ids)
    continuing_employee_ids = list(old_ids.intersection(new_ids))

    # Index DFs for faster name/gross lookup
    old_df_indexed = old_df.set_index(EMPLOYEE_ID_COL)
    new_df_indexed = new_df.set_index(EMPLOYEE_ID_COL)

    # 3. Format New Employees (from the NEW payroll)
    new_employees = []
    if new_employee_ids:
        new_df_subset = new_df_indexed.loc[new_employee_ids]
        for emp_id, row in new_df_subset.iterrows():
            # AMENDMENT: Construct name
            first_name = safe_to_string(row.get(FIRST_NAME_COL, ''))
            last_name = safe_to_string(row.get(LAST_NAME_COL, ''))
            full_name = f"{first_name} {last_name}".strip() or 'Unknown'
            
            new_employees.append({
                "name": full_name,
                "id": emp_id,
                "impact": f"₦{row.get('gross', 0.0):,.2f}"
            })

    # 4. Format Departed Employees (from the OLD payroll)
    departed_employees = []
    if departed_employee_ids:
        old_df_subset = old_df_indexed.loc[departed_employee_ids]
        for emp_id, row in old_df_subset.iterrows():
            # AMENDMENT: Construct name
            first_name = safe_to_string(row.get(FIRST_NAME_COL, ''))
            last_name = safe_to_string(row.get(LAST_NAME_COL, ''))
            full_name = f"{first_name} {last_name}".strip() or 'Unknown'

            # Departure impact is negative Gross
            departed_employees.append({
                "name": full_name,
                "id": emp_id,
                "impact": f"₦{-row.get('gross', 0.0):,.2f}" 
            })
            
    return {
        "NewEmployees": new_employees,
        "DepartedEmployees": departed_employees,
        "ContinuingEmployeeIDs": continuing_employee_ids
    }


# --- 5. Supporting Functions (No significant logic change) ---
# ... (payroll_comparison, create_llm_summary, get_payslips_from_json, systemprompt remain as they were in the previous complete block)
# The logic in get_payslips_from_json handles the new name columns for cleaning automatically.