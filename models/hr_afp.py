# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class HrAfp(models.Model):
    _name = 'hr.afp'
    _description = 'Fondos de Pension (Pension Funds)' # Updated description

    codigo = fields.Char('Código', required=True, help="Official code for the AFP") # Added help text
    name = fields.Char('Nombre', required=True, help="Name of the AFP")
    rut = fields.Char('RUT', required=True, help="Tax ID of the AFP") # Clarified RUT meaning
    rate = fields.Float('Tasa Afiliado (%)', required=True, digits='Payroll Rate', help="Employee contribution rate (%)") # Added % and clarity
    sis = fields.Float('Tasa SIS (%)', required=True, digits='Payroll Rate', help="Employer SIS contribution rate (%)") # Added % and clarity
    independiente = fields.Float('Tasa Independientes (%)', required=True, digits='Payroll Rate', help="Independent worker contribution rate (%)") # Added % and clarity

    _sql_constraints = [
        ('codigo_uniq', 'unique (codigo)', 'El Código de la AFP debe ser único!'),
    ]