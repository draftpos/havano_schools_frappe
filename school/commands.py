import click
import frappe
from frappe.commands import pass_context

# Emulate get_site_context for older modules if absolutely necessary,
# but usually modern click commands don't need it.
def get_site_context(context):
    return context.sites[0] if context.sites else None

@click.command('school-test')
@pass_context
def school_test(context):
    pass
