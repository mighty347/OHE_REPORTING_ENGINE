import os
import sys
import shutil

from report_modules import build as report_module_builder

from setuptools import setup, find_packages
from Cython.Build import cythonize

from setuptools.command.build_ext import build_ext
import distutils.command.build


def create_build(build_directory:str = os.path.abspath("build")):

    if os.path.exists(build_directory):
        shutil.rmtree(build_directory)

    report_module_builder.build_report_module('visual')
    report_module_builder.build_report_module('thermal')
    report_module_builder.build_report_module('lidar')
    report_module_builder.build_report_module('ashdyke')
    report_module_builder.build_report_module('solar')
    report_module_builder.build_report_module('pmc')


    class BuildCommand(distutils.command.build.build):
        def initialize_options(self):
            distutils.command.build.build.initialize_options(self)
            self.build_base = build_directory
            self.build_lib = build_directory


    python_files = [
        "celery_report_config.py",
        "celery_report_gen.py",
        "kafka_bridge_report_config.py",
        "kafka_bridge_report.py",
        "report_module_manager.py"
    ]


    static_files = {f"main.sh": f"{build_directory}/main.sh",
                    f"kafka_listener.py": f"{build_directory}/kafka_listener.py",
                    # f"installation_instrucitons.txt": f"{build_directory}/installation_instrucitons.txt",
                    f"requirements.txt": f"{build_directory}/requirements.txt",
                    f"start_redis_server.sh": f"{build_directory}/start_redis_server.sh",
                    f"start_celery_worker.sh": f"{build_directory}/start_celery_worker.sh",
                    f"start_kafka_listener.sh": f"{build_directory}/start_kafka_listener.sh",
                    f"start_reporting_service.sh": f"{build_directory}/start_reporting_service.sh",
                    f"ntpc_reporting_engine.service": f"{build_directory}/ntpc_reporting_engine.service",

                    }

    static_directories = {
                        f"./report_modules/visual_default_build/": f"{build_directory}/report_modules/visual_default_build/",
                        f"./report_modules/thermal_default_build/": f"{build_directory}/report_modules/thermal_default_build/",
                        f"./report_modules/lidar_default_build/": f"{build_directory}/report_modules/lidar_default_build/",

                        f"./report_modules/ashdyke_default_build/": f"{build_directory}/report_modules/ashdyke_default_build/",
                        f"./report_modules/pmc_default_build/": f"{build_directory}/report_modules/pmc_default_build/",
                        f"./report_modules/solar_default_build": f"{build_directory}/report_modules/solar_default_build",
                        }


    ext_modules = cythonize(python_files)

    distribution = setup(
                            ext_modules=ext_modules,
                            cmdclass={"build": BuildCommand}
                        )


    # copy static files to build directory
    for src, dest in static_files.items():
        shutil.copy(os.path.abspath(src), os.path.abspath(dest))

    for src, dest in static_directories.items():
        shutil.copytree(os.path.abspath(src), os.path.abspath(dest), dirs_exist_ok=True)


    # remove report modules build directories
    for src, dest in static_directories.items():
        shutil.rmtree(src)

    # remove generated .c files
    for ext_module in ext_modules:
        module_path = ext_module.sources[0]
        os.remove(module_path)


# python setup.py build_ext clean
if __name__=="__main__":

    if len(sys.argv) < 3:
        print("Usage:\npython build.py build_ext clean")
        sys.exit()

    create_build()