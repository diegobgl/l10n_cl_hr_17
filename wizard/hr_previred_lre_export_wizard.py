# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import date
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
    # Opcional: filtro por journal/estructura salarial/centro de costo
    structure_id = fields.Many2one('hr.payroll.structure', string='Estructura Salarial')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Centro de Costo')

    def _period_range(self):
        year = int(self.period_year)
        month = int(self.period_month)
        date_from = date(year, month, 1)
        # último día del mes
        if month == 12:
            date_to = date(year+1, 1, 1) - fields.Date.resolution
        else:
            date_to = date(year, month+1, 1) - fields.Date.resolution
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
    def _rut_parts(partner):
        """Devuelve (rut_num, dv) SIN puntos y con guion DV aparte."""
        # Asume partner.vat = 'CLXXXXXXXX-X' o 'XXXXXXXX-X'
        vat = (partner.vat or '').replace('CL', '').replace('.', '').replace('-', '')
        if not vat or not vat[:-1].isdigit():
            return ('', '')
        return (vat[:-1], vat[-1].upper())

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

        # PREVIRED exige 105 campos por línea; si no aplica: ceros o blancos (según tipo). :contentReference[oaicite:3]{index=3}
        # Construimos filas mínimas viables y dejamos extensiones en 0/''.
        buf = io.StringIO()
        writer = csv.writer(buf, delimiter=SEPARATOR, lineterminator='\n')

        # mmaaaa del período
        period_mmaaaa = '%02d%s' % (int(self.period_month), str(self.period_year))

        # Mapeo base: códigos de institución (AFP/FONASA/ISAPRE/Mutual/CCAF) deben existir en tus catálogos locales
        # o en un modelo de parámetros (ej. hr.indicadores) para calcular montos/tasas.
        # Datos condicionales (APV, Trabajo Pesado, Subsidios, Movimientos, etc.) suman líneas anexas. :contentReference[oaicite:4]{index=4}

        for slip in slips:
            emp = slip.employee_id
            contract = slip.contract_id
            if not emp or not contract:
                # Saltamos sin romper export
                continue

            rut_num, rut_dv = self._rut_parts(emp.address_home_id or emp)
            apellido_p = self._clean_str(emp.last_name or emp.name.split()[:1][0] if emp.name else '')
            apellido_m = self._clean_str(getattr(emp, 'x_lastname_m', '') or '')
            nombres = self._clean_str(getattr(emp, 'x_firstnames', '') or emp.name)

            # Sexo M/F según campo genero del empleado
            sexo = 'M' if getattr(emp, 'gender', '') in ('male', 'm') else 'F'

            # Nacionalidad: 0 Chileno, 1 Extranjero. Ajusta según tus campos. :contentReference[oaicite:5]{index=5}
            nacionalidad = '0' if getattr(emp, 'country_id', False) and emp.country_id.code == 'CL' else '1'

            # Tipo de pago (8): 01 Normal (por defecto). Refiérete a tabla equivalencia. :contentReference[oaicite:6]{index=6}
            tipo_pago = '01'

            # Período desde/hasta: para la gran mayoría misma mmaaaa
            periodo_desde = period_mmaaaa
            periodo_hasta = ''  # condicional

            # Régimen previsional / Tipo trabajador (pens/activo) según contrato
            regimen_previsional = 'AFP'  # Placeholder ‘AFP’ → PreviRed espera códigos; mapea a tu tabla local.
            tipo_trabajador = '1'  # 1=Activo, 2=Pensionado (ajusta si corresponde). :contentReference[oaicite:7]{index=7}

            # Días trabajados (1115 en LRE, aquí “Días trabajados” campo 13 PREVIRED). :contentReference[oaicite:8]{index=8}
            dias_trabajados = self._clean_int(slip.worked_days_line_ids.filtered(lambda l: l.code == 'WORK100').number_of_days or 30)

            # Tipo de línea (14): 00 = principal (ver tabla 6). :contentReference[oaicite:9]{index=9}
            tipo_linea = '00'

            # Movimiento de personal (15,16,17): por defecto 11 “Otros Movimientos (Ausentismo)” solo si corresponde. :contentReference[oaicite:10]{index=10}
            cod_mov = '00'   # 00 = sin movimiento adicional (usa tu convención); si usas 11/3/6, completa fechas/rut pagador.

            fecha_desde = ''
            fecha_hasta = ''

            # Asignación familiar: tramo y cargas (18-24). Si no admin, setea ceros. :contentReference[oaicite:11]{index=11}
            tramo_asig = 'A'  # A/B/C/D según renta imponible; calcula con tus indicadores.
            cargas_simples = '0'
            cargas_maternas = '0'
            cargas_invalidas = '0'
            asig_familiar = '0'
            asig_retro = '0'
            reintegro_cargas = '0'
            sol_trabajador_joven = 'N'  # Uso futuro en spec. :contentReference[oaicite:12]{index=12}

            # -------- AFP --------
            afp_code = (contract.l10n_cl_afp_code or '')  # Debes guardar este code según tabla equivalencia. :contentReference[oaicite:13]{index=13}
            renta_imp_afp = self._clean_int(slip._get_salary_line_total('IMPONIBLE'))  # tu regla imponible
            cot_oblig_afp = self._clean_int(slip._get_salary_line_total('AFP'))        # regla descuento AFP
            sis_empleador = self._clean_int(slip._get_salary_line_total('SIS_EMP'))    # regla SIS empleador

            # -------- SALUD --------
            salud_code = (contract.l10n_cl_health_code or '')  # FONASA=07 o ISAPRE según tabla. :contentReference[oaicite:14]{index=14}
            fun_numero = (contract.l10n_cl_isapre_fun or '')
            renta_imp_isapre = self._clean_int(slip._get_salary_line_total('IMPONIBLE'))  # misma base
            moneda_plan = '1'  # 1=$, 2=UF (tabla 17). :contentReference[oaicite:15]{index=15}
            cotizacion_pactada = self._clean_int(slip._get_salary_line_total('ISAPRE_PACTADA'))
            cot_oblig_isapre = self._clean_int(slip._get_salary_line_total('SALUD_7'))
            cot_adic_vol_isapre = self._clean_int(slip._get_salary_line_total('SALUD_ADIC'))

            # -------- CCAF / Mutual / AFC -------- (rellena si aplica, ver tablas de equivalencia) :contentReference[oaicite:16]{index=16}
            ccaf_code = (contract.l10n_cl_ccaf_code or '')
            renta_imp_ccaf = self._clean_int(slip._get_salary_line_total('IMPONIBLE'))
            mutual_code = (contract.l10n_cl_mutual_code or '')
            renta_imp_mutual = self._clean_int(slip._get_salary_line_total('IMPONIBLE'))
            cot_mutual = self._clean_int(slip._get_salary_line_total('MUTUAL'))

            renta_imp_sc = self._clean_int(slip._get_salary_line_total('IMPONIBLE_SC'))  # renta total imponible seguro cesantía (tope UF 90). :contentReference[oaicite:17]{index=17}
            sc_trabajador = self._clean_int(slip._get_salary_line_total('AFC_TRAB'))
            sc_empleador = self._clean_int(slip._get_salary_line_total('AFC_EMP'))

            # Armar lista de 105 campos (inicia con los 1..25, etc.). Los no aplicables: '' o 0 según tipo. :contentReference[oaicite:18]{index=18}
            row = []
            # 1..5 Identificación
            row += [rut_num, rut_dv, apellido_p, apellido_m, nombres]
            # 6..13
            row += [cod_mov, fecha_desde, fecha_hasta, afp_code or '00', salud_code or '00', '', '']  # (rut pagador subsidio si aplica)
            # Ajuste: desde campo 1..105 según especificación exacta. Para brevedad, mostramos campos clave:
            # Reemplaza/ordena exactamente conforme a la tabla 1..105 del PDF (largo variable).
            # [...]
            # Campos 26..39 (AFP)
            row += [afp_code or '00', renta_imp_afp, cot_oblig_afp, sis_empleador, 0, 0, 0, 0, 0, 0, '', '','', '', '','', '', 0, '00', 0]
            # Campos 40..49 (APV/APVC)
            row += ['000','','',0,0,'000','','',0,0]
            # Campos 50..61 (Afiliado voluntario)
            row += ['','','','','','00','','','00',0,0,0]
            # Campos 62..74 (IPS/ISL/FONASA)
            row += ['0000','00,00',0,'0000','00,00',0,0,0,0,0,0,0,0]
            # Campos 75..82 (Salud)
            row += [salud_code or '00', fun_numero, renta_imp_isapre, '1', cotizacion_pactada, cot_oblig_isapre, cot_adic_vol_isapre, 0]
            # Campos 83..95 (CCAF)
            row += [ccaf_code or '00', renta_imp_ccaf] + [0]*11
            # Campos 96..99 (Mutual)
            row += [mutual_code or '00', renta_imp_mutual, cot_mutual, '000']
            # Campos 100..102 (AFC)
            row += [renta_imp_sc, sc_trabajador, sc_empleador]
            # Campos 103..105 (Pagador subsidios / Centro costo)
            row += ['', '', '']  # rut, dv, centro de costos

            # Asegura 105 posiciones:
            if len(row) < 105:
                row += [''] * (105 - len(row))
            elif len(row) > 105:
                row = row[:105]

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
        action = {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/{attachment.id}?download=1",
            'target': 'self',
        }
        return action

    # --------------------------
    # EXPORT LRE (CSV)
    # --------------------------
    def _export_lre(self):
        slips = self.env['hr.payslip'].search(self._slips_domain(), order='employee_id')
        if not slips:
            raise UserError(_('No hay liquidaciones validadas en el período.'))

        # Estructura basada en el suplemento LRE (códigos 11xx, 21xx, 31xx, 41xx, 5xxx). :contentReference[oaicite:19]{index=19}
        headers = [
            '1101_rut', '1102_inicio_contrato', '1103_termino_contrato', '1107_tipo_jornada',
            '1141_afp', '1143_salud', '1151_afc', '1115_dias_trabajados',
            '2101_sueldo', '2111_bonos_fijos', '5210_total_imponible',
            '3141_cot_oblig_afp', '3143_salud_7', '3151_afc_trab',
            '4151_afc_emp', '4152_seg_accidentes', '4155_sis_emp',
            '5201_total_haberes', '5301_total_descuentos', '5410_total_aportes',
            '5501_liquido'
        ]

        buf = io.StringIO()
        writer = csv.writer(buf, delimiter=SEPARATOR, lineterminator='\n')
        writer.writerow(headers)

        for slip in slips:
            emp = slip.employee_id
            contract = slip.contract_id
            rut_num, rut_dv = self._rut_parts(emp.address_home_id or emp)
            rut = f'{rut_num}-{rut_dv}' if rut_num and rut_dv else ''

            # Helpers para totales por código de regla
            def amt(code):
                line = slip.line_ids.filtered(lambda l: l.code == code)[:1]
                return int(round(line.total)) if line else 0

            row = [
                rut,
                contract.date_start or '',
                contract.date_end or '',
                getattr(contract, 'l10n_cl_tipo_jornada', ''),                # mapea a tabla de la DT
                getattr(contract, 'l10n_cl_afp_code', ''),                    # 1141
                getattr(contract, 'l10n_cl_health_code', ''),                 # 1143
                'S' if getattr(contract, 'l10n_cl_afc', True) else 'N',       # 1151
                int(round(sum(wd.number_of_days for wd in slip.worked_days_line_ids if wd.work_entry_type_id.is_leave is False))) or 30,  # 1115
                amt('BASIC'),                 # 2101 Sueldo
                amt('BONO_FIJO'),             # 2111 Bonos fijos
                amt('IMPONIBLE'),             # 5210 Total imponible
                amt('AFP'),                   # 3141
                amt('SALUD_7'),               # 3143
                amt('AFC_TRAB'),              # 3151
                amt('AFC_EMP'),               # 4151
                amt('MUTUAL'),                # 4152
                amt('SIS_EMP'),               # 4155
                amt('TOTAL_HABERES'),         # 5201
                amt('TOTAL_DESCUENTOS'),      # 5301
                amt('TOTAL_APORTES_EMP'),     # 5410
                amt('NET'),                   # 5501 Liquido
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
