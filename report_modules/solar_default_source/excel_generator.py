import pandas as pd
import json


class ExcelGenerator:
    def __init__(self, payload):
        self.payload = payload

    def generate_excel(self, output_file: str) -> str:
        exported_data = []
        s_no = 1

        for block in self.payload.get("Blocks", []):
            for annotation in block.get("Annotations", []):

                images = annotation.get("Images", [])
                if not images:
                    continue

                # -------- Parse member_path --------
                member_path = annotation.get("member_path", "") or ""
                segments = [p.strip() for p in member_path.split("/") if p.strip()]

                mp = {}
                for seg in segments:
                    if ":" in seg:
                        k, v = seg.split(":", 1)
                        mp[k.strip()] = v.strip()

                # -------- Image handling (3 cases) --------
                visual_img_url = ""
                thermal_img_url = ""
                capture_date = ""
                annotation_json = {}

                for image in images:
                    img_url = image.get("ImageUrl", "")
                    capture_date = image.get("ImageDate", capture_date)
                    Latitude = image.get('MetaData').get("Latitude")
                    Longitude = image.get('MetaData').get('Longitude')

                    if not img_url:
                        continue

                    if "_T.JPG" in img_url:
                        thermal_img_url = img_url
                        annotation_json = image.get("annotation_json") or {}
                        
                    elif "_V.JPG" in img_url or "RGB" in img_url:
                        visual_img_url = img_url

                

                exported_data.append({
                    "S.No.": s_no,
                    "Image Type": block.get("ObjectStructureName", ""),
                    "Block No.": mp.get("Block", ""),
                    "String No.": mp.get("String", ""),
                    "Row No.": mp.get("Row", ""),
                    "Table No.": mp.get("Table", ""),
                    "Module No.": mp.get("Module", ""),
                    "Defect": annotation.get("annomaly_name", ""),
                    "Severity": annotation.get("severity", ""),
                    "Average Temp.": annotation_json.get("AvgTemp", ""),
                    "Delta Temp.": annotation_json.get("DeltaTemp", ""),
                    "Min Temp.": annotation_json.get("MinTemp", ""),
                    "Max Temp.": annotation_json.get("MaxTemp", ""),
                    "Latitude" : Latitude,
                    "Longitude" : Longitude,
                    "Thermal Image Url": thermal_img_url,
                    "Visual Image Url": visual_img_url,
                    "Capture Date": capture_date,
                    "Remarks/Comment": annotation.get("remarks", "")
                })

                s_no += 1

        # -------- Handle empty export --------
        if not exported_data:
            exported_data.append({})

        df = pd.DataFrame(exported_data)
        
        temp_columns = [
            "Average Temp.",
            "Delta Temp.",
            "Min Temp.",
            "Max Temp."
        ]

        # Check if all temperature columns are fully empty
        if all(
            col in df.columns and df[col].replace("", pd.NA).isna().all()
            for col in temp_columns
        ):
            df.drop(columns=temp_columns, inplace=True)

        # -------- Drop empty image columns --------
        if "Thermal Image Url" in df.columns and df["Thermal Image Url"].replace("", pd.NA).isna().all():
            df.drop(columns=["Thermal Image Url"], inplace=True)

        if "Visual Image Url" in df.columns and df["Visual Image Url"].replace("", pd.NA).isna().all():
            df.drop(columns=["Visual Image Url"], inplace=True)

        # -------- Write Excel --------
        with pd.ExcelWriter(output_file, engine="xlsxwriter") as writer:
            df.to_excel(writer, sheet_name="Sheet1", index=False)
            worksheet = writer.sheets["Sheet1"]

            # Auto-adjust column width
            for col_num, col_name in enumerate(df.columns):
                max_length = max(
                    df[col_name].astype(str).map(len).max(),
                    len(col_name)
                ) + 2
                worksheet.set_column(col_num, col_num, max_length)

        return output_file


if __name__ == "__main__":
    with open("current_payload.json", "r") as f:
        payload = json.load(f)

    excel_generator = ExcelGenerator(payload)
    excel_file = excel_generator.generate_excel("output.xlsx")
    print("Excel generated:", excel_file)
