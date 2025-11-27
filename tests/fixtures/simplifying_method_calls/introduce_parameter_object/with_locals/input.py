"""Example code for introduce parameter object with local variables."""


class Report:
    def __init__(self, title, data):
        self.title = title
        self.data = data


class ReportGenerator:
    def generate_summary(self, start_row, end_row, include_headers, include_totals, data_source):
        """Generate a report summary with parameters stored in locals."""
        # Store parameters in local variables for additional processing
        first_row = start_row
        last_row = end_row
        show_headers = include_headers
        show_totals = include_totals
        source = data_source

        # Additional local processing
        row_count = last_row - first_row + 1
        has_header_row = show_headers
        needs_totals_row = show_totals

        print(f"Generating report: rows {first_row}-{last_row} ({row_count} rows)")
        print(f"Headers: {has_header_row}, Totals: {needs_totals_row}")

        # Call helper with all the parameters
        return self._format_report(first_row, last_row, show_headers, show_totals, source)

    def _format_report(self, start, end, headers, totals, source):
        """Format the report based on configuration."""
        data = source.get_data(start, end)
        if headers:
            data = ["Header"] + data
        if totals:
            data.append("Total: " + str(sum(int(x) for x in data if x.isdigit())))
        return "\n".join(data)
