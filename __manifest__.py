# -*- coding: utf-8 -*-
{
    'name': "Chilean HR Payroll Localization (Odoo 17)",

    'summary': """
        Chilean Human Resources Payroll Rules and Reports.
        AFP, Isapre, APV, CCAF, Mutual, Previred Export, Salary Book.
    """,

    'description': """
        This module provides the necessary localization for Chilean Payroll:
        - Employee data extensions (RUT validation, names).
        - Contract specific fields (AFP, Isapre, APV, Allowances, Cargas Familiares).
        - Chilean institutions (AFP, Isapre, CCAF, Mutual, APV entities).
        - Forecast Indicators (Indicadores Previsionales) with web scraping.
        - Salary rules according to Chilean legislation (Sueldo Base, Gratificación, Impuesto Único, etc.).
        - Worked days calculation adjustments.
        - Previred CSV export wizard.
        - Libro de Remuneraciones (Salary Book) report.
        - Customized Payslip report.
        - Standard Chilean configurations (Contract Types, Holiday Types, Calendar).
    """,

    'author': "Your Name / Company", # Change this
    'website': "https://www.yourcompany.com", # Change this

    # Categories can be used to filter modules in modules listing
    'category': 'Human Resources/Payroll Localization',
    'version': '17.0.1.0.0',
    'license': 'OEEL-1', # Or other appropriate license

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'hr_work_entry_contract_enterprise',
        'hr',
        'hr_contract',
        'hr_holidays',
        'hr_payroll', # Base payroll app
        'account',
        'analytic',
        'resource',
        # Add 'hr_payroll_account' if accounting integration from payroll is needed
    ],
    # always loaded
    
    # always loaded
    'data': [
        # Security
        'security/ir.model.access.csv',
        # Views - Load base models first, then dependent models/extensions
        'views/menu_root.xml',
        'views/hr_afp_view.xml',
        'views/hr_apv_view.xml',
        'views/hr_ccaf_view.xml',
        'views/hr_isapre_view.xml',
        'views/hr_mutualidad_view.xml',
        'views/hr_seguro_complementario_view.xml',
        'views/hr_type_employee_view.xml',
        'views/hr_contract_type_view.xml',
        'views/hr_employee_view.xml',
        'views/hr_contract_view.xml',
        'views/hr_holiday_views.xml',
        'views/hr_indicadores_previsionales_view.xml',
        'views/hr_salary_rule_view.xml',
        'views/hr_payslip_view.xml',
        'views/hr_payslip_run_view.xml',
        'views/hr_contribution_register_view.xml', # Inherits hr_payroll view

        # Wizards
        # 'wizard/wizard_export_csv_previred_view.xml',
        # 'report/hr_salary_books.xml', # Contains wizard view for salary book

        # Reports
        # 'report/report_hrsalarybymonth.xml',
        # 'report/report_payslip.xml',

        # Data - Load categories/types first, then records using them
         #'data/hr_salary_rule_category.xml',
         'data/hr_type_employee.xml',
         'data/hr_contract_type.xml',
         'data/hr_holidays_status.xml',
        # 'data/account_journal.xml',
        # 'data/hr_centros_costos.xml',
         'data/resource_calendar_attendance.xml', # noupdate="1" temporal
        #'data/partner.xml', # noupdate="1"
         'data/l10n_cl_hr_afp.xml',
         'data/l10n_cl_hr_apv.xml',
         'data/l10n_cl_hr_ccaf.xml',
         'data/l10n_cl_hr_isapre.xml',
         'data/l10n_cl_hr_mutual.xml',
        # 'data/l10n_cl_hr_indicadores.xml', # noupdate="1"
        'data/l10n_cl_hr_salary_rule_category.xml',  # Primero categorías
        'data/l10n_cl_hr_structure_type.xml',        # Luego tipos de estructura
        'data/l10n_cl_hr_structure_data.xml',        # Luego estructuras (sin category_id)
        'data/l10n_cl_hr_rules_data.xml',            # Luego reglas (ya tienen struct_id)

        # Menus - Load last
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml', # Add demo data if needed
    ],
    'external_dependencies': {
        'python': ['requests', 'beautifulsoup4','pypdf', 'bs4'],
    },
    'installable': True,
    'application': True, # Set to True if it's a main application
    'auto_install': False,
}