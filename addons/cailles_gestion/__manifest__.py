{
    "name":'Cailles Ivoire',
    "author":'Guindo/Cailles Ivoire',
    "version": '1.0',
    "description":'Gestion de productions et de ventes de cailles ',
    'sequence' : '-100',
    "depends":['base','sale_management','account'],
    "data":[
        "views/caille_client_view.xml",
        "views/caille_ventes_views.xml",
        "views/caille_production_view.xml",
        "views/caille_menu.xml",
        "security/caille_securite.xml",
        "security/ir.model.access.csv",
        "data/caille_data.xml"
    ],

'demo': [
    'demo/demo.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}