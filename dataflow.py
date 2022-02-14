import sys
import json
import click

from reaching_definitions import reaching_defs
from constant_propagation import constant_prop
from live_variables import live_variables


@click.command()
@click.option('--reaching', default=False, help='Run Reaching Defintion Analysis.')
@click.option('--constant', default=False, help='Run Constant Propagation Analysis.')
@click.option('--live', default=False, help='Run Live Variables Analysis.')
@click.option('--pretty-print', default=False, help='Print Program Under Analysis.')
def main(reaching, constant, live, pretty_print):
    prog = json.load(sys.stdin)
    if pretty_print:
        print(json.dumps(prog, indent=4, sort_keys=True))
    if reaching:
        print(reaching_defs(prog))
    if constant:
        print(constant_prop(prog))
    if live:
        print(live_variables(prog))


if __name__ == "__main__":
    main()
