from odoo import models, fields, api
from odoo.exceptions import ValidationError


class caillegestionclient(models.Model):

    _name ="caille.client"
    _description ="Gestion des client"
    _rec_name = "nom_client"

    nom_client = fields.Char(string="Nom", required=True)
    telephone_client = fields.Integer(string="Téléphone", required=True)
    email_client = fields.Char(string="Email")
    livraison = fields.Char(string="Lieu de livraison", required=True)

    @api.constrains('telephone')
    def _check_telephone_format(self):
        """Vérifie le format du téléphone"""
        for client in self:
            if client.telephone:
                # Supprimer les espaces et caractères spéciaux
                tel_clean = ''.join(filter(str.isdigit, client.telephone))
                if len(tel_clean) < 10:
                    raise ValidationError("Le numéro de téléphone doit contenir au moins 10 chiffres")

    @api.constrains('email')
    def _check_email_format(self):
        """Vérifie le format de l'email"""
        for client in self:
            if client.email and '@' not in client.email:
                raise ValidationError("Veuillez entrer une adresse email valide")

    def name_get(self):
        """Personnalise l'affichage du client dans les sélections"""
        result = []
        for client in self:
            display_name = f"{client.nom_client} ({client.telephone_client})"
            result.append((client.id, display_name))
        return result