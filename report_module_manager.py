import os
import json
import subprocess


def consume_pdf_task(bash_script:str, conda_env_name:str, report_module_dir:str, python_file_name:str, kwargs_json_path:str ):
    # report_module_dir : is the directory where 

    # Command to open a new terminal and execute the Bash script
    # terminal_command = f"x-terminal-emulator -e 'bash {bash_script} -c camui -w default -j 4'" # creating a new terminal and then running the bash script. (BUG: main process not waiting for the terminal to exit)
    # terminal_command = f"gnome-terminal -- bash {bash_script} -c camui -w default -j 4"   # creating a new gnome-terminal and then running the bash script. (BUG: main process not waiting for the terminal to exit)
    
    terminal_command = f"bash {bash_script} -c {conda_env_name} -w {report_module_dir} -f {python_file_name} -j {kwargs_json_path}"   # running the bash file in the same terminal

    # Use subprocess to open a new terminal and run the script
    process = subprocess.Popen(terminal_command, shell=True)
    # print("subprocess pid : ", process.pid)
    process.wait()



def process_pdf_task( report_module_dir:str, bash_script:str="main.sh", conda_env_name:str="base", python_file_name:str="main.py", **kwargs):

    if not os.path.exists(os.path.join(report_module_dir, python_file_name )):
        print(f"Template dir or the python file {python_file_name} does not exist.\n{os.path.join(report_module_dir, python_file_name)}")
        return False
    
    kwargs_json_path = os.path.join(os.path.dirname(__file__), "kwargs.json")

    with open(kwargs_json_path, 'w') as f:
        json.dump(kwargs, f,  indent=4)


    consume_pdf_task(bash_script, conda_env_name, report_module_dir, python_file_name, kwargs_json_path)

    return True

