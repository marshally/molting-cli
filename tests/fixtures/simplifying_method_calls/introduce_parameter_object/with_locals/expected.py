"""Example code for introduce parameter object with local variables."""


class Report:
    def __init__(self, title, data):
        self.title = title
        self.data = data


class ReportConfig:
    def __init__(self, start_row, end_row, include_headers, include_totals):
        self.start_row = start_row
        self.end_row = end_row
        self.include_headers = include_headers
        self.include_totals = include_totals


class ReportGenerator:
    def generate_summary(self, config, data_source):
        """Generate a report summary using a parameter object."""
        # Store parameter object fields in local variables for additional processing
        first_row = config.start_row
        last_row = config.end_row
        show_headers = config.include_headers
        show_totals = config.include_totals
        source = data_source

        # Additional local processing
        row_count = last_row - first_row + 1
        has_header_row = show_headers
        needs_totals_row = show_totals

        print(f"Generating report: rows {first_row}-{last_row} ({row_count} rows)")
        print(f"Headers: {has_header_row}, Totals: {needs_totals_row}")

        # Call helper with parameter object
        return self._format_report(config, source)

    def _format_report(self, config, source):
        """Format the report based on configuration."""
        data = source.get_data(config.start_row, config.end_row)
        if config.include_headers:
            data = ["Header"] + data
        if config.include_totals:
            data.append("Total: " + str(sum(int(x) for x in data if x.isdigit())))
        return "\n".join(data)
