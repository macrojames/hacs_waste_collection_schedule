#!/usr/bin/env python3

import argparse
import datetime
import importlib
import re
import site
import traceback
from pathlib import Path

import yaml

SECRET_FILENAME = "secrets.yaml"
SECRET_REGEX = re.compile(r"!secret\s(\w+)")


def main():
    parser = argparse.ArgumentParser(description="Test sources.")
    parser.add_argument(
        "-s", "--source", action="append", help="Test given source file"
    )
    parser.add_argument(
        "-l", "--list", action="store_true", help="List retrieved entries"
    )
    parser.add_argument(
        "-i", "--icon", action="store_true", help="Show waste type icon"
    )
    parser.add_argument(
        "-t",
        "--traceback",
        action="store_true",
        help="Print exception information and stack trace",
    )
    args = parser.parse_args()

    # read secrets.yaml
    secrets = {}
    try:
        with open(SECRET_FILENAME) as stream:
            try:
                secrets = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)
    except FileNotFoundError:
        # ignore missing secrets.yaml
        pass

    package_dir = Path(__file__).resolve().parents[2]
    source_dir = package_dir / "waste_collection_schedule" / "source"

    # add module directory to path
    site.addsitedir(str(package_dir))

    if args.source is not None:
        files = args.source
    else:
        files = filter(
            lambda x: x != "__init__",
            map(lambda x: x.stem, source_dir.glob("*.py")),
        )

    for f in sorted(files):
        # iterate through all *.py files in waste_collection_schedule/source
        print(f"Testing source {f} ...")
        module = importlib.import_module(f"waste_collection_schedule.source.{f}")

        # get all names within module
        names = set(dir(module))

        # test if all mandatory names exist
        assert "TITLE" in names
        assert "DESCRIPTION" in names
        assert "URL" in names
        assert "TEST_CASES" in names

        # run through all test-cases
        for name, tc in module.TEST_CASES.items():
            # replace secrets in arguments
            replace_secret(secrets, tc)

            # create source
            try:
                source = module.Source(**tc)
                result = source.fetch()
                count = len(result)
                if count > 0:
                    print(
                        f"  found {bcolors.OKGREEN}{count}{bcolors.ENDC} entries for {name}"
                    )
                else:
                    print(
                        f"  found {bcolors.WARNING}0{bcolors.ENDC} entries for {name}"
                    )

                # test if source is returning the correct date format
                if (
                    len(
                        list(
                            filter(lambda x: type(x.date) is not datetime.date, result)
                        )
                    )
                    > 0
                ):
                    print(
                        f"{bcolors.FAIL}  ERROR: source returns invalid date format (datetime.datetime instead of datetime.date?){bcolors.ENDC}"
                    )

                if args.list:
                    for x in result:
                        icon_str = f" [{x.icon}]" if args.icon else ""
                        print(f"    {x.date.isoformat()}: {x.type}{icon_str}")
            except KeyboardInterrupt:
                exit()
            except Exception as exc:
                print(f"  {name} {bcolors.FAIL}failed{bcolors.ENDC}: {exc}")
                if args.traceback:
                    print(indent(traceback.format_exc(), 4))


def replace_secret(secrets, d):
    for key in d.keys():
        value = d[key]
        if isinstance(value, dict):
            replace_secret(secrets, value)
        elif isinstance(value, str):
            match = SECRET_REGEX.fullmatch(value)
            if match is not None:
                id = match.group(1)
                if id in secrets:
                    d[key] = secrets[id]
                else:
                    print(f"identifier '{id}' not found in {SECRET_FILENAME}")


def indent(s, count):
    indent = " " * count
    return "\n".join([indent + line for line in s.split("\n")])


class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


if __name__ == "__main__":
    main()
