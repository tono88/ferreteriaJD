# Ejecutar en Odoo shell únicamente en COPIA_PRDO_CUIDADO.
# Lectura exclusiva: no usa create/write/unlink/commit.

MODULE = 'pos_sales_summary_report_ferre'
GROUP = 'ferreteria_user_scope_ferre.group_pos_global_order_read'
ana = env['res.users'].sudo().search([('login', '=', 'corpjb.atebelan@gmail.com')], limit=1)
module = env['ir.module.module'].sudo().search([('name', '=', MODULE)], limit=1)
view = env.ref(MODULE + '.view_pos_sales_report_wizard_form', raise_if_not_found=False)
print('BASE DE DATOS:', env.cr.dbname)
print('MODULO:', module.name if module else '<no registrado>')
print('ESTADO:', module.state if module else '-')
print('INSTALLED_VERSION:', module.installed_version if module else '-')
print('LATEST_VERSION:', module.latest_version if module else '-')
print('VISTA EN DB:', bool(view))
if view:
    arch = view.arch_db or ''
    if not isinstance(arch, str):
        arch = str(arch)
    print('DB arch incluye global_pos_config_id:', 'global_pos_config_id' in arch)
    print('DB arch incluye groups global:', 'groups="ferreteria_user_scope_ferre.group_pos_global_order_read"' in arch)
print('ANA ENCONTRADA:', bool(ana))
if ana:
    print('LOGIN:', ana.login)
    print('GRUPO (has_group):', ana.has_group(GROUP))
    usr_env = env['pos.sales.report.wizard'].with_user(ana).with_context(allowed_company_ids=ana.company_ids.ids)
    print('CAMPO GLOBAL REGISTRADO:', 'global_pos_config_id' in usr_env._fields)
    print('CAMPO BOOLEAN REGISTRADO:', 'can_select_global_pos' in usr_env._fields)
    if view:
        try:
            effective = usr_env.get_view(view_id=view.id, view_type='form')
            effective_arch = effective.get('arch', '')
            print('ANA VISTA EFECTIVA incluye GLOBAL:', 'name="global_pos_config_id"' in effective_arch)
            print('ANA VISTA EFECTIVA incluye ORIGINAL:', 'name="pos_config_id"' in effective_arch)
        except Exception as e:
            print('ERROR get_view:', type(e).__name__, str(e))
