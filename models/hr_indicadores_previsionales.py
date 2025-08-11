# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from urllib.error import URLError
from bs4 import BeautifulSoup
from datetime import datetime
import logging
import requests
import base64
import io
import re

# Preferir pypdf (proyecto actual). Fallback a PyPDF2 si no está disponible.
try:
    from pypdf import PdfReader
except Exception:
    from PyPDF2 import PdfReader

_logger = logging.getLogger(__name__)

MONTH_LIST = [
    ('1', 'Enero'), ('2', 'Febrero'), ('3', 'Marzo'),
    ('4', 'Abril'), ('5', 'Mayo'), ('6', 'Junio'),
    ('7', 'Julio'), ('8', 'Agosto'), ('9', 'Septiembre'),
    ('10', 'Octubre'), ('11', 'Noviembre'), ('12', 'Diciembre')
]


class HrIndicadores(models.Model):
    _name = 'hr.indicadores'
    _description = 'Indicadores Previsionales'
    _order = 'year desc, month desc'

    # Identificación / estado
    name = fields.Char('Nombre Período', compute='_compute_name', store=True, readonly=True)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('done', 'Validado'),
    ], string='Estado', readonly=True, default='draft', tracking=True)

    # Archivos
    pdf_file = fields.Binary('Archivo PDF')
    pdf_filename = fields.Char('Nombre del Archivo')

    # Período
    month = fields.Selection(MONTH_LIST, string='Mes', required=True)
    year = fields.Integer('Año', required=True, default=lambda self: datetime.now().year)

    # --- Asignación Familiar
    asignacion_familiar_primer = fields.Float('Tope Tramo 1 AF', digits='Payroll', help="Límite superior renta imponible Tramo 1 Asig. Familiar ($)")
    asignacion_familiar_segundo = fields.Float('Tope Tramo 2 AF', digits='Payroll', help="Límite superior renta imponible Tramo 2 Asig. Familiar ($)")
    asignacion_familiar_tercer = fields.Float('Tope Tramo 3 AF', digits='Payroll', help="Límite superior renta imponible Tramo 3 Asig. Familiar ($)")
    asignacion_familiar_monto_a = fields.Float('Monto Tramo 1 AF', digits='Payroll', help="Monto Asignación Familiar por carga para Tramo 1 ($)")
    asignacion_familiar_monto_b = fields.Float('Monto Tramo 2 AF', digits='Payroll', help="Monto Asignación Familiar por carga para Tramo 2 ($)")
    asignacion_familiar_monto_c = fields.Float('Monto Tramo 3 AF', digits='Payroll', help="Monto Asignación Familiar por carga para Tramo 3 ($)")

    # --- Seguro Cesantía (tasas)
    contrato_plazo_fijo_empleador = fields.Float('SC Tasa Fijo Empleador (%)', digits='Payroll Rate', help="Seguro Cesantía Plazo Fijo - Empleador (%)")
    contrato_plazo_fijo_trabajador = fields.Float('SC Tasa Fijo Trabajador (%)', digits='Payroll Rate', help="Seguro Cesantía Plazo Fijo - Trabajador (%)")
    contrato_plazo_indefinido_empleador = fields.Float('SC Tasa Indef. Empleador (%)', digits='Payroll Rate', help="Seguro Cesantía Indefinido (<11 años) Empleador (%)")
    contrato_plazo_indefinido_trabajador = fields.Float('SC Tasa Indef. Trabajador (%)', digits='Payroll Rate', help="Seguro Cesantía Indefinido (<11 años) Trabajador (%)")
    contrato_plazo_indefinido_empleador_otro = fields.Float('SC Tasa Indef. 11+ Empleador (%)', digits='Payroll Rate', help="Seguro Cesantía Indefinido (11+ años) Empleador (%)")
    contrato_plazo_indefinido_trabajador_otro = fields.Float('SC Tasa Indef. 11+ Trabajador (%)', digits='Payroll Rate', help="Seguro Cesantía Indefinido (11+ años) Trabajador (%)")

    # --- Otros legales
    caja_compensacion = fields.Float('Tasa Base CCAF (%)', digits='Payroll Rate')
    fonasa = fields.Float('Tasa FONASA (%)', digits='Payroll Rate')
    mutual_seguridad = fields.Float('Tasa Base Mutual (%)', digits='Payroll Rate')
    isl = fields.Float('Tasa Base ISL (%)', digits='Payroll Rate')

    # --- Sueldo Mínimo
    sueldo_minimo = fields.Float('Sueldo Mínimo General', digits='Payroll')
    sueldo_minimo_otro = fields.Float('Sueldo Mínimo (<18/>65)', digits='Payroll')

    # --- AFP (tasa obligatoria)
    tasa_afp_capital = fields.Float('Tasa AFP Capital (%)', digits='Payroll Rate')
    tasa_afp_cuprum = fields.Float('Tasa AFP Cuprum (%)', digits='Payroll Rate')
    tasa_afp_habitat = fields.Float('Tasa AFP Habitat (%)', digits='Payroll Rate')
    tasa_afp_modelo = fields.Float('Tasa AFP Modelo (%)', digits='Payroll Rate')
    tasa_afp_planvital = fields.Float('Tasa AFP PlanVital (%)', digits='Payroll Rate')
    tasa_afp_provida = fields.Float('Tasa AFP ProVida (%)', digits='Payroll Rate')
    tasa_afp_uno = fields.Float('Tasa AFP Uno (%)', digits='Payroll Rate')

    # --- SIS
    tasa_sis_capital = fields.Float('Tasa SIS Capital (%)', digits='Payroll Rate')
    tasa_sis_cuprum = fields.Float('Tasa SIS Cuprum (%)', digits='Payroll Rate')
    tasa_sis_habitat = fields.Float('Tasa SIS Habitat (%)', digits='Payroll Rate')
    tasa_sis_modelo = fields.Float('Tasa SIS Modelo (%)', digits='Payroll Rate')
    tasa_sis_planvital = fields.Float('Tasa SIS PlanVital (%)', digits='Payroll Rate')
    tasa_sis_provida = fields.Float('Tasa SIS ProVida (%)', digits='Payroll Rate')
    tasa_sis_uno = fields.Float('Tasa SIS Uno (%)', digits='Payroll Rate')

    # --- Independientes (AFP + SIS)
    tasa_independiente_capital = fields.Float('Tasa Indep. Capital (%)', digits='Payroll Rate')
    tasa_independiente_cuprum = fields.Float('Tasa Indep. Cuprum (%)', digits='Payroll Rate')
    tasa_independiente_habitat = fields.Float('Tasa Indep. Habitat (%)', digits='Payroll Rate')
    tasa_independiente_modelo = fields.Float('Tasa Indep. Modelo (%)', digits='Payroll Rate')
    tasa_independiente_planvital = fields.Float('Tasa Indep. PlanVital (%)', digits='Payroll Rate')
    tasa_independiente_provida = fields.Float('Tasa Indep. ProVida (%)', digits='Payroll Rate')
    tasa_independiente_uno = fields.Float('Tasa Indep. Uno (%)', digits='Payroll Rate')

    # --- Topes (UF) y APV
    tope_anual_apv = fields.Float('Tope Anual APV (UF)', digits='Payroll Rate')
    tope_mensual_apv = fields.Float('Tope Mensual APV (UF)', digits='Payroll Rate')
    tope_imponible_afp = fields.Float('Tope Imponible AFP/IPS (UF)', digits='Payroll Rate')
    tope_imponible_ips = fields.Float('Tope Imponible IPS (UF)', digits='Payroll Rate', help="Usualmente igual al tope de AFP")
    tope_imponible_salud = fields.Float('Tope Imponible Salud (UF)', digits='Payroll Rate')
    tope_imponible_seguro_cesantia = fields.Float('Tope Imponible SC (UF)', digits='Payroll Rate')
    deposito_convenido = fields.Float('Tope Depósito Convenido (UF)', digits='Payroll Rate')

    # --- Valores monetarios e índices
    uf = fields.Float('Valor UF (Fin de Mes)', digits=(16, 2))
    utm = fields.Float('Valor UTM (Mes)', digits='Payroll', required=True)
    uta = fields.Float('Valor UTA (Año)', digits='Payroll')
    uf_otros = fields.Float('UF Otros', digits='Payroll Rate', help="UF Seguro Complementario")
    ipc = fields.Float('Variación IPC Mensual (%)', digits='Payroll Rate')

    # --- Instituciones por defecto
    mutualidad_id = fields.Many2one('hr.mutual', 'Mutualidad Compañía')
    ccaf_id = fields.Many2one('hr.ccaf', 'CCAF Compañía')

    # --- Configuración adicional
    gratificacion_legal = fields.Boolean(
        string="Activar Gratificación Legal Manual",
        help="Permite usar gratificación legal en vez de regla estándar. Se puede condicionar en reglas salariales."
    )
    pensiones_ips = fields.Boolean(
        string="Empresa tiene cotizantes en IPS",
        default=False,
        help="Activa reglas especiales si la empresa tiene empleados cotizando en IPS"
    )
    mutual_seguridad_bool = fields.Boolean(
        'Empresa Afiliada a Mutual', default=True,
        help="Indica si la empresa está afiliada a una Mutual (vs ISL)"
    )

    # --- Constraints
    _sql_constraints = [
        ('month_year_uniq', 'unique (month, year)', 'Ya existen indicadores para este Mes y Año!'),
    ]

    # --- Computed
    @api.depends('month', 'year')
    def _compute_name(self):
        month_map = dict(MONTH_LIST)
        for record in self:
            record.name = f"{month_map.get(record.month, '')} {record.year}"

    # --- Helpers scraping
    def _clean_value(self, value_str):
        """Limpia textos de moneda/porcentaje."""
        if not value_str:
            return 0.0
        cleaned = re.sub(r'[$.%\s]', '', value_str)
        cleaned = cleaned.replace(',', '.')
        cleaned = re.sub(r'[\u200b-\u200d\uFEFF]', '', cleaned)
        try:
            return float(cleaned)
        except ValueError:
            _logger.warning("No se pudo convertir a float: '%s'", value_str)
            return 0.0

    def _divide_values(self, num_str, den_str, default=0.0):
        num = self._clean_value(num_str)
        den = self._clean_value(den_str)
        if den:
            return round(num / den, 2)
        return default

    # --- Acción: actualizar desde Previred (web)
    def update_document(self):
        """Obtiene indicadores desde Previred (puede romper si cambia el HTML)."""
        url = 'https://www.previred.com/web/previred/indicadores-previsionales'
        headers = {'User-Agent': 'Mozilla/5.0'}

        for record in self:
            if record.state != 'draft':
                raise UserError(_("Solo se pueden actualizar indicadores en estado Borrador."))

            try:
                _logger.info("Fetch Previred: %s", url)
                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                tables = soup.find_all("table", class_="tableizer-table")

                if not tables or len(tables) < 7:
                    _logger.error("Estructura inesperada en Previred.")
                    raise UserError(_("No se encontró la estructura esperada en Previred. ¿Cambió la página?"))

                try:
                    # Tabla 0: UF/UTM/UTA
                    values_t0 = tables[0].find_all('strong')
                    record.uf = self._clean_value(values_t0[1].get_text() if len(values_t0) > 1 else '0')
                    record.utm = self._clean_value(values_t0[3].get_text() if len(values_t0) > 3 else '0')
                    record.uta = self._clean_value(values_t0[4].get_text() if len(values_t0) > 4 else '0')

                    uf_val = record.uf or 0.0

                    # Tabla 1: Topes imponibles
                    values_t1 = tables[1].find_all('strong')
                    if uf_val > 0:
                        record.tope_imponible_afp = self._clean_value(values_t1[1].get_text() if len(values_t1) > 1 else '0') / uf_val
                        record.tope_imponible_seguro_cesantia = self._clean_value(values_t1[2].get_text() if len(values_t1) > 2 else '0') / uf_val
                        record.tope_imponible_salud = self._clean_value(values_t1[3].get_text() if len(values_t1) > 3 else '0') / uf_val
                    else:
                        record.tope_imponible_afp = record.tope_imponible_seguro_cesantia = record.tope_imponible_salud = 0.0

                    # Tabla 2: Rentas mínimas
                    values_t2 = tables[2].find_all('strong')
                    record.sueldo_minimo = self._clean_value(values_t2[1].get_text() if len(values_t2) > 1 else '0')
                    record.sueldo_minimo_otro = self._clean_value(values_t2[2].get_text() if len(values_t2) > 2 else '0')

                    # Tabla 3: APV (anual/mensual en CLP, convertir a UF)
                    values_t3 = tables[3].find_all('strong')
                    if uf_val > 0:
                        record.tope_anual_apv = self._clean_value(values_t3[1].get_text() if len(values_t3) > 1 else '0') / uf_val
                        record.tope_mensual_apv = self._clean_value(values_t3[2].get_text() if len(values_t3) > 2 else '0') / uf_val
                    else:
                        record.tope_anual_apv = record.tope_mensual_apv = 0.0

                    # Tabla 4: Depósito convenido (CLP -> UF)
                    values_t4 = tables[4].find_all('strong')
                    record.deposito_convenido = (self._clean_value(values_t4[1].get_text()) / uf_val) if uf_val > 0 and len(values_t4) > 1 else 0.0

                    # Tabla 5: Seguro cesantía (tasas)
                    values_t5 = tables[5].find_all('strong')
                    record.contrato_plazo_indefinido_empleador = self._clean_value(values_t5[5].get_text() if len(values_t5) > 5 else '0')
                    record.contrato_plazo_indefinido_trabajador = self._clean_value(values_t5[6].get_text() if len(values_t5) > 6 else '0')
                    record.contrato_plazo_fijo_empleador = self._clean_value(values_t5[7].get_text() if len(values_t5) > 7 else '0')
                    record.contrato_plazo_indefinido_empleador_otro = self._clean_value(values_t5[9].get_text() if len(values_t5) > 9 else '0')

                    # Tabla 6: Tasas AFP/SIS/Indep
                    values_t6 = tables[6].find_all('strong')
                    # Capital
                    record.tasa_afp_capital = self._clean_value(values_t6[8].get_text() if len(values_t6) > 8 else '0')
                    record.tasa_sis_capital = self._clean_value(values_t6[9].get_text() if len(values_t6) > 9 else '0')
                    record.tasa_independiente_capital = self._clean_value(values_t6[10].get_text() if len(values_t6) > 10 else '0')
                    # Cuprum
                    record.tasa_afp_cuprum = self._clean_value(values_t6[11].get_text() if len(values_t6) > 11 else '0')
                    record.tasa_sis_cuprum = self._clean_value(values_t6[12].get_text() if len(values_t6) > 12 else '0')
                    record.tasa_independiente_cuprum = self._clean_value(values_t6[13].get_text() if len(values_t6) > 13 else '0')
                    # Habitat
                    record.tasa_afp_habitat = self._clean_value(values_t6[14].get_text() if len(values_t6) > 14 else '0')
                    record.tasa_sis_habitat = self._clean_value(values_t6[15].get_text() if len(values_t6) > 15 else '0')
                    record.tasa_independiente_habitat = self._clean_value(values_t6[16].get_text() if len(values_t6) > 16 else '0')
                    # PlanVital
                    record.tasa_afp_planvital = self._clean_value(values_t6[17].get_text() if len(values_t6) > 17 else '0')
                    record.tasa_sis_planvital = self._clean_value(values_t6[18].get_text() if len(values_t6) > 18 else '0')
                    record.tasa_independiente_planvital = self._clean_value(values_t6[19].get_text() if len(values_t6) > 19 else '0')
                    # ProVida
                    record.tasa_afp_provida = self._clean_value(values_t6[20].get_text() if len(values_t6) > 20 else '0')
                    record.tasa_sis_provida = self._clean_value(values_t6[21].get_text() if len(values_t6) > 21 else '0')
                    record.tasa_independiente_provida = self._clean_value(values_t6[22].get_text() if len(values_t6) > 22 else '0')
                    # Modelo
                    record.tasa_afp_modelo = self._clean_value(values_t6[23].get_text() if len(values_t6) > 23 else '0')
                    record.tasa_sis_modelo = self._clean_value(values_t6[24].get_text() if len(values_t6) > 24 else '0')
                    record.tasa_independiente_modelo = self._clean_value(values_t6[25].get_text() if len(values_t6) > 25 else '0')
                    # Uno (si existe, usa índices siguientes; si no, deja en 0 o repite modelo)
                    record.tasa_afp_uno = self._clean_value(values_t6[26].get_text() if len(values_t6) > 26 else '0')
                    record.tasa_sis_uno = self._clean_value(values_t6[27].get_text() if len(values_t6) > 27 else '0')
                    record.tasa_independiente_uno = self._clean_value(values_t6[28].get_text() if len(values_t6) > 28 else '0')

                    # Tabla 7: Asignación Familiar
                    if len(tables) > 7:
                        values_t7 = tables[7].find_all('strong')
                        record.asignacion_familiar_monto_a = self._clean_value(values_t7[4].get_text() if len(values_t7) > 4 else '0')
                        record.asignacion_familiar_monto_b = self._clean_value(values_t7[6].get_text() if len(values_t7) > 6 else '0')
                        record.asignacion_familiar_monto_c = self._clean_value(values_t7[8].get_text() if len(values_t7) > 8 else '0')
                        # Topes (extraídos desde el texto, números sueltos)
                        def _first_num(txt):
                            m = re.search(r'\d[\d.]*', (txt or '').replace('.', ''))
                            return self._clean_value(m.group()) if m else 0.0
                        record.asignacion_familiar_primer = _first_num(values_t7[5].get_text() if len(values_t7) > 5 else '')
                        record.asignacion_familiar_segundo = _first_num(values_t7[7].get_text() if len(values_t7) > 7 else '')
                        record.asignacion_familiar_tercer = _first_num(values_t7[9].get_text() if len(values_t7) > 9 else '')

                    _logger.info("Indicadores actualizados: %s", record.name)

                except (IndexError, AttributeError, TypeError, ValueError) as e:
                    _logger.error("Error parseando Previred para %s: %s", record.name, e)
                    raise UserError(_("Error al procesar datos de Previred para {}. La estructura puede haber cambiado.").format(record.name))

            except (requests.exceptions.RequestException, URLError) as e:
                _logger.error("Error de red al obtener Previred: %s", e)
                raise UserError(_("Error de red al obtener indicadores de Previred: %s") % e)
            except Exception as e:
                _logger.exception("Error inesperado actualizando indicadores (%s):", record.name)
                raise UserError(_("Error inesperado al actualizar indicadores para {}: {}").format(record.name, e))

        return True

    # --- Acción: parsear PDF subido
    def action_parse_pdf(self):
        self.ensure_one()
        if not self.pdf_file:
            raise UserError(_("Debes adjuntar un archivo PDF."))
        try:
            decoded = base64.b64decode(self.pdf_file)
            with io.BytesIO(decoded) as buf:
                reader = PdfReader(buf)
                parts = []
                for page in getattr(reader, "pages", []):
                    t = page.extract_text() or ""
                    if t:
                        parts.append(t)
            text = "\n".join(parts).strip()
            if not text:
                raise UserError(_("No se pudo extraer texto del PDF (¿es un PDF escaneado?)."))
            self._parse_values_from_text(text)
        except Exception as e:
            _logger.exception("Error al procesar el PDF")
            raise UserError(_("Error al procesar el PDF: %s") % e)

    # --- Parser de texto PDF
    def _parse_values_from_text(self, text):
        import unicodedata

        def normalize(txt):
            return unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode("ascii")

        lines = normalize(text).splitlines()
        num_re = re.compile(r'[-+]?\d{1,3}(?:[\.\s]\d{3})*(?:[,\.]\d+)?|[-+]?\d+(?:[,\.]\d+)?')

        def parse_number(s):
            m = num_re.search(s)
            if not m:
                return None
            v = m.group(0).replace("\u202f", "").replace(" ", "")
            # normaliza miles/decimales estilo CL
            if v.count(",") == 1 and v.count(".") >= 1:
                v = v.replace(".", "").replace(",", ".")
            elif "," in v and "." not in v:
                v = v.replace(",", ".")
            else:
                v = v.replace(",", "")
            try:
                return float(v)
            except Exception:
                return None

        vals = {}
        for raw in lines:
            line = raw.strip()
            low = line.lower()

            # directos
            if ' uf' in f' {low}' or low.startswith('uf'):
                v = parse_number(line)
                if v is not None:
                    vals['uf'] = v
            elif 'utm' in low:
                v = parse_number(line);  vals['utm'] = v if v is not None else vals.get('utm')
            elif 'fonasa' in low:
                v = parse_number(line);  vals['fonasa'] = v if v is not None else vals.get('fonasa')
            elif 'tope imponible afp' in low or 'tope imponible ips' in low:
                v = parse_number(line);  vals['tope_imponible_afp'] = v if v is not None else vals.get('tope_imponible_afp')
            elif 'tope imponible salud' in low:
                v = parse_number(line);  vals['tope_imponible_salud'] = v if v is not None else vals.get('tope_imponible_salud')
            elif 'tope imponible sc' in low or 'tope imponible seguro cesantia' in low:
                v = parse_number(line);  vals['tope_imponible_seguro_cesantia'] = v if v is not None else vals.get('tope_imponible_seguro_cesantia')

            # APV: detectar mensual/anual por el texto
            elif 'apv' in low or 'ahorro previsional voluntario' in low:
                v = parse_number(line)
                if v is not None:
                    if 'anual' in low:
                        vals['tope_anual_apv'] = v
                    elif 'mensual' in low:
                        vals['tope_mensual_apv'] = v

            # Seguro de cesantía (tasas)
            elif 'seguro cesantia contrato indefinido trabajador' in low:
                v = parse_number(line);  vals['contrato_plazo_indefinido_trabajador'] = v
            elif 'seguro cesantia contrato indefinido empleador' in low:
                v = parse_number(line);  vals['contrato_plazo_indefinido_empleador'] = v

            # Asignación familiar
            elif 'asignacion familiar tramo a' in low:
                v = parse_number(line);  vals['asignacion_familiar_monto_a'] = v
            elif 'asignacion familiar tramo b' in low:
                v = parse_number(line);  vals['asignacion_familiar_monto_b'] = v
            elif 'asignacion familiar tramo c' in low:
                v = parse_number(line);  vals['asignacion_familiar_monto_c'] = v

        if vals:
            self.write(vals)

    def action_done(self):
            self.write({'state': 'done'})
            return True

    def action_draft(self):
        self.write({'state': 'draft'})
        return True