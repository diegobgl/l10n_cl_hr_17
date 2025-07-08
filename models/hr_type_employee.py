# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class HrTypeEmployee(models.Model):
    _name = 'hr.type.employee'
    _description = 'Tipo de Trabajador (Previred)' # Clarified description

    id_type = fields.Char('Código Previred', required=True, help="Código numérico según tabla de Previred (0: Activo, 1: Pens. Cotiza, ...)")
    name = fields.Char('Descripción', required=True, help="Descripción del tipo de trabajador")

    _sql_constraints = [
        ('id_type_uniq', 'unique (id_type)', 'El Código Previred del Tipo de Trabajador debe ser único!'),
    ]