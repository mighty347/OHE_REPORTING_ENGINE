import pandas as pd
import json


class ExcelGenerator:
    def __init__(self, payload):
        self.payload = payload

    def generate_excel(self, output_file: str) -> str:
        exported_data = []
        s_no = 1

        blocks = self.payload.get("Blocks", []) or self.payload.get("Towers", [])
        asset_details = self.payload.get("AssetDetails", {})

        # Process Blocks or Towers structure
        if blocks:
            for block in blocks:
                mast_name = block.get("ObjectStructureName") or block.get("name") or ""
                for annotation in block.get("Annotations", []) or []:
                    images = annotation.get("Images", []) or []
                    if not images:
                        continue

                    visual_img_url = ""
                    thermal_img_url = ""
                    latitude = None
                    longitude = None

                    for image in images:
                        if not isinstance(image, dict):
                            continue
                        img_url = image.get("ImageUrl", "")
                        meta = image.get("MetaData") or {}
                        if isinstance(meta, dict):
                            if meta.get("Latitude") is not None:
                                latitude = meta.get("Latitude")
                            if meta.get("Longitude") is not None:
                                longitude = meta.get("Longitude")

                        if not img_url:
                            continue

                        if "_T.JPG" in img_url.upper():
                            thermal_img_url = img_url
                        elif "_V.JPG" in img_url.upper() or "RGB" in img_url.upper():
                            visual_img_url = img_url

                    report_cols_v = annotation.get("ReportColumnsVisual") or {}
                    report_cols_t = annotation.get("ReportColumnsThermal") or {}

                    component = (
                        annotation.get("component")
                        or report_cols_v.get("Component  Name")
                        or report_cols_v.get("Component Name")
                        or report_cols_v.get("Component")
                        or report_cols_t.get("Component  Name")
                        or report_cols_t.get("Component Name")
                        or report_cols_t.get("Component")
                        or annotation.get("parent_name")
                        or ""
                    )

                    sub_component = (
                        annotation.get("sub_component")
                        or report_cols_v.get("Subcomponent Name")
                        or report_cols_v.get("Sub-Component")
                        or report_cols_v.get("Sub-component")
                        or report_cols_v.get("Subcomponent")
                        or report_cols_t.get("Subcomponent Name")
                        or report_cols_t.get("Sub-Component")
                        or report_cols_t.get("Sub-component")
                        or report_cols_t.get("Subcomponent")
                        or annotation.get("member_name")
                        or ""
                    )

                    defect = annotation.get("annomaly_name") or annotation.get("Anomaly") or ""

                    exported_data.append({
                        "S.No.": s_no,
                        "Mast Name": mast_name,
                        "Defect": defect,
                        "Component": component,
                        "Sub-Component": sub_component,
                        "Latitude": latitude,
                        "Longitude": longitude,
                        "Visual Image URL": visual_img_url,
                        "Thermal Image URL": thermal_img_url
                    })
                    s_no += 1

        # Process AssetDetails structure
        elif isinstance(asset_details, dict) and asset_details:
            for section_name, items in asset_details.items():
                if not isinstance(items, list):
                    continue
                for item in items:
                    if not isinstance(item, dict):
                        continue

                    mast_name = item.get("AssetName") or item.get("ObjectStructureName") or ""
                    defect = item.get("Anomaly") or item.get("annomaly_name") or ""

                    report_cols_v = item.get("ReportColumnsVisual") or {}
                    report_cols_t = item.get("ReportColumnsThermal") or {}

                    component = (
                        report_cols_v.get("Component  Name")
                        or report_cols_v.get("Component Name")
                        or report_cols_v.get("Component")
                        or report_cols_t.get("Component  Name")
                        or report_cols_t.get("Component Name")
                        or report_cols_t.get("Component")
                        or item.get("Component")
                        or item.get("parent_name")
                        or ""
                    )

                    sub_component = (
                        report_cols_v.get("Subcomponent Name")
                        or report_cols_v.get("Sub-Component")
                        or report_cols_v.get("Sub-component")
                        or report_cols_v.get("Subcomponent")
                        or report_cols_t.get("Subcomponent Name")
                        or report_cols_t.get("Sub-Component")
                        or report_cols_t.get("Sub-component")
                        or report_cols_t.get("Subcomponent")
                        or item.get("Sub-Component")
                        or item.get("member_name")
                        or ""
                    )

                    visual_img_url = item.get("ImageVisualUrl") or ""
                    thermal_img_url = item.get("ImageThermalUrl") or ""

                    latitude = None
                    longitude = None

                    img_payload_v = item.get("ImageVisualPayload") or {}
                    if isinstance(img_payload_v, dict):
                        latitude = img_payload_v.get("lat")
                        longitude = img_payload_v.get("lng")

                    if latitude is None or longitude is None:
                        img_payload_t = item.get("ImageThermalPayload") or {}
                        if isinstance(img_payload_t, dict):
                            latitude = latitude if latitude is not None else img_payload_t.get("lat")
                            longitude = longitude if longitude is not None else img_payload_t.get("lng")

                    exported_data.append({
                        "S.No.": s_no,
                        "Mast Name": mast_name,
                        "Defect": defect,
                        "Component": component,
                        "Sub-Component": sub_component,
                        "Latitude": latitude,
                        "Longitude": longitude,
                        "Visual Image URL": visual_img_url,
                        "Thermal Image URL": thermal_img_url
                    })
                    s_no += 1

        # -------- Handle empty export --------
        if not exported_data:
            exported_data.append({
                "S.No.": "",
                "Mast Name": "",
                "Defect": "",
                "Component": "",
                "Sub-Component": "",
                "Latitude": "",
                "Longitude": "",
                "Visual Image URL": "",
                "Thermal Image URL": ""
            })

        df = pd.DataFrame(exported_data)

        # -------- Drop columns where no values exist --------
        cols_to_drop = []
        for col in df.columns:
            series_str = df[col].fillna("").astype(str).str.strip()
            if (series_str.isin(["", "None", "nan", "NaN", "<NA>"])).all():
                cols_to_drop.append(col)

        if cols_to_drop:
            df.drop(columns=cols_to_drop, inplace=True)

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
    with open("current_payload_new.json", "r") as f:
        payload = json.load(f)

    excel_generator = ExcelGenerator(payload)
    excel_file = excel_generator.generate_excel("output.xlsx")
    print("Excel generated:", excel_file)
