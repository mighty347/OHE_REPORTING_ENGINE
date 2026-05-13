import pdfkit
import os
import re

# Configuration for wkhtmltopdf
path_wkhtmltopdf = '/usr/bin/wkhtmltopdf'
config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)

# Define paths
base_dir = '/app/report_modules/inspection_default_source'
html_file = os.path.join(base_dir, 'html_templates/temp_anomaly_page.html')
css_file = os.path.join(base_dir, 'html_templates/inspection-report-new.component.css')
output_pdf = os.path.join(base_dir, 'test/output.pdf')

# PDF options
options = {
    'page-size': 'A4',
    'margin-top': '0',
    'margin-right': '0',
    'margin-bottom': '0',
    'margin-left': '0',
    'encoding': "UTF-8",
    'enable-local-file-access': None,
    'no-outline': None
}

def check_images_in_html(html_path):
    print(f"Checking images in {html_path}...")
    with open(html_path, 'r') as f:
        content = f.read()
    
    # Simple regex to find img src
    img_sources = re.findall(r'<img [^>]*src="([^"]+)"', content)
    
    all_exist = True
    for src in img_sources:
        if os.path.exists(src):
            print(f" [OK] Found: {src}")
        else:
            print(f" [MISSING] Not found: {src}")
            all_exist = False
    return all_exist

def convert_html_to_pdf(html_path, pdf_path, css_path):
    # Check images first
    check_images_in_html(html_path)
    
    print(f"\nConverting {html_path} to {pdf_path}...")
    try:
        pdfkit.from_file(html_path, pdf_path, configuration=config, options=options, css=css_path)
        print("Success! PDF generated at:", pdf_path)
    except Exception as e:
        print("Error during conversion:", e)

if __name__ == "__main__":
    os.makedirs(os.path.dirname(output_pdf), exist_ok=True)
    convert_html_to_pdf(html_file, output_pdf, css_file)
