# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
# No longer need decimal_precision

class HrContract(models.Model):
    _inherit = 'hr.contract'
    # _description = 'Employee Contract' # Inherited

    # Chilean Specific Fields
    complete_name = fields.Char(
        string="Nombre completo",
        compute="_compute_complete_name",
        store=True,
    )
    afp_id = fields.Many2one('hr.afp', string='AFP', tracking=True)
    anticipo_sueldo = fields.Float(
        'Anticipo de Sueldo Contable',
        digits='Payroll',
        help="Anticipo De Sueldo Realizado Contablemente (Accounting Salary Advance)",
        tracking=True
    )
    carga_familiar = fields.Integer(
        'Cargas Familiares Simples',
        help="Número de cargas familiares simples para cálculo de asignación familiar.",
        tracking=True
    )
    carga_familiar_maternal = fields.Integer(
        'Cargas Maternales',
        help="Número de cargas familiares maternales para cálculo de asignación familiar.",
        tracking=True
    )
    carga_familiar_invalida = fields.Integer(
        'Cargas Inválidas',
        help="Número de cargas familiares inválidas para cálculo de asignación familiar.",
        tracking=True
    )
    colacion = fields.Float('Asig. Colación', digits='Payroll', help="Allowance for meals", tracking=True)
    isapre_id = fields.Many2one('hr.isapre', string='Institución de Salud', tracking=True) # Renamed label for clarity
    isapre_cotizacion_uf = fields.Float(
        'Cotización Pactada Salud (UF/CLP)',
        digits='Payroll Rate', # Using Payroll Rate for potentially high precision like UF
        help="Cotización de salud pactada con la Isapre, en UF o Pesos según 'Tipo Moneda Salud'.",
        tracking=True
    )
    isapre_fun = fields.Char(
        'Número FUN Isapre',
        help="Indicar N° de Formulario Único de Notificación (FUN) del contrato de salud con la Isapre.",
        tracking=True
    )
    isapre_cuenta_propia = fields.Boolean(
        'Cotización Salud Pagada por Empleado Directamente',
        help="Marcar si el empleado paga la cotización de Isapre directamente (no descontar de la nómina).",
        tracking=True
    )
    movilizacion = fields.Float('Asig. Movilización', digits='Payroll', help="Allowance for transportation", tracking=True)
    mutual_seguridad = fields.Boolean('Afiliado a Mutual de Seguridad', default=True, tracking=True)
    otro_no_imp = fields.Float('Otros Haberes No Imponibles', digits='Payroll', help="Other non-taxable earnings", tracking=True)
    otros_imp = fields.Float('Otros Haberes Imponibles', digits='Payroll', help="Other taxable earnings", tracking=True)
    pension = fields.Boolean('Pensionado', help="Indicar si el empleado es pensionado.", tracking=True)
    sin_afp = fields.Boolean('No Cotiza AFP', help="Marcar si el empleado no debe cotizar en AFP (ej. extranjero con convenio).", tracking=True)
    sin_afp_sis = fields.Boolean('No Calcular SIS Empleador', help="Marcar si no corresponde calcular el aporte SIS del empleador (ej. pensionado que cotiza).", tracking=True)
    seguro_complementario_id = fields.Many2one('hr.seguro.complementario', string='Seguro Complementario', tracking=True)
    seguro_complementario = fields.Float(
        'Cotización Seguro Comp. (UF/CLP)',
        digits='Payroll Rate',
        help="Cotización del seguro complementario, en UF o Pesos según 'Tipo Moneda Seguro Comp.'.",
        tracking=True
    )
    viatico_santiago = fields.Float('Asig. Viático', digits='Payroll', help="Allowance for travel expenses", tracking=True)
    # Related fields - check if still needed or if base module provides similar functionality
    # complete_name = fields.Char(related='employee_id.firstname') # Consider using employee_id.name
    last_name = fields.Char(related='employee_id.last_name') # Consider using employee_id.name

    gratificacion_legal = fields.Boolean('Calcular Gratificación Manualmente', help="Marcar si la gratificación se ingresará manualmente en la nómina en lugar de calcularla automáticamente.", tracking=True)
    isapre_moneda = fields.Selection(
        [('uf', 'UF'), ('clp', 'Pesos')],
        string='Tipo Moneda Salud',
        default="uf",
        tracking=True,
        help="Moneda en la que está expresada la 'Cotización Pactada Salud'."
    )
    apv_id = fields.Many2one('hr.apv', string='Institución APV', tracking=True)
    aporte_voluntario = fields.Float(
        'Ahorro Previsional Voluntario (APV/APVC)',
        digits='Payroll Rate',
        help="Monto del Ahorro Previsional Voluntario (APV o APVC), en UF o Pesos según 'Tipo Moneda APV'.",
        tracking=True
    )
    aporte_voluntario_moneda = fields.Selection(
        [('uf', 'UF'), ('clp', 'Pesos')],
        string='Tipo Moneda APV',
        default="uf",
        tracking=True,
        help="Moneda en la que está expresado el 'Aporte Voluntario'."
    )
    forma_pago_apv = fields.Selection(
        [('1', 'Directa (Empleado a Institución)'), ('2', 'Indirecta (Descuento Empleador)')], # Added descriptions
        string='Forma de Pago APV',
        default="2", # Changed default to Indirect, common for payroll
        tracking=True,
        help="Cómo se realiza el pago del APV."
    )
    seguro_complementario_moneda = fields.Selection(
        [('uf', 'UF'), ('clp', 'Pesos')],
        string='Tipo Moneda Seguro Comp.',
        default="uf",
        tracking=True,
        help="Moneda en la que está expresada la 'Cotización Seguro Comp.'."
    )

    # Overriding existing fields to add tracking or modify slightly
    wage = fields.Monetary('Sueldo Base', required=True, tracking=True, help="Sueldo base mensual del empleado.")
    job_id = fields.Many2one('hr.job', tracking=True)
    department_id = fields.Many2one('hr.department', tracking=True)
    resource_calendar_id = fields.Many2one('resource.calendar', tracking=True)
    company_id = fields.Many2one('res.company', tracking=True)
    employee_id = fields.Many2one('hr.employee', tracking=True)
    date_start = fields.Date('Fecha Inicio Contrato', required=True, tracking=True)
    date_end = fields.Date('Fecha Fin Contrato', tracking=True)
    structure_type_id = fields.Many2one('hr.payroll.structure.type', string="Salary Structure Type", tracking=True)
    journal_id = fields.Many2one(
    'account.journal',
    string="Diario de Sueldos",
    domain="[('type', '=', 'general')]"
)

    @api.depends('employee_id.name')
    def _compute_complete_name(self):
        for contract in self:
            first = contract.employee_id.name or ""
            last = contract.last_name or ""
            contract.complete_name = f"{first} {last}".strip()
