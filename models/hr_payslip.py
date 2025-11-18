# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    indicadores_id = fields.Many2one(
        'hr.indicadores',
        string='Indicadores Previsionales',
        required=True,
        copy=False,
        domain="[('state', '=', 'done'), ('year', '=', year_domain), ('month', '=', month_domain)]",
        default=lambda self: self._default_indicadores(),
        help='Indicadores previsionales utilizados para este cálculo de nómina.'
    )

    # Helpers para el domain dinámico en vista
    month_domain = fields.Selection(
        selection=[(str(i), str(i)) for i in range(1, 13)],
        compute='_compute_period_domain',
        store=False
    )
    year_domain = fields.Integer(compute='_compute_period_domain', store=False)

    movimientos_personal = fields.Selection([
        ('0', '00: Sin Movimiento en el Mes'),
        ('1', '01: Contratación a plazo indefinido'),
        ('2', '02: Retiro'),
        ('3', '03: Subsidios (Licencia Médica)'),
        ('4', '04: Permiso Sin Goce de Sueldo'),
        ('5', '05: Incorporación Tras Ausencia/Licencia'),
        ('6', '06: Accidente del Trabajo'),
        ('7', '07: Contratación a plazo fijo'),
        ('8', '08: Cambio Contrato Fijo a Indefinido'),
        ('11', '11: Otros Movimientos (Ausentismos)'),
        ('12', '12: Reliquidación, Premio, Bono'),
    ], string='Código Movimiento (Previred)', default='0', copy=False, tracking=True)

    date_start_mp = fields.Date('Fecha Inicio Movimiento', copy=False, tracking=True)
    date_end_mp   = fields.Date('Fecha Fin Movimiento',   copy=False, tracking=True)

    # -------- Defaults / Onchange --------
    @api.model
    def _default_indicadores(self):
        date_from = self.env.context.get('default_date_from') or self.env.context.get('date_from') or fields.Date.context_today(self)
        df = fields.Date.to_date(date_from)
        month = str(df.month)
        year = df.year
        rec = self.env['hr.indicadores'].search([('month', '=', month), ('year', '=', year), ('state', '=', 'done')], limit=1)
        if rec:
            return rec.id
        last = self.env['hr.indicadores'].search([('state', '=', 'done')], order='year desc, month desc', limit=1)
        return last.id if last else False

    @api.depends('date_from', 'date_to')
    def _compute_period_domain(self):
        for slip in self:
            df = slip.date_from or fields.Date.context_today(self)
            df = fields.Date.to_date(df)
            slip.month_domain = str(df.month)
            slip.year_domain = df.year

    @api.onchange('date_from', 'date_to')
    def _onchange_period_set_indicadores(self):
        if self.date_from:
            df = fields.Date.to_date(self.date_from)
            rec = self.env['hr.indicadores'].search([
                ('month', '=', str(df.month)),
                ('year',  '=', df.year),
                ('state', '=', 'done')
            ], limit=1)
            if rec:
                self.indicadores_id = rec.id

    @api.onchange('employee_id', 'date_from', 'date_to')
    def _onchange_employee_dates_set_contract_and_structure(self):
        for slip in self:
            if not slip.employee_id or not slip.date_from or not slip.date_to:
                continue

            contract = self.env['hr.contract'].search([
                ('employee_id', '=', slip.employee_id.id),
                ('state', 'in', ['open', 'close']),
                ('date_start', '<=', slip.date_to),
                '|', ('date_end', '=', False), ('date_end', '>=', slip.date_from),
            ], order='date_start desc', limit=1)

            if not contract:
                continue

            # asigna el contrato
            slip.contract_id = contract

            # elige estructura compatible según lo disponible
            struct = False
            if 'structure_type_id' in contract._fields and contract.structure_type_id:
                # v14+ (con tipos de estructura)
                struct = contract.structure_type_id.default_struct_id or False

            if not struct and 'struct_id' in contract._fields:
                # fallback para versiones que usan struct_id en el contrato
                struct = contract.struct_id

            if struct:
                slip.struct_id = struct

            # solo asigna structure_type_id si el campo EXISTE en hr.payslip
            if 'structure_type_id' in slip._fields and \
            'structure_type_id' in contract._fields and contract.structure_type_id:
                slip.structure_type_id = contract.structure_type_id

    def _get_salary_line_total(self, code):
        self.ensure_one()
        line = self.line_ids.filtered(lambda l: l.code == code)[:1]
        return int(round(line.total)) if line else 0# -----