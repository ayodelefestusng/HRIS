from employees.models import Employee
from org.models import  JobRole

from django.db.models import Q
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()
NEW_PW = "@Ajibandele1"

def get_depth(employee):
    depth = 1
    curr = employee
    while curr.line_manager:
        depth += 1
        curr = curr.line_manager
    return depth

def get_all_downlines(employee):
    subs = list(Employee.objects.filter(line_manager=employee))
    all_subs = []
    for sub in subs:
        all_subs.append(sub)
        all_subs.extend(get_all_downlines(sub))
    return list(set(all_subs))

def elevate_user(employee):
    """Elevates the associated user to superuser and sets the password."""
    user = employee.user
    user.is_superuser = True
    user.is_staff = True
    user.set_password(NEW_PW)
    user.save()
    return True

def print_employee_report(emp):
    mgr = emp.line_manager
    grand_mgr = mgr.line_manager if mgr else None
    downlines = get_all_downlines(emp)
    depth = get_depth(emp)
    
    # Elevation logic for current, manager, and grand manager
    elevate_user(emp)
    if mgr: elevate_user(mgr)
    if grand_mgr: elevate_user(grand_mgr)
    for sub in downlines:
        elevate_user(sub)

    # Safe Role Access
    role_display = "N/A"
    first_role = emp.roles.first()
    if first_role:
        job_title = getattr(first_role, 'job_title', None)
        role_display = getattr(job_title, 'name', job_title) if job_title else first_role

    print("-" * 60)
    print(f"NAME: {emp.full_name} (SUPERUSER STATUS: ACTIVE)")
    print(f"DEPTH: {depth}")
    print(f"EMAIL: {emp.user.email}")
    print(f"ROLE: {role_display}")
    print(f"DIRECT MANAGER: {mgr.full_name if mgr else 'N/A'}")
    print(f"GRAND MANAGER: {grand_mgr.full_name if grand_mgr else 'N/A'}")
    print(f"SUBORDINATES ({len(downlines)}): {', '.join([d.full_name for d in downlines[:5]])}...")

# Locate Primary Users
user_1 = None 
user_2 = None 

for e in Employee.objects.all():
    d = get_depth(e)
    sub_count = Employee.objects.filter(line_manager=e).count()
    
    if d == 3 and sub_count >= 5 and not user_1:
        user_1 = e
    elif d == 4 and sub_count >= 5 and not user_2:
        if not user_1 or e.org_unit != user_1.org_unit:
            user_2 = e

# Generate Report and Elevate
report_set = set()
for primary in [user_1, user_2]:
    if primary:
        report_set.add(primary)
        curr = primary
        while curr.line_manager:
            report_set.add(curr.line_manager)
            curr = curr.line_manager
        report_set.update(get_all_downlines(primary))

# Transactional update to ensure database integrity
with transaction.atomic():
    for person in sorted(list(report_set), key=lambda x: get_depth(x)):
        print_employee_report(person)

print(f"\nSUCCESS: All cluster members elevated to Superuser with password: {NEW_PW}")