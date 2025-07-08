# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class HrCcaf(models.Model):
    _name = 'hr.ccaf'
    _description = 'Caja de Compensación de Asignación Familiar (CCAF)' # Expanded description

    codigo = fields.Char('Código', required=True, help="Official code for the CCAF")
    name = fields.Char('Nombre', required=True, help="Name of the CCAF")

    _sql_constraints = [
        ('codigo_uniq', 'unique (codigo)', 'El Código de la CCAF debe ser único!'),
    ]