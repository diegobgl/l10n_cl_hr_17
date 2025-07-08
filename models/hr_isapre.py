# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class HrIsapre(models.Model):
    _name = 'hr.isapre'
    _description = 'Institución de Salud Previsional (Isapre)' # Expanded description

    codigo = fields.Char('Código', required=True, help="Official code for the Isapre")
    name = fields.Char('Nombre', required=True, help="Name of the Isapre")
    rut = fields.Char('RUT', required=True, help="Tax ID of the Isapre")
    cotizacion_uf = fields.Float(string="Cotización UF") 

    _sql_constraints = [
        ('codigo_uniq', 'unique (codigo)', 'El Código de la Isapre debe ser único!'),
        ('rut_uniq', 'unique (rut)', 'El RUT de la Isapre debe ser único!'),
    ]