# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

# TODO: Review if this override is still necessary in Odoo 17.
# The 'indicadores_id' might be correctly passed from the payslip run
# to the payslip creation context by standard Odoo mechanisms.
class HrPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    # Removed api.multi
    def compute_sheet(self):
        """
        Injects 'indicadores_id' from the active payslip run into the context
        before calling the standard compute_sheet method.
        """
        indicadores_id = False
        payslip_run_id = self.env.context.get('active_id')

        if payslip_run_id:
            payslip_run = self.env['hr.payslip.run'].browse(payslip_run_id)
            if payslip_run.exists() and payslip_run.indicadores_id:
                indicadores_id = payslip_run.indicadores_id.id

        # Add the indicator ID to the context for the super call
        # The list of employees to process is already on self.employee_ids
        context_with_indicator = self.env.context.copy()
        if indicadores_id:
             context_with_indicator['indicadores_id'] = indicadores_id

        # Call super with potentially modified context
        # The original method likely loops through self.employee_ids and creates/computes payslips
        return super(HrPayslipEmployees, self.with_context(context_with_indicator)).compute_sheet()