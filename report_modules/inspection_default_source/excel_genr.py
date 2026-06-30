import pandas as pd
import json


class ExcelGenerator:
    def __init__(self, payload):
        self.payload = payload

    def generate_excel(self, output_file: str) -> str:
        bhi = self.payload.get("bhi", "")
        sections = self.payload.get("sections", [])
        # Prepare workbook and worksheet
        workbook = pd.ExcelWriter(output_file, engine="xlsxwriter").book
        worksheet = workbook.add_worksheet("BHI Report")

        # Define formats
        title_format = workbook.add_format({
            'bold': True, 'align': 'center', 'valign': 'vcenter', 'font_size': 14
        })
        header_format = workbook.add_format({
            'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#E0E0E0', 'text_wrap': True
        })
        cell_format = workbook.add_format({
            'align': 'left', 'valign': 'vcenter', 'border': 1, 'text_wrap': True
        })
        num_format = workbook.add_format({
            'align': 'center', 'valign': 'vcenter', 'border': 1
        })
        section_format = workbook.add_format({
            'bold': True, 'align': 'left', 'valign': 'vcenter', 'border': 1, 'bg_color': '#F5F5F5'
        })

        # Set column widths
        worksheet.set_column('A:A', 10)  # Sl. No.
        worksheet.set_column('B:B', 30)  # Bridge components
        worksheet.set_column('C:C', 30)  # Distress Type
        worksheet.set_column('D:D', 15)  # Condition State No.
        worksheet.set_column('E:E', 10)  # Wj
        worksheet.set_column('F:F', 10)  # CSj
        worksheet.set_column('G:G', 15)  # CIi
        worksheet.set_column('H:H', 15)  # BHI

        # Write Headers
        headers = ["Sl. No.", "Bridge components", "Distress Type", "Condition State No.", "Wj", "CSj", "CIi", "BHI"]
        for col, header in enumerate(headers):
            worksheet.write(1, col, header, header_format)

        current_row = 2 
        
        for section in sections:
            section_id = section.get("section_id", "")
            section_name = section.get("section_name", "")
            group_score = section.get("group_score", "")
            components = section.get("components", [])

            # Section Header Row
            worksheet.write(current_row, 0, section_id, section_format)
            worksheet.write(current_row, 1, section_name, section_format)
            for i in range(2, 6):
                worksheet.write(current_row, i, "", section_format)
            
            # Identify the range for CIi merging
            section_start_row = current_row
            current_row += 1

            for comp in components:
                comp_id = comp.get("sl_no", "")
                comp_name = comp.get("component_name", "")
                wj = comp.get("weight_wj", "")
                csj = comp.get("cs_j", "")
                ci = comp.get("ci", "")
                
                # Handle distresses (can be single "distress" or list "distresses")
                distresses = []
                
                if "distresses" in comp:
                    distresses = comp["distresses"]
                else:
                    distresses = [{"distress_type": comp.get("primary_distress", "Nil"), "condition_state": comp.get("primary_condition", "I")}]
                
                comp_start_row = current_row
                num_distresses = len(distresses)

                for distress in distresses:
                    d_type = distress.get("asset_name", "Nil")
                    c_state = distress.get("condition_state", "I")
                    worksheet.write(current_row, 2, d_type, cell_format)
                    worksheet.write(current_row, 3, c_state, num_format)
                    current_row += 1

                # Merge component-level cells if multiple distresses
                if num_distresses > 1:
                    worksheet.merge_range(comp_start_row, 0, current_row - 1, 0, comp_id, cell_format)
                    worksheet.merge_range(comp_start_row, 1, current_row - 1, 1, comp_name, cell_format)
                    worksheet.merge_range(comp_start_row, 4, current_row - 1, 4, wj, num_format)
                    worksheet.merge_range(comp_start_row, 5, current_row - 1, 5, csj, num_format)
                    
                else:
                    worksheet.write(comp_start_row, 0, comp_id, cell_format)
                    worksheet.write(comp_start_row, 1, comp_name, cell_format)
                    worksheet.write(comp_start_row, 4, wj, num_format)
                    worksheet.write(comp_start_row, 5, csj, num_format)

            # Merge CIi for the whole section (including its header row? No, usually just the component rows)
            # Based on image, CIi is merged across the component rows of the section.
            if current_row > section_start_row + 1:
                worksheet.merge_range(section_start_row + 1, 6, current_row - 1, 6, group_score, num_format)
                # Ensure the section header row has a border for CIi col too
                worksheet.write(section_start_row, 6, "", section_format)
            else:
                # If no components? (Unlikely)
                worksheet.write(section_start_row, 6, "", section_format)

        # Merge BHI for the entire table (placeholder)
        bhi_score = bhi # Could be calculated if needed
        if current_row > 2:
            worksheet.merge_range(2, 7, current_row - 1, 7, bhi_score, num_format)

        workbook.close()
        return output_file

if __name__ == "__main__":
    with open("current_payload.json", "r") as f:
        payload = json.load(f)

    excel_generator = ExcelGenerator(payload)
    excel_file = excel_generator.generate_excel("output.xlsx")
    print("Excel generated:", excel_file)
