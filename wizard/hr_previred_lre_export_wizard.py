# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import date, timedelta
import base64
import io
import csv

SEPARATOR = ';'


class HrPreviredLreExportWizard(models.TransientModel):
    _name = 'hr.previred.lre.export.wizard'
    _description = 'Exportador PREVIRED / LRE (Chile)'

    company_id = fields.Many2one(
        'res.company', string='Compañía', required=True,
        default=lambda self: self.env.company
    )
    period_month = fields.Selection(
        [(str(m), '%02d' % m) for m in range(1, 13)],
        string='Mes', required=True, default=lambda self: str(fields.Date.today().month)
    )
    period_year = fields.Integer(
        string='Año', required=True, default=lambda self: fields.Date.today().year
    )
    export_type = fields.Selection(
        [('previred', 'PREVIRED (TXT/CSV)'), ('lre', 'Libro Remuneraciones Electrónico (CSV)')],
        string='Tipo de Exportación', required=True, default='previred'
    )
    include_zip = fields.Boolean('Comprimir en ZIP', default=False)
    structure_id = fields.Many2one('hr.payroll.structure', string='Estructura Salarial')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Centro de Costo')

    def _period_range(self):
        year = int(self.period_year)
        month = int(self.period_month)
        date_from = date(year, month, 1)
        if month == 12:
            date_to = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            date_to = date(year, month + 1, 1) - timedelta(days=1)
        return date_from, date_to

    def _slips_domain(self):
        date_from, date_to = self._period_range()
        domain = [
            ('company_id', '=', self.company_id.id),
            ('state', '=', 'done'),
            ('date_from', '>=', date_from),
            ('date_to', '<=', date_to),
        ]
        if self.structure_id:
            domain.append(('struct_id', '=', self.structure_id.id))
        return domain

    # --------------------------
    # UTILIDADES DE FORMATEO CL
    # --------------------------
    @staticmethod
    def _clean_str(val, size=None):
        out = (val or '').strip().upper()
        if size:
            out = out[:size]
        return out

    @staticmethod
    def _clean_int(n, zeros=0):
        try:
            v = int(round(float(n or 0)))
        except Exception:
            v = 0
        return str(v).rjust(zeros, '0') if zeros else str(v)

    @staticmethod
    def _rut_parts(identification_id):
        """Devuelve (rut_num, dv) SIN puntos, DV aparte.
        Acepta formatos: '12.345.678-9', '12345678-9', 'CL12345678-9'.
        """
        val = (identification_id or '').replace('CL', '').replace('.', '').replace('-', '').upper()
        if not val or len(val) < 2 or not val[:-1].isdigit():
            return ('', '')
        return (val[:-1], val[-1])

    @staticmethod
    def _bool_to_S(val):
        return 'S' if bool(val) else 'N'

    # --------------------------
    # EXPORT PREVIRED
    # --------------------------
    def action_export(self):
        self.ensure_one()
        if self.export_type == 'previred':
            return self._export_previred()
        return self._export_lre()

    def _export_previred(self):
        slips = self.env['hr.payslip'].search(self._slips_domain(), order='employee_id')
        if not slips:
            raise UserError(_('No hay liquidaciones validadas en el período.'))

        buf = io.StringIO()
        writer = csv.writer(buf, delimiter=SEPARATOR, lineterminator='\n')

        period_mmaaaa = '%02d%s' % (int(self.period_month), str(self.period_year))

        for slip in slips:
            emp = slip.employee_id
            contract = slip.contract_id
            indic = slip.indicadores_id
            if not emp or not contract:
                continue

            # Identificación empleado
            rut_num, rut_dv = self._rut_parts(emp.identification_id)
            apellido_p = self._clean_str(emp.last_name or '')
            apellido_m = self._clean_str(emp.mothers_name or '')
            nombres = self._clean_str(emp.firstname or emp.name or '')

            sexo = 'M' if (emp.gender or '') in ('male', 'm') else 'F'
            nacionalidad = '0' if (emp.country_id and emp.country_id.code == 'CL') else '1'
            tipo_pago = '01'
            periodo_desde = period_mmaaaa
            tipo_trabajador = '2' if (contract.pension or False) else '1'

            dias_trabajados = self._clean_int(
                slip.worked_days_line_ids.filtered(lambda l: l.code == 'WORK100').number_of_days or 30
            )
            tipo_linea = '00'

            # Movimiento de personal desde la liquidación
            cod_mov = slip.movimientos_personal or '0'
            fecha_desde = str(slip.date_start_mp or '')
            fecha_hasta = str(slip.date_end_mp or '')

            # Asignación familiar: determinar tramo
            afam_renta = (contract.wage or 0.0)
            if indic:
                if afam_renta <= (indic.asignacion_familiar_primer or 0.0):
                    tramo_asig = 'A'
                elif afam_renta <= (indic.asignacion_familiar_segundo or 0.0):
                    tramo_asig = 'B'
                elif afam_renta <= (indic.asignacion_familiar_tercer or 0.0):
                    tramo_asig = 'C'
                else:
                    tramo_asig = 'D'
            else:
                tramo_asig = 'A'

            cargas_simples = self._clean_int(contract.carga_familiar or 0)
            cargas_maternas = self._clean_int(contract.carga_familiar_maternal or 0)
            cargas_invalidas = self._clean_int(contract.carga_familiar_invalida or 0)
            asig_familiar = self._clean_int(slip._get_salary_line_total('ASIGFAM'))
            asig_retro = '0'
            reintegro_cargas = '0'
            sol_trabajador_joven = 'N'

            # AFP
            afp_code = (contract.afp_id.codigo or '00') if contract.afp_id else '00'
            renta_imp_afp = self._clean_int(slip._get_salary_line_total('IMPONIBLE'))
            cot_oblig_afp = self._clean_int(abs(slip._get_salary_line_total('AFP')))
            sis_empleador = self._clean_int(abs(slip._get_salary_line_total('SIS')))

            # Salud
            if contract.isapre_id:
                salud_code = contract.isapre_id.codigo or '00'
                fun_numero = contract.isapre_fun or ''
                moneda_plan = '2' if contract.isapre_moneda == 'uf' else '1'
                cotizacion_pactada = self._clean_int(
                    (contract.isapre_cotizacion_uf or 0.0) * ((indic.uf or 0.0) if indic else 0.0)
                    if contract.isapre_moneda == 'uf'
                    else (contract.isapre_cotizacion_uf or 0.0)
                )
                cot_oblig_isapre = self._clean_int(abs(slip._get_salary_line_total('SALUD')))
                cot_adic_vol_isapre = '0'
            else:
                salud_code = '07'  # FONASA
                fun_numero = ''
                moneda_plan = '1'
                cotizacion_pactada = '0'
                cot_oblig_isapre = self._clean_int(abs(slip._get_salary_line_total('SALUD')))
                cot_adic_vol_isapre = '0'

            renta_imp_isapre = renta_imp_afp

            # CCAF (código desde indicadores)
            ccaf_code = ''
            if indic and indic.ccaf_id:
                ccaf_code = indic.ccaf_id.codigo or ''
            renta_imp_ccaf = renta_imp_afp

            # Mutual
            mutual_code = ''
            if indic and indic.mutualidad_id:
                mutual_code = indic.mutualidad_id.codigo or ''
            renta_imp_mutual = renta_imp_afp
            cot_mutual = self._clean_int(abs(slip._get_salary_line_total('MUTUAL')))

            # AFC
            renta_imp_sc = renta_imp_afp
            sc_trabajador = self._clean_int(abs(slip._get_salary_line_total('SC_TRAB')))
            sc_empleador = self._clean_int(abs(slip._get_salary_line_total('SC_EMPL')))

            # Construcción fila de 105 campos según especificación Previred
            row = []
            # Campos 1-5: identificación
            row += [rut_num, rut_dv, apellido_p, apellido_m, nombres]
            # Campos 6-17: movimiento, AFP, salud (orden simplificado)
            row += [cod_mov, fecha_desde, fecha_hasta, afp_code or '00', salud_code or '00', '', '']
            # Campos 18-24: asignación familiar
            row += [tramo_asig, cargas_simples, cargas_maternas, cargas_invalidas,
                    asig_familiar, asig_retro, reintegro_cargas]
            # Campos 25: trabajador joven
            row += [sol_trabajador_joven]
            # Campos 26-45: AFP y APV
            row += [afp_code or '00', renta_imp_afp, cot_oblig_afp, sis_empleador,
                    0, 0, 0, 0, 0, 0, '', '', '', '', '', '', '', 0, '00', 0]
            # Campos 46-55: APV/APVC
            row += ['000', '', '', 0, 0, '000', '', '', 0, 0]
            # Campos 56-67: afiliado voluntario
            row += ['', '', '', '', '', '00', '', '', '00', 0, 0, 0]
            # Campos 68-80: IPS/ISL/FONASA
            row += ['0000', '00,00', 0, '0000', '00,00', 0, 0, 0, 0, 0, 0, 0, 0]
            # Campos 81-88: Salud
            row += [salud_code or '00', fun_numero, renta_imp_isapre,
                    moneda_plan, cotizacion_pactada, cot_oblig_isapre, cot_adic_vol_isapre, 0]
            # Campos 89-101: CCAF
            row += [ccaf_code or '00', renta_imp_ccaf] + [0] * 11
            # Campos 102-105: Mutual
            row += [mutual_code or '00', renta_imp_mutual, cot_mutual, '000']
            # Campos 106-108: AFC
            row += [renta_imp_sc, sc_trabajador, sc_empleador]
            # Campos 109-111: Pagador subsidios / Centro costo
            row += ['', '', '']

            expected_columns = 111
            if len(row) < expected_columns:
                row += [''] * (expected_columns - len(row))
            elif len(row) > expected_columns:
                row = row[:expected_columns]

            writer.writerow([str(x) for x in row])

        filename = f'previred_{self.company_id.id}_{self.period_year}{int(self.period_month):02d}.txt'
        data = buf.getvalue().encode('utf-8')
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(data),
            'res_model': 'hr.previred.lre.export.wizard',
            'res_id': self.id,
            'mimetype': 'text/plain',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/{attachment.id}?download=1",
            'target': 'self',
        }

    # --------------------------
    # EXPORT LRE (CSV)
    # --------------------------
    def _export_lre(self):
        slips = self.env['hr.payslip'].search(self._slips_domain(), order='employee_id')
        if not slips:
            raise UserError(_('No hay liquidaciones validadas en el período.'))

        headers = [
            '1101_rut', '1102_inicio_contrato', '1103_termino_contrato', '1107_tipo_jornada',
            '1141_afp', '1143_salud', '1151_afc', '1115_dias_trabajados',
            '2101_sueldo', '2111_bonos_fijos', '5210_total_imponible',
            '3141_cot_oblig_afp', '3143_salud_desc', '3151_afc_trab',
            '4151_afc_emp', '4152_seg_accidentes', '4155_sis_emp',
            '5201_total_haberes', '5301_total_descuentos', '5410_total_aportes',
            '5501_liquido',
        ]

        buf = io.StringIO()
        writer = csv.writer(buf, delimiter=SEPARATOR, lineterminator='\n')
        writer.writerow(headers)

        for slip in slips:
            emp = slip.employee_id
            contract = slip.contract_id
            indic = slip.indicadores_id

            rut_num, rut_dv = self._rut_parts(emp.identification_id)
            rut = f'{rut_num}-{rut_dv}' if rut_num and rut_dv else ''

            def amt(code):
                line = slip.line_ids.filtered(lambda l: l.code == code)[:1]
                return int(round(line.total)) if line else 0

            # Código AFP
            afp_code = (contract.afp_id.codigo or '') if contract.afp_id else ''
            # Código salud: isapre o FONASA (07)
            salud_code = (contract.isapre_id.codigo or '07') if contract.isapre_id else '07'
            # Cotiza AFC
            cotiza_afc = 'S' if not (contract.pension or contract.sin_afp) else 'N'

            dias_trabajados = int(round(sum(
                wd.number_of_days for wd in slip.worked_days_line_ids
                if not wd.work_entry_type_id.is_leave
            ))) or 30

            # Totales descuentos trabajador (AFP + salud + AFC trab + APV + IUT)
            total_descuentos = (
                amt('AFP') + amt('SALUD') + amt('SC_TRAB') + amt('APV') + amt('IUT')
            )
            # Totales aportes empleador (SIS + AFC empl + Mutual)
            total_aportes_emp = amt('SIS') + amt('SC_EMPL') + amt('MUTUAL')

            row = [
                rut,
                contract.date_start or '',
                contract.date_end or '',
                '',                         # 1107 tipo jornada (no implementado)
                afp_code,                   # 1141
                salud_code,                 # 1143
                cotiza_afc,                 # 1151
                dias_trabajados,            # 1115
                amt('SUELDO'),              # 2101 Sueldo base
                0,                          # 2111 Bonos fijos (no implementado)
                amt('IMPONIBLE'),           # 5210 Total imponible
                abs(amt('AFP')),            # 3141
                abs(amt('SALUD')),          # 3143
                abs(amt('SC_TRAB')),        # 3151
                abs(amt('SC_EMPL')),        # 4151
                abs(amt('MUTUAL')),         # 4152
                abs(amt('SIS')),            # 4155
                amt('BRUTO'),               # 5201 Total haberes
                abs(total_descuentos),      # 5301 Total descuentos trabajador
                abs(total_aportes_emp),     # 5410 Total aportes empleador
                amt('NETO'),                # 5501 Líquido
            ]
            writer.writerow(row)

        filename = f'lre_{self.company_id.id}_{self.period_year}{int(self.period_month):02d}.csv'
        data = buf.getvalue().encode('utf-8')
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(data),
            'res_model': 'hr.previred.lre.export.wizard',
            'res_id': self.id,
            'mimetype': 'text/csv',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/{attachment.id}?download=1",
            'target': 'self',
        }
