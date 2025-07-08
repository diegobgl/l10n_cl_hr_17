# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'
    # _description = 'Salary Rule' # Inherited

    # Add start/end dates for rule validity
    date_start = fields.Date('Válido Desde', help="Regla activa a partir de esta fecha (inclusive).")
    date_end = fields.Date('Válido Hasta', help="Regla activa hasta esta fecha (inclusive).")

    # Override _satisfy_condition to include date checks
    def _satisfy_condition(self, payslip_dict):
        """
        Checks if the rule condition is satisfied, including date validity checks.
        :param payslip_dict: Dictionary containing payslip values (contract, employee, payslip obj etc.)
        :return: True if the rule conditions and date validity are met, False otherwise.
        """
        self.ensure_one()
        # First, check date validity
        payslip_date = payslip_dict.get('payslip', {}).get('date_to') or payslip_dict.get('date_to')
        if not payslip_date:
             # Cannot determine validity without a date, maybe default to True or log a warning?
             # Let's assume it's not satisfied if date is unknown.
             return False

        # Convert payslip_date to date object if it's string or datetime
        payslip_date_obj = fields.Date.to_date(payslip_date)

        if self.date_start and payslip_date_obj < self.date_start:
            return False # Rule hasn't started yet
        if self.date_end and payslip_date_obj > self.date_end:
            return False # Rule has ended

        # If date conditions are met, proceed with the original condition check
        return super(HrSalaryRule, self)._satisfy_condition(payslip_dict)