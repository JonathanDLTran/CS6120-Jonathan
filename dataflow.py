import sys
import json
import click

from reaching_definitions import reaching_defs
from constant_propagation import constant_prop
from live_variables import live_variables
from available_expressions import available_exprs


@click.command()
@click.option('--reaching', default=False, help='Run Reaching Defintion Analysis.')
@click.option('--constant', default=False, help='Run Constant Propagation Analysis.')
@click.option('--live', default=False, help='Run Live Variables Analysis.')
@click.option('--available', default=False, help='Run Available Expressions Analysis.')
@click.option('--pretty-print', default=False, help='Print Program Under Analysis.')
def main(reaching, constant, live, available, pretty_print):
    prog = json.load(sys.stdin)
    if pretty_print:
        print(json.dumps(prog, indent=4, sort_keys=True))
    if reaching:
        print("Reaching Definitions Analysis")
        reaching_defs(prog)
    if constant:
        print("Constant Propagation Analysis")
        constant_prop(prog)
    if live:
        print("Live Variables Analysis")
        live_variables(prog)
    if available:
        print("Available Expressions Analysis")
        available_exprs(prog)


if __name__ == "__main__":
    main()
