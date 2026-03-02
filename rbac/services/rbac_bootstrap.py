from rbac.models import Role, Permission, RolePermission


def bootstrap_rbac():
    # 1) Define permissions
    perms = [
        # Employees
        "view_employee",
        "edit_employee",

        # Leave
        "request_leave",
        "approve_leave",
        "view_team_leave",

        # Payroll
        "view_own_payslip",
        "run_payroll",

        # Org
        "view_org",
        "manage_org",

        # Workflow
        "view_workflows",
        "act_on_workflows",

        # ATS
        "view_jobs",
        "manage_jobs",
        "manage_applications",

        # Onboarding
        "view_own_onboarding",
        "manage_onboarding",

        # RBAC
        "manage_rbac",
    ]

    perm_map = {}
    for code in perms:
        perm, _ = Permission.objects.get_or_create(code=code)
        perm_map[code] = perm

    # 2) Define roles and assign permissions
    roles = {
        "EMPLOYEE": [
            "view_employee",
            "request_leave",
            "view_own_payslip",
            "view_org",
            "view_workflows",
            "view_jobs",
            "view_own_onboarding",
        ],
        "MANAGER": [
            "view_employee",
            "edit_employee",
            "request_leave",
            "approve_leave",
            "view_team_leave",
            "view_own_payslip",
            "view_org",
            "view_workflows",
            "act_on_workflows",
            "view_jobs",
            "manage_applications",
            "view_own_onboarding",
        ],
        "HR": [
            "view_employee",
            "edit_employee",
            "request_leave",
            "approve_leave",
            "view_team_leave",
            "view_own_payslip",
            "run_payroll",
            "view_org",
            "manage_org",
            "view_workflows",
            "act_on_workflows",
            "view_jobs",
            "manage_jobs",
            "manage_applications",
            "view_own_onboarding",
            "manage_onboarding",
            "manage_rbac",
        ],
        "ADMIN": perms,  # everything
    }

    for role_name, role_perms in roles.items():
        role, _ = Role.objects.get_or_create(name=role_name)
        for code in role_perms:
            perm = perm_map[code]
            RolePermission.objects.get_or_create(role=role, permission=perm)

    return True