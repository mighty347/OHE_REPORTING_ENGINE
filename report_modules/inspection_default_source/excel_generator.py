import pandas as pd
import json


class ExcelGenerator:
    def __init__(self, payload):
        self.payload = payload

    def generate_excel(self, output_file: str) -> str:
        bhi = self.payload.get("bhi", "")
        spans = self.payload.get("spans", [])

        # Proper writer usage - open ONCE outside the loop
        writer = pd.ExcelWriter(output_file, engine="xlsxwriter")
        workbook = writer.book
        worksheet = workbook.add_worksheet("BHI Report")

        # Formats
        header_format = workbook.add_format({
            'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#E0E0E0', 'text_wrap': True
        })

        cell_format = workbook.add_format({
            'border': 1, 'text_wrap': True, 'valign': 'vcenter', 'align': 'center'
        })

        num_format = workbook.add_format({
            'align': 'center', 'border': 1, 'valign': 'vcenter'
        })

        section_format = workbook.add_format({
            'bold': True, 'align': 'left', 'valign': 'vcenter', 'border': 1, 'bg_color': '#F5F5F5'
        })

        span_format = workbook.add_format({
            'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#CCCCCC'
        })

        # Column widths
        worksheet.set_column('A:I', 18)

        # Headers - written ONCE
        headers = ["Sl. No.", "Bridge components", "Component Name",
                   "Distress Type", "Condition State No.", "Wj", "CSj", "CIi", "BHI"]

        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)

        current_row = 1

        for span in spans:
            sections = span.get("sections") or []
            span_name = span.get("span_name", "Unknown Span")
            span_bhi = span.get("bhi", "")

            span_start_row = current_row

            # Optional: Span Header Row
            if len(spans) > 1:
                worksheet.merge_range(current_row, 0, current_row, 7, f"Span: {span_name}", span_format)
                current_row += 1

            for section in sections:
                section_id = section.get("section_id", "")
                section_name = section.get("section_name", "")
                group_score = section.get("group_score", "")
                components = section.get("components") or []

                # Section row
                worksheet.write(current_row, 0, section_id, section_format)
                worksheet.write(current_row, 1, section_name, section_format)

                for i in range(2, 9):
                    worksheet.write(current_row, i, "", section_format)

                section_start_row = current_row
                current_row += 1

                for comp in components:
                    comp_id = comp.get("sl_no", "")
                    comp_name = comp.get("component_name", "")
                    wj = comp.get("weight_wj", "")
                    csj = comp.get("cs_j", "")
                    ci = comp.get("ci", "")

                    distresses = comp.get("distresses") or [{
                        "asset_name": comp.get("asset_type_name", "Nil"),
                        "anomaly_name": comp.get("primary_condition", "Nil"),
                        "condition_state": comp.get("primary_condition", "I")
                    }]

                    comp_start_row = current_row
                    
                    for distress in distresses:
                        worksheet.write(current_row, 2, distress.get("asset_name", ""), cell_format)
                        worksheet.write(current_row, 3, distress.get("anomaly_name", ""), cell_format)
                        worksheet.write(current_row, 4, distress.get("condition_state", ""), num_format)
                        current_row += 1

                    if len(distresses) > 1:
                        worksheet.merge_range(comp_start_row, 0, current_row-1, 0, comp_id, cell_format)
                        worksheet.merge_range(comp_start_row, 1, current_row-1, 1, comp_name, cell_format)
                        worksheet.merge_range(comp_start_row, 5, current_row-1, 5, wj, num_format)
                        worksheet.merge_range(comp_start_row, 6, current_row-1, 6, csj, num_format)
                    else:
                        worksheet.write(comp_start_row, 0, comp_id, cell_format)
                        worksheet.write(comp_start_row, 1, comp_name, cell_format)
                        worksheet.write(comp_start_row, 5, wj, num_format)
                        worksheet.write(comp_start_row, 6, csj, num_format)

                # Merge CIi (column H = index 7)
                if current_row > section_start_row + 1:
                    worksheet.merge_range(section_start_row + 1, 7, current_row - 1, 7, group_score, num_format)

            # Merge Span-specific BHI (column I = index 8)
            if current_row > span_start_row :
                worksheet.merge_range(span_start_row, 8, current_row - 1, 8, span_bhi, num_format)

        writer.close()
        return output_file

if __name__ == "__main__":
    with open("current_payload.json", "r") as f:
        payload = json.load(f)

    excel_generator = ExcelGenerator(payload)
    excel_file = excel_generator.generate_excel("output.xlsx")
    print("Excel generated:", excel_file)
