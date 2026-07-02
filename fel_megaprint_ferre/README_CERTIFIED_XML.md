# Certified XML storage

After a successful FEL registration, the module replaces the preliminary signed XML in `documento_xml_fel` with the final certified DTE returned by `retornarXML`.

For invoices certified before this update, use **Recuperar XML certificado FEL** from the invoice form. The action only calls `solicitarToken` and `retornarXML`; it does not sign or register a new document.
