# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class HrSeguroComplementario(models.Model):
    _name = 'hr.seguro.complementario'
    _description = 'Aseguradora Seguro Complementario'

    codigo = fields.Char('Código (Uso Interno)', help="Código interno para la aseguradora")
    name = fields.Char('Nombre Aseguradora', required=True, help="Nombre de la aseguradora de seguro complementario")
