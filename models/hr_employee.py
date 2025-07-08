# -*- coding: utf-8 -*-

import re
import logging

from odoo import models, fields, api, _ # Added _ for translations
from odoo.exceptions import UserError, ValidationError # Added ValidationError

_logger = logging.getLogger(__name__)

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # Splitting name fields for Chilean standard
    # Odoo standard 'name' field will be computed from these
    firstname = fields.Char("Primer Nombre", tracking=True) # Required is handled by compute/inverse
    last_name = fields.Char("Apellido Paterno", tracking=True) # Required is handled by compute/inverse
    middle_name = fields.Char("Segundo Nombre", help='Segundo nombre del empleado', tracking=True)
    mothers_name = fields.Char("Apellido Materno", help='Apellido materno del empleado', tracking=True)
    formated_vat = fields.Char(
        string="RUT Formateado",
        compute="_compute_formated_vat",
        store=True,
        help="RUT chileno con puntos y guión, derivado de identification_id"
    )

    # Overriding name to be computed
    name = fields.Char(compute='_compute_name', store=True, readonly=False, required=True, tracking=True) # Added required=True back

    type_id = fields.Many2one(
        'hr.type.employee',
        string='Tipo de Trabajador (Previred)', # Renamed for clarity
        help="Clasificación del trabajador según Previred (Activo, Pensionado, etc.)",
        tracking=True
    )
    # Removed formated_vat as Odoo standard formatting might suffice, or can be added later if needed.

    # --- Compute & Inverse for Name ---
    @api.depends('firstname', 'middle_name', 'last_name', 'mothers_name')
    def _compute_name(self):
        for employee in self:
            parts = [employee.firstname, employee.middle_name, employee.last_name, employee.mothers_name]
            employee.name = " ".join(part for part in parts if part)

    # --- Onchange methods (Kept for immediate UI feedback, compute handles storage) ---
    # Note: Onchange is often redundant if compute/inverse is correctly implemented.
    # Keeping it here as per original code, but consider removal if compute is sufficient.
    @api.onchange('firstname', 'mothers_name', 'middle_name', 'last_name')
    def _onchange_parts_for_name(self):
        if self.firstname or self.last_name: # Trigger even if only one part exists initially
            parts = [self.firstname, self.middle_name, self.last_name, self.mothers_name]
            self.name = " ".join(part for part in parts if part)


    # --- RUT/Identification Validation ---
    @api.onchange('identification_id')
    def _onchange_identification_id_format(self):
        # Format RUT input: XX.XXX.XXX-X or K
        if self.identification_id and self.country_id and self.country_id.code == 'CL':
            try:
                val = self.identification_id
                # Remove dots, hyphens, spaces and keep K
                val_clean = re.sub(r'[^\dKk]', '', val).upper()
                if not val_clean:
                    self.identification_id = ''
                    return

                # Separate body and DV
                if len(val_clean) > 1:
                    body = val_clean[:-1]
                    dv = val_clean[-1]

                    # Format body with dots
                    body_int = int(body) # Will raise ValueError if not digits
                    body_formatted = "{:,}".format(body_int).replace(",", ".")

                    self.identification_id = f"{body_formatted}-{dv}"
                elif len(val_clean) == 1: # Only DV? Keep it simple for now
                     self.identification_id = val_clean
                # No else needed, handled by initial check

            except (ValueError, TypeError):
                 # Handle cases where conversion fails gracefully (e.g., non-numeric body)
                 # Optionally raise a UserError or just keep the original value
                 # For onchange, it's often better not to raise errors immediately
                 pass # Keep original value if formatting fails


    def _check_rut_chile(self, rut):
        """Validates a Chilean RUT"""
        if not rut or not isinstance(rut, str):
            return False
        rut_clean = re.sub(r'[^\dKk]', '', rut).upper()
        if len(rut_clean) < 2:
            return False

        body, dv = rut_clean[:-1], rut_clean[-1]
        try:
            body_int = int(body) # Ensure body is numeric
            reversed_digits = map(int, reversed(str(body_int)))
            factors = [2, 3, 4, 5, 6, 7] * (len(str(body_int)) // 6 + 1)
            checksum = sum(d * factors[i] for i, d in enumerate(reversed_digits))
            res = 11 - (checksum % 11)
            calculated_dv = str(res) if res < 10 else ('K' if res == 10 else '0') # Handle res == 11 -> 0
            return dv == calculated_dv
        except ValueError:
            return False # Body wasn't numeric


    @api.constrains('identification_id', 'country_id', 'company_id')
    def _check_identification_id(self):
        # Override or extend base check if needed
        # super(HrEmployee, self)._check_identification_id() # Call super if extending
        for employee in self:
            if employee.identification_id and employee.country_id and employee.country_id.code == 'CL':
                if not employee._check_rut_chile(employee.identification_id):
                     raise ValidationError(_("El RUT '%s' ingresado no es válido.") % employee.identification_id)

                # Uniqueness Check (similar to original)
                if employee.identification_id != "55.555.555-5": # Allow placeholder
                    domain = [
                        ('company_id', '=', employee.company_id.id), # Check within the same company
                        ('identification_id', '=', employee.identification_id),
                        ('id', '!=', employee.id),
                    ]
                    if self.env['hr.employee'].search_count(domain) > 0:
                        raise ValidationError(_("El RUT '%s' ya existe para otro empleado en esta compañía.") % employee.identification_id)


    # Add tracking to other important fields if needed
    gender = fields.Selection(tracking=True)
    country_id = fields.Many2one('res.country', tracking=True)
    #... other fields ...

    @staticmethod
    def rut_format(rut):
        """Aplica formato chileno: 12345678K -> 12.345.678-K"""
        rut = rut.replace(".", "").replace("-", "").upper()
        if not rut[:-1].isdigit() or not rut[-1].isalnum():
            return rut
        cuerpo = rut[:-1]
        dv = rut[-1]
        return f"{int(cuerpo):,}".replace(",", ".") + "-" + dv

    @api.depends('identification_id')
    def _compute_formated_vat(self):
        for emp in self:
            emp.formated_vat = self.rut_format(emp.identification_id or "")
