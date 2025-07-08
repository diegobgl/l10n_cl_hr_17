# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class HrContractType(models.Model):
    _inherit = 'hr.contract.type'
    # _description = 'Tipo de Contrato' # Description is inherited

    codigo = fields.Char('Código Previred', help="Code used for Previred reporting associated with this contract type.") # Added specific help text