import pandas as pd

class ExcelGenerator():
    payload: dict

    def __init__(self, payload):
        self.payload = payload


    def generate_excel(self, output_file:str) -> str:
        """
        Utility funciton to generate excel sheet.

        Args:
            excel_data (list): list of dict 
                                    [
                                        {'col_1': value1, 'col_2': value2},
                                        {'col_1': value3, 'col_2': value4},
                                        ...
                                    ]

            output_file (str): path where excel file needs to be stored.

        Returns:
            str: Generated excel file path.
        """

        exported_data = []

        s_no = 1

        for block in self.payload.get("Blocks"):
            for image in block.get("Images"):
                if image.get("Annotations") :
                    for annotation in image.get("Annotations"):
                        
                        member_path = annotation.get("member_path","") or ""
                        segments = [p.strip() for p in member_path.split("/") if p.strip()]

                        mp = {}
                        for seg in segments:
                            if ":" in seg:
                                k, v = seg.split(":", 1)
                                mp[k.strip()] = v.strip()
                        
                        exported_data.append({  "S.No.": s_no,
                                                "Image Type": block.get("ObjectStructureName"),
                                                "Block No." : mp.get("Block", ""),
                                                "String No.": mp.get("String", ""),
                                                "Row No.": mp.get("Row", ""),
                                                "Table No.": mp.get("Table", ""),
                                                "Module No.": mp.get("Module", ""),
                                                # "Location": annotation.get("member_path"),
                                                "Defect": annotation.get("annomaly_name"),
                                                "Severity": annotation.get("severity"),
                                                "Average Temp.": (annotation.get("annotation_json") or {}).get("AvgTemp", ""),
                                                "Delta Temp." : (annotation.get("annotation_json") or {}).get("DeltaTemp", ""),
                                                "Min Temp.": (annotation.get("annotation_json") or {}).get("MinTemp", ""),
                                                "Max Temp.": (annotation.get("annotation_json") or {}).get("MaxTemp", ""),
                                                "Image Url": image.get("ImageUrl"),
                                                "Capture Date" : image.get("ImageDate"),
                                                "Remarks/Comment": annotation.get("remarks", "")
        
                                            })
                        s_no += 1

        if not exported_data:
            exported_data.append({
                                    "S.No.": "",
                                    "Image Type": "",
                                    "Block No." : "",
                                    "String No.": "",
                                    "Row No.": "",
                                    "Table No.": "",
                                    "Module No.": "",
                                    # "Location": "",
                                    "Defect": "",
                                    "Severity": "",
                                    "Average Temp.": "",
                                    "Delta Temp.": "",
                                    "Min Temp.": "",
                                    "Max Temp.": "",
                                    "Image Url": "",
                                    "Capture Date" : "",
                                    "Remarks/Comment": ""
                                })



        df = pd.DataFrame(exported_data)
        # df.to_excel(output_file, index=False)

        with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Sheet1', index=False)
            # Get the xlsxwriter workbook and worksheet objects
            workbook = writer.book
            worksheet = writer.sheets['Sheet1']


             # Auto-adjust column width
            for col_num, col_name in enumerate(df.columns):
                max_length = max(
                                    df[col_name].astype(str).map(len).max(),  # Maximum length of column data
                                    len(col_name)  # Length of column header
                                ) + 2  # Add extra padding for better appearance
                
                worksheet.set_column(col_num, col_num, max_length)

                
            # Define a cell format with the hyperlink format
            # hyperlink_format = workbook.add_format({'color': 'blue', 'underline': 1})

            # num_rows = len(df)

            # Iterate through each row and add hyperlinks to the specified column
            # for row_num in range(1, num_rows + 1):
            #     cell_value = df.at[row_num - 1, "File Location / Image Link"]
            #     worksheet.write_url(row_num, df.columns.get_loc("File Location / Image Link"), cell_value, hyperlink_format)

        return output_file
    
