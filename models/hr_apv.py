# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class HrApv(models.Model):
    _name = 'hr.apv'
    _description = 'Institución Autorizada APV - APVC' # Simplified description

    codigo = fields.Char('Código', required=True, help="Official code for the APV institution")
    name = fields.Char('Nombre', required=True, help="Name of the APV institution")

    _sql_constraints = [
        ('codigo_uniq', 'unique (codigo)', 'El Código de la Institución APV debe ser único!'),
    ]