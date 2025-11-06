from odoo import api, fields, models


class GuindoFoodClients(models.Model):
    _name = "guindo.food.clients"
    _description = "clients"

    name = fields.Char(string="nom du client", required=True)
    email = fields.Char(string="email", required=True)
    telephone= fields.Char(string="telephone")

