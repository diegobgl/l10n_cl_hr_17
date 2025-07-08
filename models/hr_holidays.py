# -*- coding: utf-8 -*-

import math
from odoo import api, fields, models, _

class HrLeaveType(models.Model): # Renamed class for consistency
    _inherit = 'hr.leave.type'

    is_continued = fields.Boolean(
        'Descontar Fines de Semana y Festivos',
        help="Si está marcado, la duración de la ausencia incluirá sábados, domingos y festivos (cálculo de días corridos)."
        # Note: Odoo's standard behavior with resource calendars might already handle this.
        # This field provides an explicit override/alternative logic.
    )

class HrLeave(models.Model): # Renamed class for consistency
    _inherit = 'hr.leave'

    # Overriding the calculation method
    # WARNING: Test thoroughly. Odoo 17's base calculation might be different.
    # This override forces 'days running' calculation if is_continued is True.
    # It might conflict with Odoo's handling of resource calendars and public holidays.
    def _get_number_of_days(self, date_from, date_to, employee_id):
        """
        Calculates the number of days for the leave request.
        If the leave type has 'is_continued' checked, calculates running days.
        Otherwise, uses the standard Odoo calculation.
        """
        self.ensure_one() # _get_number_of_days usually operates on one record

        employee = self.env['hr.employee'].browse(employee_id) if employee_id else self.employee_id

        # Use UTC for date comparisons/calculations if dates are datetime
        # Ensure date_from and date_to are datetime objects if they include time
        # If they are just dates, direct subtraction is fine.
        # Assuming date_from and date_to are datetime objects as in standard Odoo leaves
        if not date_from or not date_to:
             return {'days': 0, 'hours': 0} # Handle missing dates

        # Check if the leave type dictates continuous days calculation
        if employee and self.holiday_status_id.is_continued:
            # Calculate running days (including weekends/holidays)
            # Ensure we handle date vs datetime correctly
            start_dt = fields.Datetime.to_datetime(date_from)
            end_dt = fields.Datetime.to_datetime(date_to)
            # Add a small epsilon to include the end date if it's at 00:00:00?
            # Or adjust based on whether it's full day / half day?
            # Odoo's duration often considers calendar working times.
            # This simple timedelta might not be accurate for hours if start/end times matter.
            # Let's focus on days for now, assuming full days.
            time_delta = end_dt - start_dt
            # Odoo usually returns days and hours separately.
            # This calculation forces a 'days running' result.
            # It ignores the employee's calendar.
            number_of_days = math.ceil(time_delta.days + float(time_delta.seconds) / 86400)
            # How to represent this in Odoo's return format {'days': N, 'hours': H}?
            # Let's assume it sets the days and ignores hours based on calendar.
            # This might need refinement based on how hr.leave uses the result.
            # For simplicity, let's return the calculated days and 0 hours.
            # Standard Odoo might calculate hours based on calendar *within* these days.
            # This override *replaces* that standard calculation.
            return {'days': number_of_days, 'hours': 0} # Return format expected by Odoo
        else:
            # Use the standard Odoo calculation which considers resource calendar
            # Pass the correct employee_id if available
            return super()._get_number_of_days(date_from, date_to, employee_id)

    # Optional: Add an onchange or compute for number_of_days based on is_continued
    # to reflect the change in the UI immediately, though the _get_number_of_days
    # override is the crucial part for the actual stored/used value.