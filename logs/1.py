
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
    'fullname': 'Full Name', 'employeeID.phone': 'Phone Number',
    'employeeID.accountNumber': 'Account Number', 'employeeID.accountName': 'Account Name',
    'employeeID.pencomID': 'Pencom ID', 'employeeID.jobRole.name': 'Job Role',
    'employeeID.annualSalary': 'Annual Salary (Profile)' 
}

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

ALL_COMPONENTS = list(FINANCIAL_COMPONENTS.keys()) + list(NON_FINANCIAL_COMPONENTS.keys())
