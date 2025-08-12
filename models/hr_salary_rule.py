# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'
    # _description = 'Salary Rule' # Inherited

    # Add start/end dates for rule validity
    date_start = fields.Date('Válido Desde', help="Regla activa a partir de esta fecha (inclusive).")
    date_end = fields.Date('Válido Hasta', help="Regla activa hasta esta fecha (inclusive).")

    # Override _satisfy_condition to include date checks
    def _satisfy_condition(self, localdict):
        """
        En Odoo, localdict['payslip'] es un recordset hr.payslip (no un dict).
        Copiamos date_from/date_to al localdict si faltan y delegamos al super.
        """
        try:
            payslip = localdict.get('payslip') if isinstance(localdict, dict) else None
            if payslip:
                if 'date_from' not in localdict and hasattr(payslip, 'date_from'):
                    localdict['date_from'] = payslip.date_from
                if 'date_to' not in localdict and hasattr(payslip, 'date_to'):
                    localdict['date_to'] = payslip.date_to
        except Exception:
            # no romper la evaluación de reglas si algo falla
            pass

        return super()._satisfy_condition(localdict)
