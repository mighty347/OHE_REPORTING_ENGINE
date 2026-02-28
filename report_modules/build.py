import os
import sys
import shutil
from setuptools import setup, find_packages
from Cython.Build import cythonize

from setuptools.command.build_ext import build_ext
import distutils.command.build



def build_report_module(package_name):
    base_path = os.path.dirname(__file__)

    if package_name == 'visual':
        # module_directory = os.path.abspath("../report_modules/ashdyke_default_source")
        # build_directory = os.path.abspath('../report_modules/ashdyke_default_build')

        module_directory = os.path.join(base_path, "./visual_default_source")
        build_directory = os.path.join(base_path, "./visual_default_build")

        python_files = [f"{module_directory}/awsmanager.py",
                        f"{module_directory}/db_client.py",
                        f"{module_directory}/dpds_excel_generator.py",
                        f"{module_directory}/excel_generator.py",
                        f"{module_directory}/report_gen_config.py",
                        f"{module_directory}/report_main.py",
                        f"{module_directory}/template_writer.py"
                    #    f"{module_directory}/main.py"
                    ]

        static_files = {f"{module_directory}/main.py": f"{build_directory}/main.py",
                        f"{module_directory}/arial.ttf": f"{build_directory}/arial.ttf",
                        # f"{module_directory}/wkhtmltopdf": f"{build_directory}/wkhtmltopdf"
                        }
        
        static_directories = {f"{module_directory}/html_templates/": f"{build_directory}/html_templates/",
                              f"{module_directory}/excel_templates/": f"{build_directory}/excel_templates/",
                              }
    

    elif package_name == 'thermal':
        module_directory = os.path.join(base_path, "./thermal_default_source")
        build_directory = os.path.join(base_path, "./thermal_default_build")

        python_files = [f"{module_directory}/awsmanager.py",
                        f"{module_directory}/db_client.py",
                        f"{module_directory}/excel_generator.py",
                        f"{module_directory}/report_gen_config.py",
                        f"{module_directory}/report_main.py",
                        f"{module_directory}/template_writer.py"
                    #    f"{module_directory}/main.py"
                    ]

        static_files = {f"{module_directory}/main.py": f"{build_directory}/main.py",
                        f"{module_directory}/arial.ttf": f"{build_directory}/arial.ttf",
                        # f"{module_directory}/wkhtmltopdf": f"{build_directory}/wkhtmltopdf"
                        }
        
        static_directories = {f"{module_directory}/html_templates/": f"{build_directory}/html_templates/",
                              f"{module_directory}/excel_template/": f"{build_directory}/excel_template/",
                              }
        

    elif package_name == 'lidar':
        # module_directory = os.path.abspath("../report_modules/ashdyke_default_source")
        # build_directory = os.path.abspath('../report_modules/ashdyke_default_build')

        module_directory = os.path.join(base_path, "./lidar_default_source")
        build_directory = os.path.join(base_path, "./lidar_default_build")

        python_files = [f"{module_directory}/awsmanager.py",
                        f"{module_directory}/db_client.py",
                        f"{module_directory}/excel_generator.py",
                        f"{module_directory}/report_gen_config.py",
                        f"{module_directory}/report_main.py",
                        f"{module_directory}/template_writer.py"
                    #    f"{module_directory}/main.py"
                    ]

        static_files = {f"{module_directory}/main.py": f"{build_directory}/main.py",
                        f"{module_directory}/arial.ttf": f"{build_directory}/arial.ttf",
                        # f"{module_directory}/wkhtmltopdf": f"{build_directory}/wkhtmltopdf"
                        }
        
        static_directories = {f"{module_directory}/html_templates/": f"{build_directory}/html_templates/"}
    
    elif package_name == 'ashdyke':
        # module_directory = os.path.abspath("../report_modules/ashdyke_default_source")
        # build_directory = os.path.abspath('../report_modules/ashdyke_default_build')

        module_directory = os.path.join(base_path, "./ashdyke_default_source")
        build_directory = os.path.join(base_path, "./ashdyke_default_build")

        python_files = [f"{module_directory}/awsmanager.py",
                        f"{module_directory}/db_client.py",
                        f"{module_directory}/excel_generator.py",
                        f"{module_directory}/report_gen_config.py",
                        f"{module_directory}/report_main.py",
                        f"{module_directory}/template_writer.py"
                    #    f"{module_directory}/main.py"
                    ]

        static_files = {f"{module_directory}/main.py": f"{build_directory}/main.py",
                        f"{module_directory}/arial.ttf": f"{build_directory}/arial.ttf",
                        # f"{module_directory}/wkhtmltopdf": f"{build_directory}/wkhtmltopdf"
                        }
        
        static_directories = {f"{module_directory}/html_templates/": f"{build_directory}/html_templates/"}

    elif package_name == 'solar':
        # module_directory = os.path.abspath("../report_modules/solar_default_source")
        # build_directory = os.path.abspath('../report_modules/solar_default_build')

        module_directory = os.path.join(base_path, "./solar_default_source")
        build_directory = os.path.join(base_path, "./solar_default_build")


        python_files = [f"{module_directory}/awsmanager.py",
                        f"{module_directory}/db_client.py",
                        f"{module_directory}/report_main.py",
                        f"{module_directory}/excel_generator.py",
                        f"{module_directory}/report_gen_config.py",
                        f"{module_directory}/template_writer.py"
                        ]

        static_files = {f"{module_directory}/main.py": f"{build_directory}/main.py",
                        f"{module_directory}/arial.ttf": f"{build_directory}/arial.ttf",
                        # f"{module_directory}/wkhtmltopdf": f"{build_directory}/wkhtmltopdf"
                        }
        
        static_directories = {f"{module_directory}/html_templates/": f"{build_directory}/html_templates/",
                            #   f"{module_directory}/wkhtmltopdf_0.12.6-2build2_amd64/": f"{build_directory}/wkhtmltopdf_0.12.6-2build2_amd64/"
                              }

    elif package_name == 'pmc':
        # module_directory = os.path.abspath("../report_modules/pmc_default_source")
        # build_directory = os.path.abspath('../report_modules/pmc_default_build')

        module_directory = os.path.join(base_path, "./pmc_default_source")
        build_directory = os.path.join(base_path, "./pmc_default_build")

        python_files = [f"{module_directory}/awsmanager.py",
                        f"{module_directory}/db_client.py",
                        f"{module_directory}/report_main.py",
                        f"{module_directory}/excel_generator.py",
                        f"{module_directory}/report_gen_config.py",
                        f"{module_directory}/template_writer.py"
                        ]

        static_files = {f"{module_directory}/main.py": f"{build_directory}/main.py",
                        f"{module_directory}/arial.ttf": f"{build_directory}/arial.ttf",
                        # f"{module_directory}/wkhtmltopdf": f"{build_directory}/wkhtmltopdf"
                        }

        static_directories = {f"{module_directory}/html_templates/": f"{build_directory}/html_templates/"}

    if not os.path.exists(module_directory):
        raise FileNotFoundError(module_directory)

    if os.path.exists(build_directory):
        print(f"Removing : {build_directory}")
        shutil.rmtree(build_directory)

    class BuildCommand(distutils.command.build.build):
        def initialize_options(self):
            distutils.command.build.build.initialize_options(self)
            self.build_base = build_directory
            self.build_lib = build_directory



    ext_modules = cythonize(python_files)

    distribution = setup(
                            ext_modules=ext_modules,
                            cmdclass={"build": BuildCommand}
                        )

    # copy static files to build directory
    for src, dest in static_files.items():
        shutil.copy(os.path.abspath(src), os.path.abspath(dest))

    # copy static directory to build directory

    for src, dest in static_directories.items():
        shutil.copytree(os.path.abspath(src), os.path.abspath(dest), dirs_exist_ok=True)


    # remove generated .c files
    for ext_module in ext_modules:
        module_path = ext_module.sources[0]
        os.remove(module_path)

    # python build.py build_ext clean
    # --inplace

if __name__=="__main__":
    # package_name = 'visual'
    package_name = 'thermal'
    # package_name = 'lidar'
    # package_name = 'ashdyke'
    # package_name = 'solar'
    # package_name = 'pmc'
    if len(sys.argv) < 3:
        print("Usage:\npython build.py build_ext clean")
        sys.exit()

    package_name = 'visual'
    build_report_module(package_name)
    
    package_name = 'thermal'
    build_report_module(package_name)

    package_name = 'lidar'
    build_report_module(package_name)

    package_name = 'ashdyke'
    build_report_module(package_name)

    package_name = 'solar'
    build_report_module(package_name)
    
    package_name = 'pmc'
    build_report_module(package_name)