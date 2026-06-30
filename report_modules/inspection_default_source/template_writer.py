import os
import io
import json
import shutil
import copy
import math
import time
import random
import requests
import logging
import datetime

# ------- PDF libs -------
import pdfkit
import PyPDF2
from tqdm import tqdm

# ------- Images and chart -------
import PIL.Image as Image
from PIL import ImageDraw, ImageFont
import matplotlib.pyplot as plt
from typing import List, Tuple
# ------- Api related -------
# from pydantic import BaseModel
# from fastapi import APIRouter
from jinja2 import Environment, FileSystemLoader
# from starlette.responses import JSONResponse

# ------- Parallel Processing libs -------
import subprocess
from concurrent.futures import ThreadPoolExecutor

# -------------------------------------------------------------------------------

from colorama import Fore


def parse_nested_json(data):
    # decoding the json by recursion for each json decodable field.
    if isinstance(data, str):
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return data
    #
    elif isinstance(data, dict):
        parsed_data = {}
        for key, value in data.items():
            parsed_data[key] = parse_nested_json(value)
        return parsed_data
    #
    elif isinstance(data, list):
        parsed_data = []
        for item in data:
            parsed_data.append(parse_nested_json(item))
        return parsed_data
    #
    else:
        return data

class TemplateWriter(object):
    payload: dict = {}
    generated_pdfs: list = [] # list of generated pdfs.
    current_date = datetime.date.today().strftime('%b %d, %Y')
    current_page_count:int = 0
    total_page_count:int = 0
    wkhtml_options: dict = {
                                'page-size': 'A4',
                                'margin-bottom': '10mm',
                                'margin-left': '0',
                                'margin-right': '0',
                                'margin-top': '10mm',
                                "enable-local-file-access": None,
                                "enable-external-links": None,
                                "enable-internal-links": None
                            }
    css_path: str
    templates_path: str
    project_dir: str
    logger: logging.Logger #
    jinja_env : Environment
    debug:bool = False
    vprint = lambda *args, **kwargs: None


    def __init__(self,
                 payload:dict,
                 css_path:str,
                 project_dir: str,
                 templates_path:str,
                 wkhtmltopdf_path:str,
                 wkhtml_options: dict,
                 logger:logging.Logger = logging.getLogger("TemplateWriter"),
                 verbose:bool = True,
                 debug:bool = False
                 ):
        
        def get_list_item(lst, index):
            if index < len(lst):
                return lst[index]
            return None
        
        self.templates_path = templates_path
        self.project_dir = project_dir
        self.css_path = css_path
        self.jinja_env = Environment(loader = FileSystemLoader(self.templates_path))
        self.jinja_env.filters['get_list_item'] = get_list_item
        
        self.wkhtmltopdf_config = pdfkit.configuration(wkhtmltopdf= wkhtmltopdf_path)
        self.wkhtml_options = wkhtml_options
        self.debug = debug
        self.verbose = verbose
        
        if self.verbose:
            self.vprint = lambda *args, **kwargs: print(*args, **kwargs)
        else:
            self.vprint = lambda *args, **kwargs: None

        self.payload = payload
        self.current_date = datetime.date.today().strftime('%b %d, %Y')

        self.current_page_count = 1
        self.total_page_count = 0
        
        # 1. Page counting starts from BHI (Front Page excluded from total)
        # self.total_page_count += 1

        # 2. Count annotation pages: 3 images per page (ensure same logic as generator)
        try:
            total_annotations = 0
            for span in (self.payload.get("spans") or []):
                for section in (span.get("sections") or []):
                    for component in (section.get("components") or []):
                        for distress in (component.get("distresses") or []):
                            # Same check as generate_annotation_page
                            image = distress.get("image") or {}
                            if distress.get("annotation_coordinates") and image.get("url"):
                                total_annotations += 1
            
            annotation_pages = math.ceil(total_annotations / 3)
            self.total_page_count += annotation_pages
            print(f"total_annotations : {total_annotations}")
            print(f"annotation_pages estimated: {annotation_pages}")
        except Exception as e:
            print(f"ERROR counting annotation pages : {e}")

        # 3. Count BHI pages: across all spans using chunk size of 25 (simulation)
        try:
            total_bhi_pages = 0
            chunk_size = 22
            for span in (self.payload.get("spans") or []):
                # Simulate grouping and chunking
                span_grouped_rows = []
                for section in (span.get("sections") or []):
                    for component in (section.get("components") or []):
                        distresses = component.get("distresses") or [1]
                        span_grouped_rows.append(len(distresses))
                
                # Simulate chunking
                current_count = 0
                span_pages = 0
                for row_count in span_grouped_rows:
                    if current_count + row_count > chunk_size and current_count > 0:
                        span_pages += 1
                        current_count = 0
                    current_count += row_count
                if current_count > 0:
                    span_pages += 1
                
                total_bhi_pages += span_pages
            
            self.total_page_count += total_bhi_pages
            print(f"total_bhi_pages estimated (simulation): {total_bhi_pages}")
        except Exception as e:
            print(f"ERROR counting BHI pages : {e}")

        # Add other pages: Front Page, Chart, Thermography, Anomalies Info
        # self.total_page_count += 4 

        self.generated_pdfs = []

    def generate_front_page(self):

        self.vprint("Generating front page ...")
        front_page_template = self.jinja_env.get_template("front_page_template.html")
        html = front_page_template.render({
                                    "base_dir":self.templates_path,
                                    "site_name":self.payload.get("site_name", "Not Found"),
                                    "plant_capacity": str(self.payload.get("PlantCapacity", 0) / 1_000_000) + ' MW',
                                    "survey_name": self.payload.get("SurveyName")
                                    })


        
        if self.debug:
            with open( os.path.join(self.templates_path, "temp_front_page.html"), "w") as f:
                f.write(html)

        survey_name = self.payload.get("SurveyName", "Not_Found").replace(" ", "_")
        pdf_path = os.path.join(self.project_dir , survey_name +"_front_page.pdf") 

        ret = pdfkit.from_string(
                            html,
                            output_path= pdf_path,
                            options= self.wkhtml_options,
                            configuration= self.wkhtmltopdf_config,
                            verbose = self.verbose,
                            # css = self.css_path

                            # css = "/home/user/All_projects/tnd-kafka/report_gen/templates/default/inspection-report-new.component.css"
                        )
        if ret :
            self.generated_pdfs.append(pdf_path)
            return True
        else:
            return False
        


    def generate_table_of_content_page(self):
        self.vprint("Generating Index page ...")
        table_of_content_page_template = self.jinja_env.get_template("table_of_content_page_template.html")

        html = table_of_content_page_template.render({
                                            "base_dir": self.templates_path,
                                        })
        

        if self.debug:
            with open( os.path.join(self.templates_path, "temp_table_of_content_page.html"), "w") as f:
                f.write(html)
        
        survey_name = self.payload.get("SurveyName", "Not_Found").replace(" ", "_")
        pdf_path = os.path.join(self.project_dir , survey_name+'_table_of_content.pdf')

        ret = pdfkit.from_string(
                            html,
                            output_path= pdf_path,
                            options= self.wkhtml_options,
                            configuration= self.wkhtmltopdf_config,
                            verbose = self.verbose,
                            # css = self.css_path
                        )
        if ret:
            self.generated_pdfs.append(pdf_path)
            return True
        else:
            return False
    

    def generate_about_page(self):
        self.vprint("Generating About page ...")
        about_page_template = self.jinja_env.get_template("about_page_template.html")

        html = about_page_template.render({
                                            "base_dir": self.templates_path,
                                            "page_index": self.current_page_count,
                                        })

        split_html =  html.split("__::__")
        html = split_html[0]
        self.current_page_count = int(split_html[1])


        if self.debug:
            with open( os.path.join(self.templates_path, "temp_about_page.html"), "w") as f:
                f.write(html)
        
        pdf_path = os.path.join(self.project_dir , self.payload.get("SurveyName")+'_about_page.pdf')

        ret = pdfkit.from_string(
                            html,
                            output_path= pdf_path,
                            options= self.wkhtml_options,
                            configuration= self.wkhtmltopdf_config,
                            verbose = self.verbose,
                            # css = self.css_path
                        )
        if ret:
            self.generated_pdfs.append(pdf_path)
            return True
        else:
            return False

    def generate_solar_common_pages(self, common_pages_content=None):
        self.vprint("Generating Common pages ...")
        common_page_template = self.jinja_env.get_template("common_page_template.html")

        desired_order = ["Scope Of Work", "Objective", "Methodology"]
        sorted_common_pages_content = sorted(common_pages_content, key=lambda x: desired_order.index(x["heading"]) if x["heading"] in desired_order else len(desired_order))

        # sorted_common_pages_content = sorted_common_pages_content[:1]
        for page in sorted_common_pages_content : 

            html = common_page_template.render({
                                                "base_dir": self.templates_path,
                                                "page_index": self.current_page_count,
                                                "page_heading": page.get("heading"),
                                                "page_content": page.get("content")
                                            })


            split_html =  html.split("__::__")
            html = split_html[0]
            self.current_page_count = int(split_html[1])


            if self.debug:
                with open( os.path.join(self.templates_path, "temp_common_page.html"), "w") as f:
                    f.write(html)
            
            survey_name = self.payload.get("SurveyName", "Not_Found").replace(" ", "_")
            pdf_path = os.path.join(self.project_dir , survey_name+f"_common_page_{page.get('heading')}.pdf")

            ret = pdfkit.from_string(
                                html,
                                output_path= pdf_path,
                                options= self.wkhtml_options,
                                configuration= self.wkhtmltopdf_config,
                                verbose = self.verbose,
                                # css = self.css_path
                            )
            if ret:
                self.generated_pdfs.append(pdf_path)
            else:
                print(f"Introduction page generatation failed for heading : {page.get('heading')}")
        
        return True



    def generate_asset_analysis_page(self):
        self.vprint("Generating Asset Analysis page ...")
        asset_page_template = self.jinja_env.get_template("asset_analysis_page_template.html")


        html = asset_page_template.render({
                                            "base_dir": self.templates_path,
                                            "page_index": self.current_page_count,
                                        })
        
        split_html =  html.split("__::__")
        html = split_html[0]
        self.current_page_count = int(split_html[1])
        
        if self.debug:
            with open( os.path.join(self.templates_path, "temp_asset_analysis_page.html"), "w") as f:
                f.write(html)
        
        survey_name = self.payload.get("SurveyName", "Not_Found").replace(" ", "_")
        pdf_path = os.path.join(self.project_dir , survey_name+'_asset_analysis.pdf')

        ret = pdfkit.from_string(
                            html,
                            output_path= pdf_path,
                            options= self.wkhtml_options,
                            configuration= self.wkhtmltopdf_config,
                            verbose = self.verbose,
                            # css = self.css_path
                        )
        if ret:
            self.generated_pdfs.append(pdf_path)
            return True
        else:
            return False


    def generate_summary_page(self):

        def generate_colors(color_count):

            def random_color():
                # return '#' + str(hex(random.randint(0,16777215)))[2:] # method 1
                # return f"#{random.randint(0,255):02x}{random.randint(0,255):02x}{random.randint(0,255):02x}" # method 2
                return f"rgba({random.randint(0,255)}, {random.randint(0,255)}, {random.randint(0,255)}, 1)"

            # color_palette = [
            #                     'rgba(195, 252, 204, 1)',
            #                     'rgba(138, 244, 172, 1)',
            #                     'rgba(107, 246, 151, 1)',
            #                     'rgba(57, 230, 112, 1)',
            #                     'rgba(22, 208, 81, 1)',
            #                     'rgba(16, 176, 67, 1)',
            #                     'rgba(17, 150, 59, 1)',
            #                 ]

            color_palette = [
                                'rgba(54, 122, 31, 1.0)', 'rgba(71, 163, 41, 1.0)',
                                'rgba(89, 204, 51, 1.0)', 'rgba(127, 191, 64, 1.0)',
                                'rgba(122, 214, 92, 1.0)', 'rgba(153, 204, 102, 1.0)',
                                'rgba(156, 224, 133, 1.0)', 'rgba(178, 217, 140, 1.0)',
                                'rgba(172, 230, 153, 1.0)', 'rgba(191, 223, 160, 1.0)',
                                'rgba(189, 235, 173, 1.0)', 'rgba(204, 229, 179, 1.0)',
                                'rgba(222, 245, 214, 1.0)', 'rgba(229, 242, 217, 1.0)',
                                'rgba(238, 250, 235, 1.0)'
                            ]
            

            generated_colors = []
            if color_count <= len(color_palette):
                generated_colors = color_palette[ : color_count]
            
            else:
                generated_colors = color_palette[:]
                random_colors = [random_color() for i in range(color_count - len(color_palette))]
                generated_colors += random_colors

            return generated_colors
        

        self.vprint("Generating summary page ...")
        summary_page_template = self.jinja_env.get_template("summary_page_template.html")

        total_issues = 0

        graph_labels = []
        graph_data = []
        graph_backgroundColor = []
        for anomaly in self.payload.get("AnnomalyDetails"):
            total_issues += anomaly["AnnomalyCount"]

            graph_labels.append(anomaly["AnnomalyName"])
            graph_data.append(anomaly["AnnomalyCount"])


        graph_backgroundColor = generate_colors(len(graph_labels))
  

        html = summary_page_template.render({
            "base_dir": self.templates_path,
            "page_index": self.current_page_count,

            "total_number_of_modules": self.payload.get("TotalNumberOfModules"),
            "total_issues": total_issues,
            "annomaly_details": self.payload.get("AnnomalyDetails"),

            "graph_labels": graph_labels,
            "graph_data": graph_data,
            "graph_backgroundColor": graph_backgroundColor

        })


        split_html =  html.split("__::__")
        html = split_html[0]
        self.current_page_count = int(split_html[1])

        if self.debug:
            with open( os.path.join(self.templates_path, "temp_summary_page.html"), "w") as f:
                f.write(html)

        survey_name = self.payload.get("SurveyName", "Not_Found").replace(" ", "_")
        pdf_path = os.path.join(self.project_dir , survey_name+'_summary.pdf' )

        ret = pdfkit.from_string(
                            html,
                            output_path= pdf_path,
                            options= self.wkhtml_options,
                            configuration= self.wkhtmltopdf_config,
                            verbose = self.verbose,
                            # css = self.css_path
                        )
        if ret :
            self.generated_pdfs.append(pdf_path)
            return True
        else:
            return False


    def generate_chart_page(self):
        
        average_module_capacity = self.payload.get("ModuleCapacity")
        total_affected_capacity_mw = ( int(self.payload.get("TotalAffectModules")) * average_module_capacity ) / 1_000_000
        total_functional_capacity_mw = self.payload.get("PlantCapacity") - total_affected_capacity_mw


        self.vprint("Generating Chart pages ...")
        chart_page_template = self.jinja_env.get_template("chart_page_template.html")

        html = chart_page_template.render({
                                            "base_dir": self.templates_path,
                                            "page_index": self.current_page_count,

                                            "plant_affected_capacity_labels": [f"Total Functional Capacity ( {total_functional_capacity_mw} MW )", f"Total Affected Capacity ( {total_affected_capacity_mw} MW )"],
                                            "plant_affected_capacity_data": [total_functional_capacity_mw ,total_affected_capacity_mw] ,
                                            "plant_affected_capacity_background_color": ['rgba(87, 179, 244, 1)', 'rgba(177, 220, 251, 1)'] ,

                                            "affected_capacity_modules_labels":[ f'Affected Modules ({self.payload.get("TotalAffectModules")})',
                                                                                 f'Inspected Modules ({self.payload.get("TotalNumberOfModules")})'],

                                            "affected_capacity_modules_data":[self.payload.get("TotalAffectModules"), self.payload.get("TotalNumberOfModules")],
                                            "affected_capacity_modules_background_color": ['rgba(230, 207, 5, 1)','rgba(251, 245, 187, 1)'],
                                        })
        
        split_html =  html.split("__::__")
        html = split_html[0]
        self.current_page_count = int(split_html[1])
        
        if self.debug:
            with open( os.path.join(self.templates_path, "temp_chart_page.html"), "w") as f:
                f.write(html)
        
        survey_name = self.payload.get("SurveyName", "Not_Found").replace(" ", "_")
        pdf_path = os.path.join(self.project_dir , survey_name+'_chart.pdf')    

        ret = pdfkit.from_string(
                            html,
                            output_path= pdf_path,
                            options= self.wkhtml_options,
                            configuration= self.wkhtmltopdf_config,
                            verbose = self.verbose,
                            # css = self.css_path
                        )
        if ret:
            self.generated_pdfs.append(pdf_path)
            return True
        else:
            return False

    def generate_thermography_page(self):
        self.vprint("Generating Thermography page ...")
        thermography_page_template = self.jinja_env.get_template("thermography_page_template.html")


        html = thermography_page_template.render({
                                            "base_dir": self.templates_path,
                                            "page_index": self.current_page_count,
                                        })
        
        split_html =  html.split("__::__")
        html = split_html[0]
        self.current_page_count = int(split_html[1])
        
        if self.debug:
            with open( os.path.join(self.templates_path, "temp_thermography_page.html"), "w") as f:
                f.write(html)
        
        survey_name = self.payload.get("SurveyName", "Not_Found").replace(" ", "_")
        pdf_path = os.path.join(self.project_dir , survey_name+'_thermography_page.pdf')

        ret = pdfkit.from_string(
                            html,
                            output_path= pdf_path,
                            options= self.wkhtml_options,
                            configuration= self.wkhtmltopdf_config,
                            verbose = self.verbose,
                            # css = self.css_path
                        )
        if ret:
            self.generated_pdfs.append(pdf_path)
            return True
        else:
            return False


    def generate_execution_plan_pages(self):
        self.vprint("Generating Execution Plan pages ...")
        execution_plan_page_template = self.jinja_env.get_template("execution_plan_page_template.html")

        html = execution_plan_page_template.render({
                                            "base_dir": self.templates_path,
                                            "page_index": self.current_page_count,
                                        })
        
        split_html =  html.split("__::__")
        html = split_html[0]
        self.current_page_count = int(split_html[1])
        
        if self.debug:
            with open( os.path.join(self.templates_path, "temp_execution_plan_page.html"), "w") as f:
                f.write(html)
        
        pdf_path = os.path.join(self.project_dir , self.payload.get("SurveyName")+'_execution_plan.pdf')

        ret = pdfkit.from_string(
                            html,
                            output_path= pdf_path,
                            options= self.wkhtml_options,
                            configuration= self.wkhtmltopdf_config,
                            verbose = self.verbose,
                            # css = self.css_path
                        )
        if ret:
            self.generated_pdfs.append(pdf_path)
            return True
        else:
            return False


    def generate_anomalies_info_page(self):
        self.vprint("Generating Anomalies Info pages ...")
        anomalies_info_page_template = self.jinja_env.get_template("anomalies_info_page_template.html")

        iso_time = self.payload.get("SurveyCreatedDate", "")
        if iso_time:
            formatted_date = datetime.datetime.fromisoformat(iso_time).strftime("%B %Y")
        else:
            formatted_date = ""

        formatted_date = self.payload.get("SurveyName")

        html = anomalies_info_page_template.render({
                                            "base_dir": self.templates_path,
                                            "page_index": self.current_page_count,
                                            "SurveyCreatedDate": formatted_date
                                        })
        
        split_html =  html.split("__::__")
        html = split_html[0]
        self.current_page_count = int(split_html[1])
        
        if self.debug:
            with open( os.path.join(self.templates_path, "temp_anomalies_info_page.html"), "w") as f:
                f.write(html)
        
        survey_name = self.payload.get("SurveyName", "Not_Found").replace(" ", "_")
        pdf_path = os.path.join(self.project_dir , survey_name+'_anomalies_info.pdf')

        ret = pdfkit.from_string(
                            html,
                            output_path= pdf_path,
                            options= self.wkhtml_options,
                            configuration= self.wkhtmltopdf_config,
                            verbose = self.verbose,
                            # css = self.css_path
                        )
        if ret:
            self.generated_pdfs.append(pdf_path)
            return True
        else:
            return False

    def generate_bhi_table_page(self, chunk_size: int = 22):
        self.vprint("Generating BHI Table page (SPAN-WISE version)...")

        template = self.jinja_env.get_template("bhi_table_template.html")
        survey_name = self.payload.get("site_name", "Not_Found").replace(" ", "_")

        # ✅ STEP 0: Calculate overall total BHI pages (Simulation) and overall minimum BHI
        overall_total_bhi_pages = 0
        overall_min_bhi = None
        for s in self.payload.get("spans", []):
            # Simulation: Group-aware chunking
            s_grouped_counts = []
            for sec in s.get("sections", []):
                for comp in sec.get("components", []):
                    distresses = comp.get("distresses") or [1]
                    s_grouped_counts.append(len(distresses))
            
            curr_count = 0
            s_pages = 0
            for r_count in s_grouped_counts:
                if curr_count + r_count > chunk_size and curr_count > 0:
                    s_pages += 1
                    curr_count = 0
                curr_count += r_count
            if curr_count > 0:
                s_pages += 1
            overall_total_bhi_pages += s_pages
            
            # Calculate overall minimum BHI
            s_bhi = s.get("bhi")
            if s_bhi is not None:
                if overall_min_bhi is None or s_bhi < overall_min_bhi:
                    overall_min_bhi = s_bhi
        
        print(f"OVERALL TOTAL BHI PAGES (SIMULATION): {overall_total_bhi_pages}")
        print(f"OVERALL MINIMUM BHI: {overall_min_bhi}")

        pdf_paths = []
        cumulative_bhi_page_idx = 0
        prev_chunk_last_row = None

        # ✅ LOOP PER SPAN
        for span_idx, span in enumerate(self.payload.get("spans", [])):
            span_name = span.get("span_name", f"Span {span_idx + 1}")
            span_bhi = span.get("bhi", 0)
            
            grouped_rows = []

            # ✅ STEP 1: Build grouped rows for THIS span only
            for section in span.get("sections", []):
                section_name = section.get("section_name")
                section_id = section.get("section_id")
                section_score = section.get("group_score")

                for component in section.get("components", []):
                    component_rows = []

                    distresses = component.get("distresses") or [{
                        "asset_name": component.get("asset_type_name", "Nil"),
                        "anomaly_name": component.get("primary_condition", "Nil"),
                        "condition_state": component.get("primary_condition", "I")
                    }]

                    for distress in distresses:

                        component_rows.append({
                            "section_name": section_name,
                            "section_id": section_id,
                            "section_score": section_score,
                            "component": component,
                            "distress": distress,
                            "show_section": False
                        })

                    if component_rows:
                        grouped_rows.append(component_rows)

            print(f"SPAN {span_idx+1} - COMPONENT GROUPS:", len(grouped_rows))

            # ✅ STEP 2: Chunk per span
            chunks = []
            current_chunk = []
            current_count = 0

            for group in grouped_rows:
                if current_count + len(group) > chunk_size and current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = []
                    current_count = 0

                current_chunk.extend(group)
                current_count += len(group)

            if current_chunk:
                chunks.append(current_chunk)

            print(f"SPAN {span_idx+1} - TOTAL CHUNKS:", len(chunks))

            # ✅ RESET section continuity PER SPAN (important!)
            last_section_id = None

            # ✅ STEP 3: Render per span
            for idx, chunk in enumerate(chunks):

                # track section continuity per chunk
                if idx == 0:
                    last_section_id = None
                else:
                    last_section_id = f"{prev_chunk_last_row['section_id']}_{prev_chunk_last_row['section_name']}"

                processed_chunk = []
                seen_sections = set()

                for i, row in enumerate(chunk):
                    new_row = dict(row)
                    sec_id = f"{new_row['section_id']}_{new_row['section_name']}"

                    if i == 0:
                        new_row["show_section"] = sec_id != last_section_id
                    elif sec_id not in seen_sections:
                        new_row["show_section"] = True
                    else:
                        new_row["show_section"] = False

                    seen_sections.add(sec_id)
                    processed_chunk.append(new_row)

                # ✅ STEP 4: Calculate rowspan for CIi PER SECTION within this chunk
                i = 0
                while i < len(processed_chunk):
                    current_sec_id = processed_chunk[i]['section_id']
                    count = 0
                    while i + count < len(processed_chunk) and processed_chunk[i+count]['section_id'] == current_sec_id:
                        count += 1
                    
                    processed_chunk[i]['section_rowspan'] = count
                    for j in range(1, count):
                        processed_chunk[i+j]['section_rowspan'] = 0
                    i += count

                # ✅ STEP 5: Calculate rowspan for Bridge Component PER COMPONENT within this chunk
                i = 0
                while i < len(processed_chunk):
                    # Use a combination of section_id and component_name for uniqueness
                    current_comp_id = f"{processed_chunk[i]['section_id']}_{processed_chunk[i]['component'].get('component_name')}"
                    count = 0
                    while (i + count < len(processed_chunk) and 
                           f"{processed_chunk[i+count]['section_id']}_{processed_chunk[i+count]['component'].get('component_name')}" == current_comp_id):
                        count += 1
                    
                    processed_chunk[i]['component_rowspan'] = count
                    for j in range(1, count):
                        processed_chunk[i+j]['component_rowspan'] = 0
                    i += count

                # Render with current counters

                html = template.render({
                    "base_dir": self.templates_path,
                    "report_page_index": self.current_page_count,
                    "current_section_page": cumulative_bhi_page_idx + 1,
                    "total_section_pages": self.total_page_count,

                    # 🔥 ADD SPAN INFO
                    "span_name": span_name,
                    "span_index": span_idx + 1,
                    "total_spans": len(self.payload.get("spans", [])),

                    "rows": processed_chunk,
                    "prev_section_id": prev_chunk_last_row["section_id"] if prev_chunk_last_row else None,
                    "prev_component_name": prev_chunk_last_row["component"].get("component_name") if prev_chunk_last_row else None,
                    "show_summary": idx == len(chunks) - 1,
                    "is_final_summary": (cumulative_bhi_page_idx + 1) == overall_total_bhi_pages,
                    "overall_min_bhi": overall_min_bhi,
                    "bhi": span_bhi,
                    "footer_inspection_name": survey_name,
                    "footer_current_date": self.current_date,
                })

                sanitized_span_name = span_name.replace(" ", "_").replace("/", "_")
                pdf_path = os.path.join(
                    self.project_dir,
                    f"{survey_name}_{sanitized_span_name}_bhi_{self.current_page_count}.pdf"
                )

                # Split HTML by marker and update page count if present
                if "__::__" in html:
                    split_html = html.split("__::__")
                    html = split_html[0]
                    # The page count is already incremented manually in this loop, 
                    # but we split to avoid rendering the marker in the PDF.

                ret = pdfkit.from_string(
                    html,
                    output_path=pdf_path,
                    options=self.wkhtml_options,
                    configuration=self.wkhtmltopdf_config,
                    verbose=self.verbose,
                )

                if ret:
                    self.generated_pdfs.append(pdf_path)
                    pdf_paths.append(pdf_path)
                    
                    # ✅ track last row AFTER successful generation for NEXT chunk
                    if processed_chunk:
                        prev_chunk_last_row = processed_chunk[-1]

                    # ✅ increment cumulative page counters AFTER successful generation
                    cumulative_bhi_page_idx += 1
                    self.current_page_count += 1
                else:
                    return False

        return True
    

    def generate_annotation_page(self):
        def extract_line_box_coordinates(line_coords: list, img_height: int, img_width: int, padding: int = 30):
            """
            Extract a padded bounding box around a LineString geometry.
            Handles UI → image Y-coordinate inversion.
            """
            x_list = [int(pt[0]) for pt in line_coords]
            y_list = [int(pt[1]) for pt in line_coords]

            xmin = min(x_list)
            ymin = img_height - max(y_list)
            xmax = max(x_list)
            ymax = img_height - min(y_list)

            # Add padding
            xmin -= padding
            ymin -= padding
            xmax += padding
            ymax += padding

            # Clamp to image boundaries
            xmin = max(0, xmin)
            ymin = max(0, ymin)
            xmax = min(img_width, xmax)
            ymax = min(img_height, ymax)

            return [(xmin, ymin), (xmax, ymax)]
        
        def extract_box_coordinates(ui_coord: list, img_height:int):
            # Utility Function
            x_list = [ int(point[0]) for point in ui_coord ]
            y_list = [ int(point[1]) for point in ui_coord ]
             
            ymin = img_height - max(y_list)
            ymax = img_height - min(y_list)   
            xmin = min(x_list)
            xmax = max(x_list)

            return [(xmin, ymin), (xmax, ymax)]

        
        def extract_line_coordinates(ui_coord: list) -> List[Tuple[int,int]]:
            coords = []

            # just take the first element and iterate the pairs
            for x, y in ui_coord:
                coords.append((int(x), int(y)))
            return coords



        def crop_coordinates_transform(box_coord: list, image_size:list, crop_padding:list, min_crop_size:list, line_coord: list = [(0,0),(0,0)], draw_output:str = 'box' ) -> tuple:
            # print("box_coord : ", box_coord)
            xmin, ymin = box_coord[0]
            xmax, ymax = box_coord[1]

            # adjust crop padding
            c_xmin = xmin - (crop_padding[0] // 2)
            c_xmax = xmax + (crop_padding[0] // 2)
            c_ymin = ymin - (crop_padding[1] // 2)
            c_ymax = ymax + (crop_padding[1] // 2)
            # print(f"breakpoint 1 c_x coordinates : ({c_xmin}, {c_ymin}, {c_xmax}, {c_ymax})")
            
            # adjust the minimum width and height criteria
            if (width_diff:=(c_xmax - c_xmin)) < min_crop_size[0]:
                delta = (min_crop_size[0] - width_diff) // 2
                c_xmin -= delta
                c_xmax += delta

            if (height_diff:=(c_ymax - c_ymin)) < min_crop_size[1]:
                delta = (min_crop_size[1] - height_diff) // 2
                c_ymin -= delta
                c_ymax += delta
            # print(f"breakpoint 2 c_x coordinates : ({c_xmin}, {c_ymin}, {c_xmax}, {c_ymax})")


            # Maintaining the original aspect ratio while cropping
            # -------------------------------------------------------------------
            # image_aspect_ratio = image_width / image_height
            original_aspect_ratio = image_size[0] / image_size[1]

            c_width = c_xmax - c_xmin
            c_height = c_ymax - c_ymin
            c_aspect_ratio = c_width / c_height

            # # Adjust Width case
            # # WORKING CODE 
            # if c_aspect_ratio < original_aspect_ratio:
            #     new_c_width = (c_ymax - c_ymin) * original_aspect_ratio
            #     c_xmin -= new_c_width // 2
            #     c_xmax += new_c_width // 2

            # # Adjust Height case
            # elif c_aspect_ratio > original_aspect_ratio:
            #     new_c_height = (c_xmax - c_xmin) / original_aspect_ratio
            #     c_ymin -= new_c_height // 2
            #     c_ymax += new_c_height // 2
            # else:
            #     pass


            # Adjust Width case
            # FOR TESTING CORRECTION IN ASPECT RATIO
            if c_aspect_ratio < original_aspect_ratio:
                new_c_width = (c_ymax - c_ymin) * original_aspect_ratio
                c_xmin -= abs(new_c_width - c_width) // 2
                c_xmax += abs(new_c_width - c_width) // 2

            # Adjust Height case
            elif c_aspect_ratio > original_aspect_ratio:
                new_c_height = (c_xmax - c_xmin) / original_aspect_ratio
                c_ymin -= abs(new_c_height - c_height) // 2
                c_ymax += abs(new_c_height - c_height) // 2
            else:
                pass


            # print(f"breakpoint 3 c_x coordinates : ({c_xmin}, {c_ymin}, {c_xmax}, {c_ymax})")

            # # -------------------------------------------------------------------------------------
            # # FOR TESTING
            # original_aspect_ratio = image_size[0] / image_size[1]

            # c_width = c_xmax - c_xmin
            # c_height = c_ymax - c_ymin
            # c_aspect_ratio = c_width / c_height

            # print(f"aspect ratio after correction : {c_aspect_ratio} / {original_aspect_ratio}")
            # # -------------------------------------------------------------------------------------

            # -------------------------------------------------------------------



            # adjust the out of bound cropping criteria
            if c_xmax >= image_size[0] :
                if (c_xmin - abs(image_size[0] - c_xmax)) >= 0:
                    c_xmin -= abs(image_size[0] - c_xmax)
                c_xmax = image_size[0]

            if c_ymax >= image_size[1] :
                if (c_ymin - abs( image_size[1]- c_ymax)) >= 0:
                    c_ymin -= abs( image_size[1]- c_ymax)
                c_ymax = image_size[1]
                
            if c_xmin <= 0:
                if c_xmax + abs(c_xmin) <= image_size[0]:
                    c_xmax += abs(c_xmin)
                c_xmin = 0

            if c_ymin <= 0:
                if c_ymax + abs(c_ymin) <= image_size[1]:
                    c_ymax += abs(c_ymin)
                c_ymin = 0


            # print(f"breakpoint 4 c_x coordinates : ({c_xmin}, {c_ymin}, {c_xmax}, {c_ymax})")


            # transform annotation box coordinates to cropped coordinates considering (xmin, ymin) of crop_coord to new origin (0,0)
            xmin -= c_xmin
            ymin -= c_ymin
            xmax -= c_xmin
            ymax -= c_ymin

            # print(f"breakpoint 2 c_x coordinates : {c_xmin}, {c_ymin}, {c_xmax}, {c_ymax}")


            # -------------------------------------------------------------------------------------
            # # FOR TESTING
            # original_aspect_ratio = image_size[0] / image_size[1]

            # c_width = c_xmax - c_xmin
            # c_height = c_ymax - c_ymin
            # c_aspect_ratio = c_width / c_height

            # print(f"aspect ratio after correction : {c_aspect_ratio} / {original_aspect_ratio}")
            # -------------------------------------------------------------------------------------



            # return the boxes ensure that all co-ordinates must be int type.
            crop_coord = [ (int(c_xmin), int(c_ymin)) , (int(c_xmax), int(c_ymax)) ]
            crop_box_coord = [ (int(xmin), int(ymin)) , (int(xmax), int(ymax)) ]

            match draw_output:
                case 'box':
                    return crop_coord, crop_box_coord
                case 'line':
                    crop_line_coord = [ (int(point[0]-c_xmin) , int(point[1]-c_ymin)) for point in line_coord ]


                    return crop_coord, crop_box_coord, crop_line_coord
                case _ :
                    raise ValueError("draw_output can have only the following values:\n\t1> box\n\t2> line")



        def draw_box_and_count(img:Image, box_coord:list, anomaly_count:int, line_width:int=3, font_file:str= "arial.ttf", image_type:str="annotation",outline_color:str="yellow"):
            draw = ImageDraw.Draw(img)
            # print("box_coord inside draw_box_and_count: ", box_coord)
            draw.rectangle(box_coord, outline=outline_color, width=line_width)

            # text = str(anomaly_count)
            # # font size proportions will be different for annotation and original image.
            # font_size = int(min(img.size[0], img.size[1]) * (15 if (image_type.lower() == "annotation") else 7 if (image_type.lower() == "original") else 15)/100 )# 15% of the max pixel in either axis.            
            # font = ImageFont.truetype(font_file, font_size)

            # # text draw box origin calculation so that text always aligns middle
            # text_size = draw.textbbox(xy = (0,0), text= text)[2:4]
            # # text_size = draw.textbbox(xy = (0,0))[2:4]
            # text_x = (box_coord[0][0] + box_coord[1][0] - text_size[0]) // 2
            # text_y = (box_coord[0][1] + box_coord[1][1] - text_size[1]) // 2
            
            # draw.text((text_x, text_y), text=text, fill="white", font=font)

            return img
        


        def draw_line_and_count(img:Image, box_coord:list, line_coord:list, anomaly_count:int, line_width:int=3, font_file:str= "arial.ttf", image_type:str="annotation"):
            draw = ImageDraw.Draw(img)

            # draw.rectangle(box_coord, outline="yellow", width=line_width)

            for i in range(len(line_coord)-1):
                line_points = [line_coord[i][0], line_coord[i][1], line_coord[i+1][0], line_coord[i+1][1]]  # [x1, y1, x2, y2]
                draw.line( line_points , fill=(5,255,0,255), width=line_width)


            # text = str(anomaly_count)
            # # font size proportions will be different for annotation and original image.
            # font_size = int(min(img.size[0], img.size[1]) * (15 if (image_type.lower() == "annotation") else 7 if (image_type.lower() == "original") else 15)/100 )# 15% of the max pixel in either axis.
            # font = ImageFont.truetype(font_file, font_size)

            # # text draw box origin calculation so that text always aligns middle
            # text_size = draw.textbbox(xy = (0,0), text= text)[2:4]
            # text_x = (box_coord[0][0] + box_coord[1][0] - text_size[0]) // 2
            # text_y = (box_coord[0][1] + box_coord[1][1] - text_size[1]) // 2
            
            # draw.text((text_x, text_y), text=text, fill="white", font=font)

            return img
        
        def generate_annotation_docx( template_path: str, output_path: str, annotations_to_plot):
            doc = DocxTemplate(template_path)
            
            annotation_contexts = []

            for index, (annotation, image) in enumerate(annotations_to_plot):
                cropped_path = annotation.get("image_path")
                parent_path = annotation.get("parent_img_path")

                # Helper function to check if value is meaningful
                def has_value(val):
                    if val is None:
                        return False
                    # Convert to string and strip whitespace
                    val_str = str(val).strip()
                    # Check for empty or common null representations
                    if val_str in ("", "N/A", "N A", "NA", "n/a", "None","N.A", "null", "NULL"):
                        return False
                    return True

                # Get raw values
                defect = annotation.get("AnomalyName", "")
                location = image.get("AssetPath", "")
                description = annotation.get("Notes", "")
                direction = annotation.get("Direction", "")

                context_entry = {
                    "pictureid": index + 1,
                    "assetname": image.get("AssetName", "N/A"),
                    "assettype": image.get("AssetTypeName", "N/A"),
                    "aianalysis": image.get("ShortSummary", "N/A"),
                    "severity": annotation.get("Severity", "N/A"),
                    
                    # Conditional display: ONLY show heading+value if value exists
                    "defect_display": f"Defect: {defect}" if has_value(defect) else "",
                    "location_display": f"Location: {location}" if has_value(location) else "",
                    "description_display": f"Description: {description}" if has_value(description) else "",
                    "direction_display": f"Direction: {direction}" if has_value(direction) else "",
                    
                    # Keep raw values for other potential uses
                    "defect": defect if has_value(defect) else "",
                    "location": location if has_value(location) else "",
                    "description": description if has_value(description) else "",
                    "direction": direction if has_value(direction) else "",
                }

                # Handle parent image safely
                if parent_path:
                    context_entry["parent_image"] = InlineImage(doc, parent_path, width=Mm(92), height=Mm(58))
                else:
                    context_entry["parent_image"] = None

                # Add cropped image ONLY IF it exists
                if cropped_path:
                    context_entry["cropped_image"] = InlineImage(doc, cropped_path, width=Mm(92), height=Mm(58))
                else:
                    context_entry["cropped_image"] = None

                annotation_contexts.append(context_entry)

            # Final context
            context = {
                "annotations": annotation_contexts,
                "survey_id": self.payload.get("SurveyId"),
                "footer_inspection_name": self.payload.get("SurveyName"),
                "footer_current_date": self.current_date,
            }

            doc.render(context)

            try:
                doc.save(output_path)
                if output_path not in self.generated_docs:
                    self.generated_docs.append(output_path)
                return True
            except Exception as e:
                self.vprint(f"Error saving document: {e}")
                return False


            


        def get_defect_location(tree: list, member_id: str, separator: str='/') -> str:
            """
            Utility function to find the location of defect in tree recursively.

            Args:
                tree (list): Inspection tree structure from which the complete location is to be found.
                member_id (str): Member id of the member to which the anomaly is associated.
                separator (str, optional): Separator to saparate the each tree node. Defaults to '/'.
            

            Returns:
                str: returns the location of defect sararated by specified separator.
            """
            
            parent_id = member_id
            parent_location = ''

            parent_found = True

            while (parent_id is not None) and (parent_found):
                parent_found = False

                for tree_member in tree:
                    if isinstance(tree_member.get('MemberId'), str) and (tree_member.get('MemberId') == member_id):
                        parent_found = True
                        parent_id = tree_member.get('ParentId')
                        member_id = parent_id

                        parent_location = tree_member.get('MemberName') + separator + parent_location

            if not parent_found:
                print(f"Warning : Tree structure abnormal behaviour can not find the member_id : {member_id} in inspection tree.")

            return parent_location[:-1] # slicing to remove separator at the end of the string.


        self.vprint("Generating annomaly pages pdf ...")
        anomaly_count = 1

        total_annotated_images = 0
        images = []
        
        for span in self.payload.get("spans"):
            for section in span.get("sections"):
                for component in section.get("components"):
                    distresses = component.get("distresses") or [{
                        "asset_name": component.get("asset_type_name", "Nil"),
                        "anomaly_name": component.get("primary_condition", "Nil"),
                        "condition_state": component.get("primary_condition", "I")
                    }]
                    for distress in distresses:
                        image = distress.get("image")
                        annotation_coordinates = distress.get("annotation_coordinates")

                        if annotation_coordinates and image.get("url") is not None:
                            images.append({
                                "image": image,
                                "annotation_coordinates": annotation_coordinates,
                                "asset_name": distress.get("asset_name"),
                                "anomaly_name": distress.get("anomaly_name"),
                                "severity": distress.get("severity"),
                                "condition_state": distress.get("condition_state"),
                                "asset_type_name" : distress.get("asset_type_name"),
                                "tree_structure" : f"{section.get('section_name')}/{component.get('component_name')}/{distress.get('asset_name')}"
                            })
                            total_        # Pre-assign annotation index before multithreading to avoid race conditions
        for annotation in images:
            if "annotation_index" not in annotation:
                annotation["annotation_index"] = anomaly_count
                anomaly_count += 1

        def process_image_task(item):
            image_count, annotation = item
            print(f"Processing... {Fore.YELLOW}{ image_count + 1 }{Fore.RESET}/{Fore.BLUE}{total_annotated_images}{Fore.RESET} ")
            image_id = annotation.get("image").get("image_id") or f"image_{image_count+1}"
            current_image_dir = os.path.join(self.project_dir, str(image_id))
            os.makedirs(current_image_dir, exist_ok=True)
            
            image_url = annotation.get("image").get("url")
            if image_url:
                try:
                    response = requests.get(image_url, timeout=30)
                    if response.status_code == 200:
                        image_bytes = response.content
                    else:
                        print(f"    Got return code : {response.status_code}")
                        image_bytes = None
                except Exception as e:
                    print(f"    Download error for {image_url}: {e}")
                    image_bytes = None
            else:
                return
                
            if image_bytes:
                print("    Processing image...")
                raw_img = Image.open(io.BytesIO(image_bytes))
                img = raw_img.copy()
                img_width, img_height = img.size
                annotation_payload = annotation.get("annotation_coordinates")
                if annotation_payload is None:
                    return
                # imagePayload may already be a dict
                if isinstance(annotation_payload.get("geometry"), str):
                    try:
                        annotation_payload["geometry"] = json.loads(annotation_payload["geometry"])
                    except Exception:
                        pass
                geojson = annotation_payload

                if geojson is None:
                    print("No geojson found in annotation payload.")
                    return
                
                # If type is Feature, extract geometry
                if geojson.get("type") == "Feature":
                    geometry = geojson.get("geometry")
                    if not geometry:
                        print("Feature has no geometry.")
                        return
                    geometry_type = geometry.get("type")
                    geometry_coords = geometry.get("coordinates")
                else:
                    geometry_type = geojson.get("type")
                    geometry_coords = geojson.get("coordinates")
                
                if annotation.get("anomaly_color"):
                    outline_color = annotation.get("anomaly_color")
                else:
                    outline_color = "yellow"
                
                anno_idx = annotation.get("annotation_index", image_count + 1)
                         
                if geometry_type == "LineString":
                    line_coord = extract_line_coordinates(geometry_coords)
                    box_coord = extract_line_box_coordinates(line_coord, img_height=img_height, img_width=img_width, padding=10)
                    crop_coord, crop_box_coord, crop_line_coord = crop_coordinates_transform(
                                box_coord=box_coord,
                                image_size=[img_width, img_height],
                                crop_padding=[30, 30],
                                min_crop_size=[300, 300],
                                line_coord=line_coord,
                                draw_output='line'
                            )
                    cropped_annotation = raw_img.crop((crop_coord[0][0], crop_coord[0][1], crop_coord[1][0], crop_coord[1][1]))
                    cropped_annotation = draw_line_and_count(cropped_annotation, crop_box_coord, crop_line_coord, anno_idx, image_type="annotation")
                    img = draw_line_and_count(img, box_coord, line_coord, anno_idx, image_type="original", line_width=3)
                    annot_img_save_path = os.path.join(current_image_dir, str(anno_idx)+".jpg")
                    cropped_annotation = cropped_annotation.convert("RGB")
                    cropped_annotation.save(annot_img_save_path)
                    annotation['image_path'] = annot_img_save_path
                    img_save_path = os.path.join(current_image_dir, str(annotation.get("image").get("file_name")).split(".")[0] + str(anno_idx) + ".jpg")
                    img = img.convert("RGB")
                    img.save(img_save_path)
                    annotation["parent_img_path"] = img_save_path

                elif geometry_type == "Polygon":
                    polygon_points = [(int(x), int(y)) for x, y in geometry_coords[0]]
                    box_coord = extract_box_coordinates(polygon_points, img_height)
                    crop_coord, crop_box_coord = crop_coordinates_transform(
                        box_coord=box_coord,
                        image_size=[img_width, img_height],
                        crop_padding=[30, 30],
                        min_crop_size=[300, 300],
                        draw_output='box'
                    )
                    cropped_annotation = raw_img.crop((crop_coord[0][0], crop_coord[0][1], crop_coord[1][0], crop_coord[1][1]))
                    
                    cropped_annotation = draw_box_and_count(cropped_annotation, crop_box_coord, anno_idx, image_type="annotation",outline_color=outline_color)
                    img = draw_box_and_count(img, box_coord, anno_idx, image_type="original", line_width=20, outline_color=outline_color)
                                    
                    annot_img_save_path = os.path.join(current_image_dir, str(anno_idx)+".jpg")
                    cropped_annotation = cropped_annotation.convert("RGB")
                    cropped_annotation.save(annot_img_save_path)
                    annotation['image_path'] = annot_img_save_path
                                
                    img_save_path = os.path.join(current_image_dir, str(annotation.get("image").get("file_name")).split(".")[0] + str(anno_idx) + ".jpg")
                    img = img.convert("RGB")
                    img.save(img_save_path)
                    annotation["parent_img_path"] = img_save_path

                else:
                    print(f"Got unsupported Annotation type : {geometry_type}")
            else:
                print(f"{Fore.RED} [template_writer] > generate_anomaly_page {Fore.RESET} |  image could not be downloaded : {annotation.get('image', {}).get('image_id')}")

        with ThreadPoolExecutor(max_workers=10) as executor:
            list(executor.map(process_image_task, enumerate(images)))

        print("\nAll images processed ...")
 
        annotation_page_template = self.jinja_env.get_template("annotation_page_template.html")

        # Group images into pairs — 2 annotations per PDF page
        image_pairs = [images[i:i+3] for i in range(0, len(images), 3)]
        
        start_page_count = self.current_page_count

        def generate_pdf_task(item):
            page_count, annotation_pair = item
            print(f"Generating PDF of ... {Fore.YELLOW}{ page_count + 1 }{Fore.RESET}/{Fore.BLUE}{len(image_pairs)}{Fore.RESET} ")
            page_idx = start_page_count + page_count
            html = annotation_page_template.render({
                                    "base_dir":self.templates_path,
                                    "annotations_group": annotation_pair,
                                    "tower_no": "&nbsp",
                                    "base_url": "https://coredatarepo.s3.ap-south-1.amazonaws.com/",
                                    "page_index": page_idx,
                                    "total_pages": self.total_page_count,
                                    "footer_inspection_name":self.payload.get("site_name"),
                                    "footer_current_date": self.current_date,
                                    "survey_id": self.payload.get("survey_id"),
                                    "show_header": True,
                                    "zonename": "",
                                    "sitename": self.payload.get("site_name", ""),
                                    "InspectionName": self.payload.get("site_name", "")
                                    })
                
            split_html =  html.split("__::__")
            html = split_html[0]

            if self.debug:
                with open( os.path.join(self.templates_path, f"temp_anomaly_page_{page_count+1}.html"), "w") as f:
                    f.write(html)

            inspection_name = self.payload.get("InspectionName") or "UnknownInspection"
            pdf_path = os.path.join(self.project_dir, f"{inspection_name}_annotation_page_{page_count+1}.pdf")

            ret = pdfkit.from_string(
                                html,
                                output_path= pdf_path,
                                options= self.wkhtml_options,
                                configuration= self.wkhtmltopdf_config,
                                verbose = self.verbose,
                                css = self.css_path
                            )
            if ret :
                return pdf_path
            else:
                self.vprint(f"Error in Generating PDF file : {pdf_path}")
                return None

        with ThreadPoolExecutor(max_workers=10) as executor:
            pdf_results = list(executor.map(generate_pdf_task, enumerate(image_pairs)))

        for pdf_path in pdf_results:
            if pdf_path:
                self.generated_pdfs.append(pdf_path)

        self.current_page_count = start_page_count + len(image_pairs)
        return True


    def compress_pdfs(self, shard_pdfs: list, workers: int = 10) -> list:
        # print("GOT SHARD PDFS : ", shard_pdfs)
        """
        Function to compress pdf size using GhostScript,
        uses workers to do task fast. max_workers defaults to 5.
        can change max_workers depending on the system specs and usage.

        Args:
            shard_pdfs (list): List of the paths of generated shard pdfs.
            workers (int, optional): number of workers to speedup process. Defaults to 1.

        Functions:
            gs_reduce_size: Uses Ghostscript to reduce the size of the pdf.
            compress_pdf_wrapper: Wrapper function for thread pool executor.

        Returns:
            list: list of compressed pdf files.
        """

        def gs_reduce_size(input_file: str, output_file: str) -> None:
            """
            Function to reduce the size of a PDF file using Ghostscript.

            Args:
                input_file (str): Path to the input PDF file.
                output_file (str): Path to the output PDF file.

            Returns:
                None
            """

            # Set Ghostscript command
            # For ref. check "https://www.adobe.com/acrobat/hub/how-to-compress-pdf-in-linux.html"
            # "-dPDFSETTINGS" can have one of the values ['/screen', '/ebook', '/prepress', '/default']
            # values are in increasing order of quality and PDF size corresponding to [ 72dpi, 150dp, 300dp, largerPDF]
            # TODO: run ghost-script as superuser prevledges.
            gs_command = [
                'gs',
                '-sDEVICE=pdfwrite',
                '-dCompatibilityLevel=1.4',
                '-dPDFSETTINGS=/prepress',
                '-dEmbedAllFonts=true',
                '-dSubsetFonts=true',
                '-dNOPAUSE',
                '-dQUIET',
                '-dBATCH',
                '-sOutputFile=' + output_file,
                input_file
            ]

            # Execute Ghostscript command
            gs_process = subprocess.Popen(gs_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Wait for subprocess to end
            stdout, stderr = gs_process.communicate()

            if bool(stderr):
                raise Exception(f"Exception in PDF compression : {stderr}")
            

        def compress_pdf_wrapper(pdf):
            compressed_file_path = os.path.join(os.path.dirname(pdf), "compressed", os.path.basename(pdf))
            gs_reduce_size(input_file=pdf, output_file=compressed_file_path)
            return compressed_file_path


        max_workers = 5 
        compressed_pdfs_dir = os.path.join(os.path.dirname(shard_pdfs[0]), "compressed")
        
        if not os.path.exists(compressed_pdfs_dir) :
            self.vprint(f"Creating directory for compressed pdfs : {compressed_pdfs_dir}")
            os.mkdir(compressed_pdfs_dir)
        
        compressed_pdfs = []
        
        with ThreadPoolExecutor(max_workers= min(workers, max_workers)) as executor:
            results = []
            with tqdm(total=len(shard_pdfs), unit="PDFs", desc="Compressing PDFs", ncols=120, disable=self.verbose) as progress_bar:
                for result in executor.map(compress_pdf_wrapper, shard_pdfs):
                    results.append(result)
                    progress_bar.update(1)

            compressed_pdfs.extend(results)

        return compressed_pdfs


    def combine_pdfs(self,pdfs: list, output_file: str) -> str :
        """
        Function to combine multiple pdfs into single file.

        Args:
            shard_pdfs (list): list of paths of input pdf files in order of appending.
            output_file (str): path of output pdf file with name.

        Returns:
            str: path of the combined pdf file.
        """
        pdf_writer = PyPDF2.PdfWriter()

        for pdf in pdfs:
            with open(pdf, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                num_pages = len(pdf_reader.pages)

                for page_num in range(num_pages):
                    page = pdf_reader.pages[page_num]
                    pdf_writer.add_page(page)

        with open(output_file, 'wb') as output:
            pdf_writer.write(output)

        return output_file

