# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class HrMutual(models.Model): # Renamed class
    _name = 'hr.mutual'
    _description = 'Mutualidad de Seguridad' # Added clarification

    codigo = fields.Char('Código', required=True, help="Official code for the Mutualidad")
    name = fields.Char('Nombre', required=True, help="Name of the Mutualidad")

    _sql_constraints = [
        ('codigo_uniq', 'unique (codigo)', 'El Código de la Mutualidad debe ser único!'),
    ]