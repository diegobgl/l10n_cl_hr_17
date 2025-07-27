# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from urllib.request import urlopen, Request # Added Request for headers
from urllib.error import URLError # To catch URL errors
from bs4 import BeautifulSoup
from datetime import datetime
import logging
import requests # Keep requests as a fallback or alternative if needed
import re # For cleaning strings more robustly
import base64
import io
import re
from PyPDF2 import PdfReader


_logger = logging.getLogger(__name__)

MONTH_LIST = [
    ('1', 'Enero'), ('2', 'Febrero'), ('3', 'Marzo'),
    ('4', 'Abril'), ('5', 'Mayo'), ('6', 'Junio'),
    ('7', 'Julio'), ('8', 'Agosto'), ('9', 'Septiembre'),
    ('10', 'Octubre'), ('11', 'Noviembre'), ('12', 'Diciembre')
]

# States no longer need explicit definition for readonly attribute handling in view
# readonly attribute in fields can depend directly on state field

class HrIndicadores(models.Model): # Renamed class
    _name = 'hr.indicadores'
    _description = 'Indicadores Previsionales (Forecast Indicators)'
    _order = 'year desc, month desc' # Added default order

    name = fields.Char('Nombre Período', compute='_compute_name', store=True, readonly=True)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('done', 'Validado'),
    ], string='Estado', readonly=True, default='draft', tracking=True)

    pdf_file = fields.Binary('Archivo PDF')
    pdf_filename = fields.Char('Nombre del Archivo')


    month = fields.Selection([
        ('1', 'Enero'),
        ('2', 'Febrero'),
        ('3', 'Marzo'),
        ('4', 'Abril'),
        ('5', 'Mayo'),
        ('6', 'Junio'),
        ('7', 'Julio'),
        ('8', 'Agosto'),
        ('9', 'Septiembre'),
        ('10', 'Octubre'),
        ('11', 'Noviembre'),
        ('12', 'Diciembre'),
    ], string='Mes')
    year = fields.Integer('Año', required=True, default=lambda self: datetime.now().year)

    # --- Fields Definition with Digits and Help Text ---
    # Asignación Familiar
    asignacion_familiar_primer = fields.Float('Tope Tramo 1 AF', digits='Payroll',  help="Límite superior Renta Imponible para Tramo 1 Asig. Familiar ($)")
    asignacion_familiar_segundo = fields.Float('Tope Tramo 2 AF', digits='Payroll',  help="Límite superior Renta Imponible para Tramo 2 Asig. Familiar ($)")
    asignacion_familiar_tercer = fields.Float('Tope Tramo 3 AF', digits='Payroll',  help="Límite superior Renta Imponible para Tramo 3 Asig. Familiar ($)")
    asignacion_familiar_monto_a = fields.Float('Monto Tramo 1 AF', digits='Payroll',  help="Monto Asignación Familiar por carga para Tramo 1 ($)")
    asignacion_familiar_monto_b = fields.Float('Monto Tramo 2 AF', digits='Payroll',  help="Monto Asignación Familiar por carga para Tramo 2 ($)")
    asignacion_familiar_monto_c = fields.Float('Monto Tramo 3 AF', digits='Payroll',  help="Monto Asignación Familiar por carga para Tramo 3 ($)")

    # Seguro Cesantía
    contrato_plazo_fijo_empleador = fields.Float('SC Tasa Fijo Empleador (%)', digits='Payroll Rate',  help="Tasa Seguro Cesantía Contrato Plazo Fijo (Aporte Empleador %)")
    contrato_plazo_fijo_trabajador = fields.Float('SC Tasa Fijo Trabajador (%)', digits='Payroll Rate',  help="Tasa Seguro Cesantía Contrato Plazo Fijo (Aporte Trabajador %)") # Usually 0
    contrato_plazo_indefinido_empleador = fields.Float('SC Tasa Indef. Empleador (%)', digits='Payroll Rate',  help="Tasa Seguro Cesantía Contrato Plazo Indefinido < 11 años (Aporte Empleador %)")
    contrato_plazo_indefinido_trabajador = fields.Float('SC Tasa Indef. Trabajador (%)', digits='Payroll Rate',  help="Tasa Seguro Cesantía Contrato Plazo Indefinido < 11 años (Aporte Trabajador %)")
    contrato_plazo_indefinido_empleador_otro = fields.Float('SC Tasa Indef. 11+ Empleador (%)', digits='Payroll Rate',  help="Tasa Seguro Cesantía Contrato Plazo Indefinido 11+ años (Aporte Empleador %)")
    contrato_plazo_indefinido_trabajador_otro = fields.Float('SC Tasa Indef. 11+ Trabajador (%)', digits='Payroll Rate',  help="Tasa Seguro Cesantía Contrato Plazo Indefinido 11+ años (Aporte Trabajador %)") # Usually same as < 11

    # Otros Legales
    caja_compensacion = fields.Float('Tasa Base CCAF (%)', digits='Payroll Rate',  help="Tasa base de cotización para CCAF (%)")
    fonasa = fields.Float('Tasa FONASA (%)', digits='Payroll Rate',  help="Tasa de cotización obligatoria para FONASA (%)")
    mutual_seguridad = fields.Float('Tasa Base Mutual (%)', digits='Payroll Rate',  help="Tasa base Ley Accidentes del Trabajo (Mutualidad %)")
    isl = fields.Float('Tasa Base ISL (%)', digits='Payroll Rate',  help="Tasa base Ley Accidentes del Trabajo (ISL %)")
    # pensiones_ips = fields.Float('Pensiones IPS (%)', digits='Payroll Rate', , help="Tasa antigua previsión IPS (%)") # Less common now

    # Sueldo Mínimo
    sueldo_minimo = fields.Float('Sueldo Mínimo General', digits='Payroll',  help="Sueldo Mínimo Mensual para trabajadores dependientes e independientes ($)")
    sueldo_minimo_otro = fields.Float('Sueldo Mínimo (<18/>65)', digits='Payroll',  help="Sueldo Mínimo para menores de 18 y mayores de 65 años ($)")

    # Tasas AFP
    tasa_afp_capital = fields.Float('Tasa AFP Capital (%)', digits='Payroll Rate', )
    tasa_afp_cuprum = fields.Float('Tasa AFP Cuprum (%)', digits='Payroll Rate', )
    tasa_afp_habitat = fields.Float('Tasa AFP Habitat (%)', digits='Payroll Rate', )
    tasa_afp_modelo = fields.Float('Tasa AFP Modelo (%)', digits='Payroll Rate', )
    tasa_afp_planvital = fields.Float('Tasa AFP PlanVital (%)', digits='Payroll Rate', )
    tasa_afp_provida = fields.Float('Tasa AFP ProVida (%)', digits='Payroll Rate', )
    tasa_afp_uno = fields.Float('Tasa AFP Uno (%)', digits='Payroll Rate', ) # Added readonly

    # Tasas SIS (Seguro Invalidez y Sobrevivencia)
    tasa_sis_capital = fields.Float('Tasa SIS Capital (%)', digits='Payroll Rate', )
    tasa_sis_cuprum = fields.Float('Tasa SIS Cuprum (%)', digits='Payroll Rate', )
    tasa_sis_habitat = fields.Float('Tasa SIS Habitat (%)', digits='Payroll Rate', )
    tasa_sis_modelo = fields.Float('Tasa SIS Modelo (%)', digits='Payroll Rate', ) # Added readonly
    tasa_sis_planvital = fields.Float('Tasa SIS PlanVital (%)', digits='Payroll Rate', )
    tasa_sis_provida = fields.Float('Tasa SIS ProVida (%)', digits='Payroll Rate', )
    tasa_sis_uno = fields.Float('Tasa SIS Uno (%)', digits='Payroll Rate', ) # Added readonly

    # Tasas Independientes (Suma AFP + SIS)
    tasa_independiente_capital = fields.Float('Tasa Indep. Capital (%)', digits='Payroll Rate', )
    tasa_independiente_cuprum = fields.Float('Tasa Indep. Cuprum (%)', digits='Payroll Rate', )
    tasa_independiente_habitat = fields.Float('Tasa Indep. Habitat (%)', digits='Payroll Rate', )
    tasa_independiente_modelo = fields.Float('Tasa Indep. Modelo (%)', digits='Payroll Rate', ) # Added readonly
    tasa_independiente_planvital = fields.Float('Tasa Indep. PlanVital (%)', digits='Payroll Rate', )
    tasa_independiente_provida = fields.Float('Tasa Indep. ProVida (%)', digits='Payroll Rate', )
    tasa_independiente_uno = fields.Float('Tasa Indep. Uno (%)', digits='Payroll Rate', ) # Added readonly

    # Topes Imponibles y Ahorro
    tope_anual_apv = fields.Float('Tope Anual APV (UF)', digits='Payroll Rate',  help="Tope Anual Ahorro Previsional Voluntario (UF)")
    tope_mensual_apv = fields.Float('Tope Mensual APV (UF)', digits='Payroll Rate',  help="Tope Mensual Ahorro Previsional Voluntario (UF)")
    tope_imponible_afp = fields.Float('Tope Imponible AFP/IPS (UF)', digits='Payroll Rate',  help="Tope Imponible Mensual para cotizaciones de AFP e IPS (UF)")
    tope_imponible_ips = fields.Float('Tope Imponible IPS (UF)', digits='Payroll Rate',  help="Tope Imponible Mensual para cotizaciones IPS (UF)") # Often same as AFP
    tope_imponible_salud = fields.Float('Tope Imponible Salud (UF)', digits='Payroll Rate',  help="Tope Imponible Mensual para cotizaciones de Salud (UF)")
    tope_imponible_seguro_cesantia = fields.Float('Tope Imponible SC (UF)', digits='Payroll Rate',  help="Tope Imponible Mensual para Seguro de Cesantía (UF)")
    deposito_convenido = fields.Float('Tope Depósito Convenido (UF)', digits='Payroll Rate',  help="Tope Anual para Depósitos Convenidos (UF)")

    # Valores Monetarios
    uf = fields.Float('Valor UF (Fin de Mes)', digits=(16, 2),   help="Valor de la Unidad de Fomento al último día del mes ($)")
    utm = fields.Float('Valor UTM (Mes)', digits='Payroll', required=True,  help="Valor de la Unidad Tributaria Mensual para el mes ($)")
    uta = fields.Float('Valor UTA (Año)', digits='Payroll',  help="Valor de la Unidad Tributaria Anual ($)")
    uf_otros = fields.Float('UF Otros', digits='Payroll Rate',  help="UF Seguro Complementario") # Not standard Previred, maybe remove?
    ipc = fields.Float('Variación IPC Mensual (%)', digits='Payroll Rate', required=False,  help="Índice de Precios al Consumidor (Variación % mensual)") # Made not required

    # Instituciones por defecto (pueden ser configuradas en la Cia)
    mutualidad_id = fields.Many2one('hr.mutual', 'Mutualidad Compañía',  help="Mutualidad a la que está afiliada la empresa")
    ccaf_id = fields.Many2one('hr.ccaf', 'CCAF Compañía',  help="CCAF a la que está afiliada la empresa")

    # Configuración Adicional (podría ir en res.config.settings)
    gratificacion_legal = fields.Boolean('Gratificación L. Manual', ) # Moved to contract
    mutual_seguridad_bool = fields.Boolean('Empresa Afiliada a Mutual', default=True,  help="Indica si la empresa está afiliada a una Mutual (vs ISL)")

    gratificacion_legal = fields.Boolean(
        string="Activar Gratificación Legal Manual",
        
        help="Permite usar gratificación legal en vez de regla estándar. Se puede condicionar en reglas salariales."
    )

    tope_imponible_ips = fields.Float(
        string="Tope Imponible IPS (UF)",
        digits='Payroll Rate',
        
        help="Usualmente igual al tope de AFP, salvo casos especiales"
    )

    pensiones_ips = fields.Boolean(
        string="Empresa tiene cotizantes en IPS",
        default=False,
        
        help="Activa reglas especiales si la empresa tiene empleados cotizando en IPS"
    )


    # --- Constraints ---
    _sql_constraints = [
        ('month_year_uniq', 'unique (month, year)', 'Ya existen indicadores para este Mes y Año!'),
    ]

    # --- Computed Fields ---
    @api.depends('month', 'year')
    def _compute_name(self):
        month_map = dict(MONTH_LIST)
        for record in self:
            month_name = month_map.get(record.month, '')
            record.name = f"{month_name} {record.year}"

    # --- Actions ---
    def action_done(self):
        self.write({'state': 'done'})
        return True

    def action_draft(self):
        self.write({'state': 'draft'})
        return True

    # --- Web Scraping ---
    def _clean_value(self, value_str):
        """ Helper to clean currency/percentage strings from Previred """
        if not value_str:
            return 0.0
        # Remove common currency symbols, thousands separators, percentage signs, normalize decimals
        cleaned = re.sub(r'[$.%\s]', '', value_str)
        cleaned = cleaned.replace(',', '.')
        # Remove potential invisible characters like ZWSP (\u200b) or others if they appear
        cleaned = re.sub(r'[\u200b-\u200d\uFEFF]', '', cleaned)
        try:
            return float(cleaned)
        except ValueError:
            _logger.warning("Could not convert value to float: '%s'", value_str)
            return 0.0

    def _divide_values(self, num_str, den_str, default=0.0):
        """ Helper to safely divide cleaned values """
        num = self._clean_value(num_str)
        den = self._clean_value(den_str)
        if den:
            return round(num / den, 2) # Round to 2 decimal places for UF conversions
        return default

    def update_document(self):
        """ Attempts to fetch and update indicators from Previred. """
        url = 'https://www.previred.com/web/previred/indicadores-previsionales'
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'} # Add a user agent

        for record in self:
            if record.state != 'draft':
                 raise UserError(_("Solo se pueden actualizar indicadores en estado Borrador."))

            try:
                _logger.info("Attempting to fetch indicators from %s", url)
                # Using requests is generally more robust than urlopen
                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
                html_doc = response.text
                soup = BeautifulSoup(html_doc, 'html.parser')
                tables = soup.find_all("table", class_="tableizer-table") # Target specific table class if possible

                if not tables or len(tables) < 9: # Check if enough tables were found
                    _logger.error("Could not find expected tables on Previred page structure.")
                    raise UserError(_("No se pudo encontrar la estructura esperada en la página de Previred. La página puede haber cambiado."))

                # --- Extracting Data (Indices based on observed structure - HIGHLY FRAGILE) ---
                # It's much better to use more specific selectors (ids, classes, text content) if available.
                # Assuming indices from original code, but adding checks.
                try:
                    # Table 0: UF, UTM, UTA
                    values_t0 = tables[0].find_all('strong')
                    record.uf = self._clean_value(values_t0[1].get_text() if len(values_t0) > 1 else '0')
                    record.utm = self._clean_value(values_t0[3].get_text() if len(values_t0) > 3 else '0')
                    record.uta = self._clean_value(values_t0[4].get_text() if len(values_t0) > 4 else '0')

                    # Table 1: Topes Imponibles (Indices might be wrong, original had letters[2]?)
                    # Let's assume tables[1] holds these based on common layout
                    values_t1 = tables[1].find_all('strong')
                    uf_val = record.uf # Use the already parsed UF value
                    if uf_val > 0:
                         # Find text like "UF" and get sibling value
                        record.tope_imponible_afp = self._clean_value(values_t1[1].get_text() if len(values_t1) > 1 else '0') / uf_val
                        # record.tope_imponible_ips = self._clean_value(values_t1[2].get_text() if len(values_t1) > 2 else '0') / uf_val # Often same as AFP
                        record.tope_imponible_seguro_cesantia = self._clean_value(values_t1[2].get_text() if len(values_t1) > 2 else '0') / uf_val # Index adjusted assuming 3rd strong tag is SC
                        record.tope_imponible_salud = self._clean_value(values_t1[3].get_text() if len(values_t1) > 3 else '0') / uf_val # Index adjusted assuming 4th strong tag is Salud
                    else:
                         _logger.warning("UF value is zero, cannot calculate UF-based topes.")
                         record.tope_imponible_afp = 0.0
                         record.tope_imponible_seguro_cesantia = 0.0
                         record.tope_imponible_salud = 0.0


                    # Table 2: Rentas Mínimas (Original used letters[3])
                    values_t2 = tables[2].find_all('strong')
                    record.sueldo_minimo = self._clean_value(values_t2[1].get_text() if len(values_t2) > 1 else '0')
                    record.sueldo_minimo_otro = self._clean_value(values_t2[2].get_text() if len(values_t2) > 2 else '0')

                    # Table 3: APV (Original used letters[4])
                    values_t3 = tables[3].find_all('strong')
                    if uf_val > 0:
                        record.tope_mensual_apv = self._clean_value(values_t3[2].get_text() if len(values_t3) > 2 else '0') / uf_val
                        record.tope_anual_apv = self._clean_value(values_t3[1].get_text() if len(values_t3) > 1 else '0') / uf_val
                    else:
                        record.tope_mensual_apv = 0.0
                        record.tope_anual_apv = 0.0


                    # Table 4: Depósito Convenido (Original used letters[5])
                    values_t4 = tables[4].find_all('strong')
                    if uf_val > 0:
                        record.deposito_convenido = self._clean_value(values_t4[1].get_text() if len(values_t4) > 1 else '0') / uf_val
                    else:
                        record.deposito_convenido = 0.0


                    # Table 5: Seguro Cesantía Tasas (Original used letters[6])
                    values_t5 = tables[5].find_all('strong')
                    record.contrato_plazo_indefinido_empleador = self._clean_value(values_t5[5].get_text() if len(values_t5) > 5 else '0')
                    record.contrato_plazo_indefinido_trabajador = self._clean_value(values_t5[6].get_text() if len(values_t5) > 6 else '0')
                    record.contrato_plazo_fijo_empleador = self._clean_value(values_t5[7].get_text() if len(values_t5) > 7 else '0')
                    record.contrato_plazo_indefinido_empleador_otro = self._clean_value(values_t5[9].get_text() if len(values_t5) > 9 else '0')

                    # Table 6: Tasas AFP / SIS / Indep (Original used letters[7])
                    values_t6 = tables[6].find_all('strong')
                    # Example for Capital (Repeat for others, adjusting indices carefully!)
                    record.tasa_afp_capital = self._clean_value(values_t6[8].get_text() if len(values_t6) > 8 else '0')
                    record.tasa_sis_capital = self._clean_value(values_t6[9].get_text() if len(values_t6) > 9 else '0')
                    record.tasa_independiente_capital = self._clean_value(values_t6[10].get_text() if len(values_t6) > 10 else '0')

                    record.tasa_afp_cuprum = self._clean_value(values_t6[11].get_text() if len(values_t6) > 11 else '0')
                    record.tasa_sis_cuprum = self._clean_value(values_t6[12].get_text() if len(values_t6) > 12 else '0')
                    record.tasa_independiente_cuprum = self._clean_value(values_t6[13].get_text() if len(values_t6) > 13 else '0')

                    record.tasa_afp_habitat = self._clean_value(values_t6[14].get_text() if len(values_t6) > 14 else '0')
                    record.tasa_sis_habitat = self._clean_value(values_t6[15].get_text() if len(values_t6) > 15 else '0')
                    record.tasa_independiente_habitat = self._clean_value(values_t6[16].get_text() if len(values_t6) > 16 else '0')

                    record.tasa_afp_planvital = self._clean_value(values_t6[17].get_text() if len(values_t6) > 17 else '0')
                    record.tasa_sis_planvital = self._clean_value(values_t6[18].get_text() if len(values_t6) > 18 else '0')
                    record.tasa_independiente_planvital = self._clean_value(values_t6[19].get_text() if len(values_t6) > 19 else '0')

                    record.tasa_afp_provida = self._clean_value(values_t6[20].get_text() if len(values_t6) > 20 else '0')
                    record.tasa_sis_provida = self._clean_value(values_t6[21].get_text() if len(values_t6) > 21 else '0')
                    record.tasa_independiente_provida = self._clean_value(values_t6[22].get_text() if len(values_t6) > 22 else '0')

                    record.tasa_afp_modelo = self._clean_value(values_t6[23].get_text() if len(values_t6) > 23 else '0')
                    record.tasa_sis_modelo = self._clean_value(values_t6[24].get_text() if len(values_t6) > 24 else '0')
                    record.tasa_independiente_modelo = self._clean_value(values_t6[25].get_text() if len(values_t6) > 25 else '0')

                    # Uno might be at different indices if added later
                    # Assuming Uno is now included and indices shifted or reused (e.g., using Modelo's index if not found)
                    record.tasa_afp_uno = self._clean_value(values_t6[26].get_text() if len(values_t6) > 26 else values_t6[23].get_text() if len(values_t6) > 23 else '0') # Fallback logic
                    record.tasa_sis_uno = self._clean_value(values_t6[27].get_text() if len(values_t6) > 27 else values_t6[24].get_text() if len(values_t6) > 24 else '0') # Fallback logic
                    record.tasa_independiente_uno = self._clean_value(values_t6[28].get_text() if len(values_t6) > 28 else values_t6[25].get_text() if len(values_t6) > 25 else '0') # Fallback logic


                    # Table 7: Asignación Familiar (Original used letters[8])
                    values_t7 = tables[7].find_all('strong')
                    # Extract amounts
                    record.asignacion_familiar_monto_a = self._clean_value(values_t7[4].get_text() if len(values_t7) > 4 else '0')
                    record.asignacion_familiar_monto_b = self._clean_value(values_t7[6].get_text() if len(values_t7) > 6 else '0')
                    record.asignacion_familiar_monto_c = self._clean_value(values_t7[8].get_text() if len(values_t7) > 8 else '0')
                    # Extract topes (requires parsing text like "$ hasta $XXX.XXX")
                    record.asignacion_familiar_primer = self._clean_value(re.search(r'\d[\d.]*', values_t7[5].get_text().replace('.','')).group() if len(values_t7) > 5 and re.search(r'\d[\d.]*', values_t7[5].get_text().replace('.','')) else '0')
                    record.asignacion_familiar_segundo = self._clean_value(re.search(r'\d[\d.]*', values_t7[7].get_text().replace('.','')).group() if len(values_t7) > 7 and re.search(r'\d[\d.]*', values_t7[7].get_text().replace('.','')) else '0')
                    record.asignacion_familiar_tercer = self._clean_value(re.search(r'\d[\d.]*', values_t7[9].get_text().replace('.','')).group() if len(values_t7) > 9 and re.search(r'\d[\d.]*', values_t7[9].get_text().replace('.','')) else '0')


                    _logger.info("Successfully updated indicators for %s", record.name)

                except (IndexError, AttributeError, TypeError, ValueError) as e:
                    _logger.error("Error parsing Previred data for %s: %s. Structure might have changed.", record.name, e)
                    raise UserError(_("Error al procesar los datos de Previred para {}. La estructura de la página puede haber cambiado. Verifique manualmente.").format(record.name))

            except (requests.exceptions.RequestException, URLError) as e:
                _logger.error("Network error fetching Previred indicators: %s", e)
                raise UserError(_("Error de red al obtener indicadores de Previred: %s") % e)
            except Exception as e:
                _logger.exception("Unexpected error updating indicators for %s:", record.name)
                raise UserError(_("Error inesperado al actualizar indicadores para {}: {}").format(record.name, e))

        return True # Indicate success or partial success if needed
    
    def action_parse_pdf(self):
        if not self.pdf_file:
            raise UserError("Debes adjuntar un archivo PDF.")

        try:
            decoded = base64.b64decode(self.pdf_file)
            reader = PdfReader(io.BytesIO(decoded))
            text = "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
            self._parse_values_from_text(text)
        except Exception as e:
            raise UserError("Error al procesar el PDF: %s" % str(e))



    def _parse_values_from_text(self, text):
        """Extrae valores numéricos del texto del PDF y los asigna a los campos del modelo."""
        import re
        import unicodedata

        def normalize(texto):
            return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")

        try:
            lines = normalize(text).splitlines()

            mapping = {
                'UF': 'uf',
                'UTM': 'utm',
                'Tope Imponible AFP': 'tope_afp',
                'Tope Imponible Salud': 'tope_salud',
                'FONASA': 'fonasa',
                'APV Voluntario': 'tope_apv',
                'Seguro Cesantía contrato indefinido trabajador': 'contrato_plazo_indefinido_trabajador',
                'Seguro Cesantía contrato indefinido empleador': 'contrato_plazo_indefinido_empleador',
                'Asignación Familiar Tramo A': 'asignacion_familiar_monto_a',
                'Asignación Familiar Tramo B': 'asignacion_familiar_monto_b',
                'Asignación Familiar Tramo C': 'asignacion_familiar_monto_c',
                'Asignación Familiar Tramo D': 'asignacion_familiar_monto_d',
            }

            for line in lines:
                for label, field in mapping.items():
                    if label.lower() in line.lower():
                        match = re.search(r'([\d\.]+)', line.replace(".", "").replace(",", "."))
                        if match:
                            value = float(match.group(1))
                            setattr(self, field, value)
        except Exception as e:
            raise ValueError(f"Error al analizar el texto: {e}")
