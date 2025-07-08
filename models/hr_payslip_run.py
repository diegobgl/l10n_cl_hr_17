# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    indicadores_id = fields.Many2one(
        'hr.indicadores',
        string='Indicadores Previsionales',
        states={'draft': [('readonly', False)], 'verify': [('readonly', False)]},
        readonly=True,
        required=True,
        copy=False,
        help="Indicadores previsionales a utilizar para calcular las nóminas de este lote."
    )

    movimientos_personal = fields.Selection([
        ('0', 'Sin Movimiento en el Mes'),
        ('1', 'Contratación a plazo indefinido'),
        ('2', 'Retiro'),
        ('3', 'Subsidios (L Médicas)'),
        ('4', 'Permiso Sin Goce de Sueldos'),
        ('5', 'Incorporación en el Lugar de Trabajo'),
        ('6', 'Accidentes del Trabajo'),
        ('7', 'Contratación a plazo fijo'),
        ('8', 'Cambio Contrato plazo fijo a plazo indefinido'),
        ('11', 'Otros Movimientos (Ausentismos)'),
        ('12', 'Reliquidación, Premio, Bono')
    ], string='Movimientos Personal', default='0')

    @api.onchange('date_start')
    def _onchange_date_start_suggest_indicators(self):
        if self.date_start:
            month = str(self.date_start.month)
            year = self.date_start.year
            domain = [('month', '=', month), ('year', '=', year), ('state', '=', 'done')]
            indicator = self.env['hr.indicadores'].search(domain, limit=1)
            if indicator:
                self.indicadores_id = indicator
            else:
                latest_done = self.env['hr.indicadores'].search(
                    [('state', '=', 'done')], order='year desc, month desc', limit=1)
                self.indicadores_id = latest_done or False
