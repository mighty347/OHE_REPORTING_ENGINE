import os
import time
import json
import report_main
# import natsort



# print(f"{Fore.GREEN}[ main ]{Fore.RESET}")


import time
import argparse
from colorama import Fore


import sys
# Ensure print statements are flushed immediately
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)


def main():
    parser = argparse.ArgumentParser(description="")

    parser.add_argument("-f", "--kwargs_file", type=str, required = True, help="Kwargs json file.")
    args = parser.parse_args()

    if args.kwargs_file:
        print(f"File argument is set to: {args.kwargs_file}")

    with open(args.kwargs_file, "r") as f:
        kwargs = json.load(f)

    # generate_pdf(**kwargs) # function to call with keyword arguments.
    report_main.main(**kwargs)

if __name__ == "__main__":
    main()