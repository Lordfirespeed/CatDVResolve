import argparse
import sys


def install_plugin_symlink(args: argparse.Namespace) -> None:
    print("I would try to make a symlink now!")


class ParserThatGivesUsageOnError(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        sys.stderr.write(f"Error: {message}\n")
        self.print_help()
        sys.exit(2)


parser = ParserThatGivesUsageOnError(description="Use the CatDV Resolve Plugin command-line tool.")
subparsers = parser.add_subparsers(
    title="commands",
    metavar="[command]",
    help="description"
)

install_parser = subparsers.add_parser("install", help="install the plugin")
install_parser.set_defaults(func=install_plugin_symlink)

args = parser.parse_args()
try:
    args.func(args)
except AttributeError:
    parser.error("No command specified")
