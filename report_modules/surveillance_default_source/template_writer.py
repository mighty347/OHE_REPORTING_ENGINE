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
from concurrent.futures import ThreadPoolExecutor, as_completed

# -------------------------------------------------------------------------------

from colorama import Fore
from urllib.parse import urlparse, urlunparse



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
                                'margin-bottom': '0',
                                'margin-left': '0',
                                'margin-right': '0',
                                'margin-top': '0',
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
        
        def format_datetime(value, fmt='%b %d, %Y %I:%M %p'):
            """Convert ISO 8601 datetime string to a readable format."""
            if not value:
                return ''
            try:
                dt = datetime.datetime.fromisoformat(str(value))
                # Define IST timezone
                ist = datetime.timezone(datetime.timedelta(hours=5, minutes=30))

                # If datetime has no timezone assume UTC
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=datetime.timezone.utc)

                # Convert to IST
                dt = dt.astimezone(ist)

                return dt.strftime(fmt)

            except (ValueError, TypeError):
                return str(value)
        
        self.jinja_env.filters['format_datetime'] = format_datetime
        
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
        
        # Calculate anomaly pages
        image_with_annotation = []
        total_anomaly_pages = 0
        images = self.payload.get("surveillance_reports", [{}])
        if images and 'sp_get_annotations_for_report' in images[0]:
            zonewise = images[0]['sp_get_annotations_for_report'].get('ZoneWiseData', [])
            for zone in zonewise:
                annotations = zone.get("Annotations", [])
                for annotation in annotations:
                    if annotations:
                        image_with_annotation.append(annotation)
                        total_anomaly_pages += 1

        annot_data = self.payload.get('surveillance_reports', [{}])[0].get('sp_get_annotations_for_report', {})
        zone_wise = annot_data.get('ZoneWiseData', [])
        cameras = annot_data.get('CameraList', [])
        anomaly_summary = annot_data.get('AnomalySummary', [])
        
        all_items_count = len(zone_wise) + len(cameras)
        graph_labels_count = len(anomaly_summary)
        summary_pages = 0
        FIRST_PAGE_ITEMS = 14
        SUBSEQUENT_PAGE_ITEMS = 26
        
        if all_items_count > 0:
            summary_pages = 1
            remaining = all_items_count - FIRST_PAGE_ITEMS
            if remaining > 0:
                summary_pages += math.ceil(remaining / SUBSEQUENT_PAGE_ITEMS)
            
            if graph_labels_count > 0:
                violation_rows = graph_labels_count + 1
                items_on_last_page = all_items_count if remaining <= 0 else (remaining % SUBSEQUENT_PAGE_ITEMS)
                if items_on_last_page == 0 and remaining > 0:
                    items_on_last_page = SUBSEQUENT_PAGE_ITEMS
                
                page_capacity = FIRST_PAGE_ITEMS if summary_pages == 1 else SUBSEQUENT_PAGE_ITEMS
                remaining_space = page_capacity - items_on_last_page
                
                if remaining_space < violation_rows:
                    summary_pages += 1
        elif graph_labels_count > 0:
            summary_pages = 1

        self.total_page_count = summary_pages + math.ceil(total_anomaly_pages/3)
        
        
        self.generated_pdfs = []
        self.generated_docs = []
        # print(f"{Fore.GREEN}Assigning Payload inside init.{Fore.RESET}")
        # print(f"{Fore.RED}self.payload : {Fore.RESET}{payload}")


    def generate_front_page(self):

        self.vprint("Generating front page ...")
        front_page_template = self.jinja_env.get_template("front_page_template.html")
        site_name = "Not Available"
        try:
            site_name = (
                self.payload.get("surveillance_reports", [{}])[0]
                .get("sp_get_annotations_for_report", {})
                .get("ZoneWiseData", [{}])[0]
                .get("SiteName", "Not Available")
            )
        except (IndexError, AttributeError):
            pass
        html = front_page_template.render({
                                    "base_dir":self.templates_path,
                                    "site_name":site_name,
                                    "plant_capacity": str(self.payload.get("PlantCapacity", 0) / 1_000_000) + ' MW',
                                    "survey_name": self.payload.get("SurveyName"),
                                    "from_date": self.payload.get("from", ""),
                                    "to_date": self.payload.get("to", ""),
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
        split_html =  html.split("__::__")
        html = split_html[0]
        self.current_page_count = int(split_html[1])
        
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
        

        def render_and_save_summary_pdf(template, render_data, pdf_suffix, page_number):
            """Helper to render a summary page chunk, convert to PDF, and append to generated_pdfs."""
            html = template.render(render_data)

            split_html = html.split("__::__")
            html = split_html[0]
            self.current_page_count = int(split_html[1])

            if self.debug:
                debug_filename = f"temp_summary_page_{page_number}.html"
                with open(os.path.join(self.templates_path, debug_filename), "w") as f:
                    f.write(html)

            survey_name = self.payload.get("SurveyName", "Not_Found").replace(" ", "_")
            pdf_path = os.path.join(self.project_dir, f"{survey_name}_summary_{pdf_suffix}.pdf")

            ret = pdfkit.from_string(
                html,
                output_path=pdf_path,
                options=self.wkhtml_options,
                configuration=self.wkhtmltopdf_config,
                verbose=self.verbose,
            )
            if ret:
                self.generated_pdfs.append(pdf_path)
            else:
                self.vprint(f"Error generating summary PDF: {pdf_path}")
            return ret
        

        self.vprint("Generating summary pages ...")
        summary_page_template = self.jinja_env.get_template("summary_page_template.html")

        total_issues = 0

        graph_labels = []
        graph_data = []
        graph_backgroundColor = []
        camera_list = []
        zonename = []
        # sitename = self.payload['surveillance_reports'][0]['sp_get_annotations_for_report']['ZoneWiseData'][0]['SiteName']
        # summary = self.payload['surveillance_reports'][0]['sp_get_annotations_for_report']['Summary']
        # anomaly_summary = self.payload['surveillance_reports'][0]['sp_get_annotations_for_report']['AnomalySummary']
        # cameras = self.payload['surveillance_reports'][0]['sp_get_annotations_for_report']['CameraList']

        report_data = self.payload.get('surveillance_reports', [{}])[0]
        annot_data = report_data.get('sp_get_annotations_for_report', {})
        zone_wise = annot_data.get('ZoneWiseData', [])
        summary = annot_data.get('Summary', '')
        anomaly_summary = annot_data.get('AnomalySummary', [])
        cameras = annot_data.get('CameraList', [])
        footer_inspection_name = zone_wise[0]['SiteName'] if zone_wise else 'Unknown'

        # Build zonename list
        for zone in zone_wise:
            zonename.append(zone["ZoneName"])

        # Build camera_list with zone info
        for camera in cameras:
            camera_list.append(camera['CameraName'])

        for anomaly in anomaly_summary:
            graph_labels.append(anomaly["AnomalyName"])
            graph_data.append(anomaly["Count"])

        graph_backgroundColor = generate_colors(len(graph_labels))

        # --- Chunk sizes ---
        FIRST_PAGE_ITEMS = 14   # max zone/camera items on the first page (has Report Overview too)
        SUBSEQUENT_PAGE_ITEMS = 26  # max zone/camera items on subsequent pages

        # --- Combine zones and cameras into one list for chunked rendering ---
        # Each item is a tuple: ("zone", name) or ("camera", name)
        all_items = [("zone", z) for z in zonename] + [("camera", c) for c in camera_list]

        # --- Split into page-sized chunks ---
        chunks = []
        if len(all_items) > 0:
            # First chunk (smaller, because first page has Report Overview)
            first_chunk = all_items[:FIRST_PAGE_ITEMS]
            chunks.append(first_chunk)
            # Remaining chunks
            remaining = all_items[FIRST_PAGE_ITEMS:]
            for i in range(0, len(remaining), SUBSEQUENT_PAGE_ITEMS):
                chunks.append(remaining[i:i + SUBSEQUENT_PAGE_ITEMS])
        
        page_number = 0
        zone_heading_shown = False
        camera_heading_shown = False

        # Check if violation analysis can fit on the last chunk page
        # +1 for the heading row
        violation_rows = len(graph_labels) + 1 if graph_labels else 0
        violations_merged = False

        # --- Render each chunk as a separate page ---
        for chunk_index, chunk in enumerate(chunks):
            # Separate zones and cameras from this chunk
            chunk_zones = [item[1] for item in chunk if item[0] == "zone"]
            chunk_cameras = [item[1] for item in chunk if item[0] == "camera"]

            is_first_page = (chunk_index == 0)
            is_last_chunk = (chunk_index == len(chunks) - 1)

            # Only show heading on the first page that contains that data type
            show_zone_heading = len(chunk_zones) > 0 and not zone_heading_shown
            show_camera_heading = len(chunk_cameras) > 0 and not camera_heading_shown

            if show_zone_heading:
                zone_heading_shown = True
            if show_camera_heading:
                camera_heading_shown = True

            # Determine if violations can fit on this (last) page
            page_capacity = FIRST_PAGE_ITEMS if is_first_page else SUBSEQUENT_PAGE_ITEMS
            remaining_space = page_capacity - len(chunk)
            include_violations = is_last_chunk and graph_labels and remaining_space >= violation_rows

            render_data = {
                "base_dir": self.templates_path,
                "page_index": self.current_page_count,
                "summary": summary if is_first_page else None,
                "total_number_of_modules": self.payload.get("TotalNumberOfModules"),
                "total_issues": total_issues,
                "annomaly_details": self.payload.get("AnnomalyDetails"),
                "camera_list": chunk_cameras,
                "zonename": chunk_zones,
                "show_zone_heading": show_zone_heading,
                "show_camera_heading": show_camera_heading,
                "footer_current_date": self.current_date,
                "footer_inspection_name": footer_inspection_name,
                "total_pages": self.total_page_count,
                "graph_labels": graph_labels if include_violations else [],
                "graph_data": graph_data if include_violations else [],
                "graph_backgroundColor": graph_backgroundColor if include_violations else [],
            }

            if include_violations:
                violations_merged = True
                self.vprint(f"  Rendering summary page {page_number + 1} (zones: {len(chunk_zones)}, cameras: {len(chunk_cameras)}, + Violation Analysis)")
            else:
                self.vprint(f"  Rendering summary page {page_number + 1} (zones: {len(chunk_zones)}, cameras: {len(chunk_cameras)})")
            render_and_save_summary_pdf(summary_page_template, render_data, f"page_{page_number}", page_number)
            page_number += 1

        # --- Render the Violation Analysis as a separate page only if it didn't fit ---
        if graph_labels and not violations_merged:
            render_data = {
                "base_dir": self.templates_path,
                "page_index": self.current_page_count,
                "summary": None,
                "total_number_of_modules": self.payload.get("TotalNumberOfModules"),
                "total_issues": total_issues,
                "annomaly_details": self.payload.get("AnnomalyDetails"),
                "camera_list": [],
                "zonename": [],
                "show_zone_heading": False,
                "show_camera_heading": False,
                "footer_current_date": self.current_date,
                "footer_inspection_name": footer_inspection_name,
                "total_pages": self.total_page_count,
                "graph_labels": graph_labels,
                "graph_data": graph_data,
                "graph_backgroundColor": graph_backgroundColor,
            }

            self.vprint(f"  Rendering summary page {page_number + 1} (Violation Analysis)")
            render_and_save_summary_pdf(summary_page_template, render_data, f"page_{page_number}", page_number)

        return True


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


    def _generate_single_annotation_pdf(self, args):
        """Generate a single PDF and return (index, pdf_path) or (index, None) on failure."""
        i, html, pdf_path = args
        print(f"Generating page : {i}")
        ret = pdfkit.from_string(
            html,
            output_path=pdf_path,
            options=self.wkhtml_options,
            configuration=self.wkhtmltopdf_config,
            verbose=self.verbose,
        )
        if ret:
            return i, pdf_path
        else:
            self.vprint(f"Error in Generating PDF file : {pdf_path}")
            return i, None

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

            xmin = min(x_list)
            ymin = min(y_list)
            xmax = max(x_list)
            ymax = max(y_list)


            return [(xmin, ymin), (xmax, ymax)]

        
        def extract_line_coordinates(ui_coord: list) -> List[Tuple[int,int]]:
            coords = []

            # just take the first element and iterate the pairs

            for group in ui_coord:
                for x, y in group:
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



        def draw_box_and_count(img:Image, box_coord:list, anomaly_count:int, line_width:int=3, font_file:str= "arial.ttf", image_type:str="annotation"):
            draw = ImageDraw.Draw(img)
            print("box_coord inside draw_box_and_count: ", box_coord)
            draw.rectangle(box_coord, outline="yellow", width=line_width)

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
        created_image_dirs = set()

        total_annotated_images = 0
        images = []
        zones = self.payload['surveillance_reports'][0]['sp_get_annotations_for_report']['ZoneWiseData']
        
        
        for zone in zones:
            zone_name = zone.get("ZoneName")
            site_name = zone.get("SiteName")
            
            for annotation in zone.get("Annotations", []):
                if annotation.get("FrameUrl") and annotation.get("Geometry"):
                    images.append(annotation["FrameUrl"])
                    total_annotated_images += 1

            for image_count,annotation  in enumerate( zone.get("Annotations", []) ):
                annotation["zone_name"] = zone_name
                annotation["site_name"] = site_name
                if annotation.get("Geometry"):
                    print(f"Processing... {Fore.YELLOW}{ image_count + 1 }{Fore.RESET}/{Fore.BLUE}{total_annotated_images}{Fore.RESET} ")
                    image_id = image_count + 1
                    # current_image_dir = os.path.join(self.project_dir, f"{zone.get('ZoneId', time.time())}{str(image_id)}") # here including zone_id because we need only a unique path if not found it will take epoch time.
                    current_image_dir = os.path.join(self.project_dir, f"{annotation.get('AnnotationId', time.time())}")
                    
                    os.makedirs(current_image_dir, exist_ok=True)
                    created_image_dirs.add(current_image_dir)
                    print(f"    Downloading image : {annotation.get('FrameUrl')} ... ")

                    # image_bytes = fetch_image(annotation.get("FrameUrl"), max_retries=3)
                    
                    ####### For Prod #######
                    parsed_url = urlparse(annotation.get("FrameUrl"))
                    new_netloc = f"minio:{parsed_url.port}"
                    modified_url = parsed_url._replace(
                                        netloc=new_netloc
                                    )
                    frame_url = urlunparse(modified_url)
                    response = requests.get(frame_url)
                    
                    ####### For Local Testing #######
                    # response = requests.get(annotation.get("FrameUrl"))
                    

                    
                    if response.status_code == 200:
                        image_bytes = response.content
                    else:
                        print(f"    Got return code : {response.status_code}")
                        image_bytes = None
                        

                    if image_bytes:
                        print("    Processing image...")
                        with Image.open(io.BytesIO(image_bytes)) as raw_img:
                            img = raw_img.copy()
                            
                        img_width, img_height = img.size
                            
                        annotation_payload = annotation.get("Geometry")                       
                        geojson = annotation_payload

                        # --- Handle GeoJSON Feature wrapper ---
                        if geojson is None:
                            print("No geojson found in annotation payload.")
                            continue
                        # If type is Feature, extract geometry
                        if geojson.get("type") == "Feature":
                            geometry = geojson.get("geometry")
                            if not geometry:
                                continue
                            geometry_type = geometry.get("type")
                            geometry_coords = geometry.get("coordinates")
                        else:
                            geometry_type = geojson.get("type")
                            geometry_coords = geojson.get("coordinates")
                        
                        if not geometry_coords:
                            continue
                        # --------------------------------------
                        
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
                            cropped_annotation = draw_line_and_count(cropped_annotation, crop_box_coord, crop_line_coord, anomaly_count, image_type="annotation")
                            img = draw_line_and_count(img, box_coord, line_coord, anomaly_count, image_type="original", line_width=3)
                            # annot_img_save_path = os.path.join(current_image_dir, str(anomaly_count)+".jpg")
                            # annot_img_save_path = os.path.join(current_image_dir, "cropped.jpg")
                            annot_img_save_path = os.path.join(current_image_dir, f"cropped_{anomaly_count}.jpg")
                            cropped_annotation = cropped_annotation.convert("RGB")
                            cropped_annotation.save(annot_img_save_path)
                            annotation["image_path"] = annot_img_save_path
                            annotation["annotation_index"] = anomaly_count
                            # img_save_path = os.path.join(current_image_dir,str(anomaly_count) + ".jpg")
                            # img_save_path = os.path.join(current_image_dir, "original.jpg")
                            img_save_path = os.path.join(current_image_dir, f"original_{anomaly_count}.jpg")
                            img = img.convert("RGB")
                            img.save(img_save_path)
                            annotation["parent_img_path"] = img_save_path
                            anomaly_count += 1

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
                            
                            cropped_annotation = draw_box_and_count(cropped_annotation, crop_box_coord, anomaly_count, image_type="annotation")
                            img = draw_box_and_count(img, box_coord, anomaly_count, image_type="original", line_width=3)
                                
                            # annot_img_save_path = os.path.join(current_image_dir, str(anomaly_count)+".jpg")
                            annot_img_save_path = os.path.join(current_image_dir, f"cropped_{anomaly_count}.jpg")
                            cropped_annotation = cropped_annotation.convert("RGB")  # <-- ADD THIS
                            cropped_annotation.save(annot_img_save_path)
                            annotation["image_path"] = annot_img_save_path
                            annotation["annotation_index"] = anomaly_count
                            img_save_path = os.path.join(current_image_dir, f"original_{anomaly_count}.jpg")
                            img = img.convert("RGB")  # <-- ADD THIS
                            img.save(img_save_path)
                            annotation["parent_img_path"] = img_save_path
                            anomaly_count += 1   

                        else:
                            print(f"Got unsupported Annotation type : {geometry_type}")
                            continue

                    else:
                        print(f"{Fore.RED} [template_writer] > generate_anomaly_page {Fore.RESET} ")#|  image could not be downloaded : {image.get('imageId')}")
                                    
        print("\nAll images processed ...")
 
        # header_image = self.download_header_image()
        # get the annotation template
        annotation_page_template = self.jinja_env.get_template("annotation_page_template.html")
        report_annotations = []
        for zone in zones:
            for annotation in zone.get("Annotations", []):
                if annotation.get("Geometry"):
                    report_annotations.append(annotation)

        report_annotations = sorted(
        report_annotations,
        key=lambda x: x.get("annotation_index", 0)
    )   
        total_annotated_images = len(report_annotations)

        tasks = []  # list of (i, html, pdf_path) tuples
        max_workers=4

        for i in range(0, total_annotated_images, 3):
            annotations_group = report_annotations[i:i + 3]
            print(f"Generating PDF of ... {Fore.YELLOW}{ i + 1 }{Fore.RESET}/{Fore.BLUE}{total_annotated_images}{Fore.RESET} ")
            html = annotation_page_template.render({
                                    "base_dir":self.templates_path,
                                    "annotations_group": annotations_group,
                                    "tower_no": "&nbsp",
                                    "base_url": "https://coredatarepo.s3.ap-south-1.amazonaws.com/",
                                    "page_index": self.current_page_count,
                                    "total_pages": self.total_page_count,
                                    "annotation_index": annotations_group[0].get("annotation_index"),   
                                    "zonename": annotations_group[0].get("zone_name"),
                                    "sitename": annotations_group[0].get("site_name"),
                                    "footer_inspection_name":self.payload["surveillance_reports"][0]['sp_get_annotations_for_report']['ZoneWiseData'][0]['SiteName'],
                                    "footer_current_date": self.current_date 
                                    })
            
            split_html =  html.split("__::__")
            html = split_html[0]
            self.current_page_count = int(split_html[1])

            if self.debug:
                with open( os.path.join(self.templates_path, "temp_anomaly_page.html"), "w") as f:
                    f.write(html)
            inspection_name = self.payload.get("InspectionName") or "UnknownInspection"
            # image_id = image.get("ImageId") or f"image_{image_count+1}"
            pdf_path = os.path.join(self.project_dir, f"{inspection_name}_{i}.pdf")
            tasks.append((i, html, pdf_path))

        # --- Phase 2: Generate PDFs in parallel, collect results ordered by i ---
        results = {}  # i -> pdf_path or None
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_index = {
                executor.submit(self._generate_single_annotation_pdf, task): task[0]
                for task in tasks
            }
            for future in as_completed(future_to_index):
                idx, pdf_path = future.result()
                results[idx] = pdf_path

        # --- Phase 3: Append in original order ---
        for i, _, _ in tasks:
            if results.get(i):
                self.generated_pdfs.append(results[i])

            # ret = pdfkit.from_string(
            #                     html,
            #                     output_path= pdf_path,
            #                     options= self.wkhtml_options,
            #                     configuration= self.wkhtmltopdf_config,
            #                     verbose = self.verbose,
            #                     # css = self.css_path
            #                 )
            # if ret :
            #     self.generated_pdfs.append(pdf_path)
            # else:
            #     self.vprint(f"Error in Generating PDF file : {pdf_path}")
                 
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

