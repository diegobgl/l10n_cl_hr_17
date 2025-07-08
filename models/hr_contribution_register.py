from odoo import fields, models

class HrContributionRegister(models.Model):
    _name = 'hr.contribution.register'
    _description = 'Registro de Entidad Previsional'

    name = fields.Char(required=True)
    partner_id = fields.Many2one('res.partner', string='Entidad Asociada')
