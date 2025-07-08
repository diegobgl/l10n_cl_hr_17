# -*- coding: utf-8 -*-

from pytz import timezone # Keep if timezone logic is needed, but Odoo handles TZ well now
from datetime import date, datetime, time

from odoo import api, fields, models, _
# No longer need decimal_precision
from odoo.exceptions import UserError, ValidationError

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'
    # _description = 'Pay Slip' # Inherited

    # Link to the specific forecast indicators used for this payslip
    indicadores_id = fields.Many2one(
        'hr.indicadores',
        string='Indicadores Previsionales',
        readonly=True,
        # Make it required if not computing/defaulting reliably
        required=True,
        copy=False,
        states={'draft': [('readonly', False)], 'verify': [('readonly', False)]}, # Allow edit in draft/verify
        help='Indicadores previsionales utilizados para este cálculo de nómina.'
    )

    # Previred Movement Code
    movimientos_personal = fields.Selection([
        ('0', '00: Sin Movimiento en el Mes'),
        ('1', '01: Contratación a plazo indefinido'),
        ('2', '02: Retiro'),
        ('3', '03: Subsidios (Licencia Médica)'), # Corrected label
        ('4', '04: Permiso Sin Goce de Sueldo'),
        ('5', '05: Incorporación Tras Ausencia/Licencia'), # Corrected label
        ('6', '06: Accidente del Trabajo'),
        ('7', '07: Contratación a plazo fijo'),
        ('8', '08: Cambio Contrato Fijo a Indefinido'), # Corrected label
        ('11', '11: Otros Movimientos (Ausentismos)'),
        ('12', '12: Reliquidación, Premio, Bono')
        ],
        string='Código Movimiento (Previred)', # Renamed for clarity
        default="0",
        copy=False, # Usually reset for new payslip
        tracking=True,
        help="Código que indica el tipo de movimiento de personal para el reporte Previred."
    )

    # Dates for the Previred movement
    date_start_mp = fields.Date(
        'Fecha Inicio Movimiento',
        copy=False,
        tracking=True,
        help="Fecha de inicio del movimiento de personal reportado en 'Código Movimiento'."
    )
    date_end_mp = fields.Date(
        'Fecha Fin Movimiento',
        copy=False,
        tracking=True,
        help="Fecha de fin del movimiento de personal reportado en 'Código Movimiento'."
    )

    # Override create to potentially get indicadores_id from context (e.g., from payslip run)
    @api.model_create_multi # Use create_multi for batch creation
    def create(self, vals_list):
        for vals in vals_list:
            # If indicators not provided, try getting from context (set by run or payslip.employees wizard)
            if 'indicadores_id' not in vals and 'indicadores_id' in self.env.context:
                vals['indicadores_id'] = self.env.context.get('indicadores_id')
            # If movement code not provided, try getting from context (less likely needed now)
            # if 'movimientos_personal' not in vals and 'movimientos_personal' in self.env.context:
            #     vals['movimientos_personal'] = self.env.context.get('movimientos_personal')

            # Try to set default indicators based on payslip date_from if still missing
            if 'indicadores_id' not in vals or not vals['indicadores_id']:
                 date_from = vals.get('date_from')
                 if date_from:
                     pay_date = fields.Date.to_date(date_from)
                     month = str(pay_date.month)
                     year = pay_date.year
                     indicator = self.env['hr.indicadores'].search([
                         ('month', '=', month), ('year', '=', year), ('state', '=', 'done')
                     ], limit=1)
                     if indicator:
                         vals['indicadores_id'] = indicator.id
                     else: # Fallback to latest done
                         latest_done = self.env['hr.indicadores'].search([('state', '=', 'done')], order='year desc, month desc', limit=1)
                         if latest_done:
                             vals['indicadores_id'] = latest_done.id
                         # else: # Raise error if no indicators found? Or allow creation without?
                         #    raise UserError(_("No se encontraron Indicadores Previsionales válidos para el período %s/%s.") % (month, year))

        return super(HrPayslip, self).create(vals_list)

    # WARNING: This override significantly changes worked days calculation.
    # Odoo 17 uses compute methods based on attendances/leaves. Overriding this
    # older method might have unintended consequences or be ignored.
    # Consider using Odoo 17's standard mechanism or overriding the newer compute methods.
    # Keeping the logic here but marking as needing verification/potential refactor.
    # @api.model
    # def get_worked_day_lines(self, contracts, date_from, date_to):
    #     """
    #     Computes the worked days lines for the given contracts and date range.
    #     Introduces EFF100 code and adjusts WORK100 based on simple logic.
    #     """
    #     # Ensure contracts is a recordset
    #     if isinstance(contracts, int):
    #         contracts = self.env['hr.contract'].browse(contracts)
    #     if isinstance(contracts, list):
    #         contracts = self.env['hr.contract'].browse(contracts)

    #     res = super().get_worked_day_lines(contracts, date_from, date_to)
    #     new_res = []

    #     for line_vals in res:
    #         if line_vals.get('code') == 'WORK100':
    #             # Store original WORK100 details
    #             attendances = line_vals.copy()
    #             original_work_days = attendances.get('number_of_days', 0)

    #             # Calculate total leave days from other lines in the initial result *for this contract*
    #             # This assumes 'res' contains lines only for the contract being processed in this iteration
    #             # which might not be true if super returns lines for multiple contracts.
    #             # This logic needs refinement if super returns multiple contracts at once.
    #             # Let's assume super() is called per contract or needs filtering here.
    #             leave_days = sum(l.get('number_of_days', 0) for l in res if l.get('code') != 'WORK100') # Simplified sum

    #             # Calculate 'dias' based on the original logic
    #             # This logic seems specific and might need re-evaluation:
    #             # Uses 30 days as base regardless of actual month length.
    #             if original_work_days < 5:
    #                 dias = original_work_days # Takes actual worked days if less than 5
    #             else:
    #                 dias = 30 - leave_days # Uses 30 days minus leaves otherwise

    #             # Adjust the WORK100 line's days
    #             attendances['number_of_days'] = max(0, dias) # Ensure non-negative
    #             attendances['number_of_hours'] = dias * contracts.resource_calendar_id.hours_per_day # Adjust hours too?

    #             # Create the EFF100 line using original values
    #             effective = line_vals.copy() # Use the original WORK100 vals
    #             effective.update({
    #                 'name': _("Dias de trabajo efectivos (Original)"), # Clarify name
    #                 'sequence': attendances.get('sequence', 10) + 1, # Place after WORK100
    #                 'code': 'EFF100',
    #                 # Keep original number_of_days and number_of_hours
    #                 'number_of_days': original_work_days,
    #                 'number_of_hours': line_vals.get('number_of_hours', 0),
    #             })
    #             new_res.append(attendances) # Add modified WORK100
    #             new_res.append(effective)   # Add new EFF100
    #         elif line_vals.get('work_entry_type_id'): # Keep other lines (leaves, etc.)
    #             new_res.append(line_vals)

    #     # Need to handle grouping if super returns lines for multiple contracts
    #     # This simplified approach assumes processing one contract at a time or requires grouping logic.
    #     # For now, returning the modified list.
    #     return new_res

    # Instead of overriding get_worked_day_lines, consider overriding
    # _get_worked_day_lines_values or related compute methods in Odoo 17.