from email.policy import default

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError

class cailleventes(models.Model):
    _name="caille.ventes"
    _description=("ventes de caille")

    name = fields.Char(string="Numero de vente", required=True, default="nouvelle ventes", copy=False)
    date_ventes = fields.Date(string="date de ventes", default=fields.Date.context_today, required=True)
    id_client = fields.Many2one('caille.client', string="client", required=True)
    produit_id = fields.Selection([("oeuf","Oeuf"),("viande", "Viande")], required=True)
    quantite_vendus = fields.Integer(string="quantité", required=True, default=1)
    prix_unitaire = fields.Float(string="prix unitaire (FCFA)", required=True)
    montant_total = fields.Float(string="Montant total (FCFA)", compute="_compute_total", store=True)


    statut = fields.Selection([('brouillon','Brouillon'),('confirme','Confirmé'),('paye','Payé'),('annule','Annulé')], string="Statut", default="brouillon")
    stock_total = fields.Integer(string="stock total", compute='_compute_stocks', store=True)
    stock_apres_ventes = fields.Integer(string="stock après ventes", compute='_compute_stocks', store=True)
    mode_de_paiement = fields.Selection([("espèces","Espèces"),("mobile money","Mobile Money")])

    @api.model
    def create(self, vals):
        if vals.get('name', 'Nouveau') == 'Nouveau':
            vals['name'] = self.env['ir.sequence'].next_by_code('caille.ventes') or 'Nouveau'
        return super(cailleventes, self).create(vals)

    @api.depends('quantite_vendus','prix_unitaire')
    def _compute_total(self):
        for record in self:
            record.montant_total = record.quantite_vendus * record.prix_unitaire

    @api.depends('produit_id', 'quantite_vendus', 'statut')
    def _compute_stocks(self):
        """Calcule le stock avant et après la vente"""
        for record in self:
            if not record.produit_id:
                record.stock_total = 0
                record.stock_apres_ventes = 0
                continue

            # Récupérer le stock global actuel
            stocks = self.env['caille.production'].get_current_stocks()

            if record.produit_id == 'oeuf':
                stock_actuel = stocks['stock_oeufs']
            else:  # viande
                stock_actuel = stocks['stock_viande']

            # Si la vente est déjà confirmée/payée, le stock actuel inclut déjà cette vente
            if record.statut in ['confirme', 'paye']:
                record.stock_total = stock_actuel + record.quantite_vendus
                record.stock_apres_ventes = stock_actuel
            else:
                # Si brouillon/annulé, montrer l'impact potentiel
                record.stock_total = stock_actuel
                record.stock_apres_ventes = stock_actuel - record.quantite_vendus

    @api.constrains('quantite_vendus')
    def _check_quantite_positive(self):
        """Vérifie que la quantité est positive"""
        for record in self:
            if record.quantite_vendus <= 0:
                raise ValidationError("La quantité doit être supérieure à 0")

    @api.constrains('quantite_vendus', 'produit_id', 'statut')
    def _check_stock_disponible(self):
        """Vérifie qu'il y a assez de stock avant de confirmer la vente"""
        for record in self:
            if record.statut in ['confirme', 'paye']:
                stocks = self.env['caille.production'].get_current_stocks()

                if record.produit_id == 'oeuf':
                    stock_disponible = stocks['stock_oeufs']
                    produit_nom = "d'œufs"
                else:
                    stock_disponible = stocks['stock_viande']
                    produit_nom = "de viande"

                # Ajouter la quantité de cette vente si elle était déjà confirmée
                vente_existante = self.search([
                    ('id', '=', record.id),
                    ('statut', 'in', ['confirme', 'paye'])
                ], limit=1)
                if vente_existante:
                    stock_disponible += vente_existante.quantite_vendus

                if record.quantite_vendus > stock_disponible:
                    raise ValidationError(
                        f"Stock insuffisant !\n"
                        f"Stock disponible {produit_nom}: {stock_disponible}\n"
                        f"Quantité demandée: {record.quantite_vendus}"
                    )

    def action_confirmer(self):
        """
        Confirme la vente et réduit le stock IMMÉDIATEMENT
        Le stock ne sera PAS réduit une 2ème fois lors du paiement
        """
        for record in self:
            if record.statut != 'brouillon':
                raise UserError("Seules les ventes en brouillon peuvent être confirmées")

            # Vérifier le stock AVANT de confirmer
            stocks = self.env['caille.production'].get_current_stocks()

            if record.produit_id == 'oeuf':
                stock_disponible = stocks['stock_oeufs']
                produit_nom = "d'œufs"
            else:
                stock_disponible = stocks['stock_viande']
                produit_nom = "de viande"

            if record.quantite_vendus > stock_disponible:
                raise UserError(
                    f"❌ Stock insuffisant !\n\n"
                    f"Stock disponible {produit_nom}: {stock_disponible}\n"
                    f"Quantité demandée: {record.quantite_vendus}\n\n"
                    f"Veuillez réduire la quantité ou produire davantage."
                )

            # Si le stock est suffisant, confirmer la vente
            # Le stock sera automatiquement réduit via get_current_stocks()
            record.write({'statut': 'confirme'})

        return True

    def action_payer(self):
        """
        Marque la vente comme payée
        IMPORTANT: Le stock a déjà été réduit lors de la confirmation,
        donc cette action ne réduit PAS le stock une 2ème fois
        """
        for record in self:
            if record.statut == 'confirme':
                # Simple changement de statut, pas de modification du stock
                record.write({'statut': 'paye'})
            elif record.statut == 'brouillon':
                # Si on passe directement de brouillon à payé, vérifier le stock
                stocks = self.env['caille.production'].get_current_stocks()

                if record.produit_id == 'oeuf':
                    stock_disponible = stocks['stock_oeufs']
                    produit_nom = "d'œufs"
                else:
                    stock_disponible = stocks['stock_viande']
                    produit_nom = "de viande"

                if record.quantite_vendus > stock_disponible:
                    raise UserError(
                        f"❌ Stock insuffisant !\n\n"
                        f"Stock disponible {produit_nom}: {stock_disponible}\n"
                        f"Quantité demandée: {record.quantite_vendus}"
                    )

                record.write({'statut': 'paye'})
            else:
                raise UserError("Seules les ventes en brouillon ou confirmées peuvent être payées")

        return True

    def action_annuler(self):
        """
        Annule la vente et RESTITUE le stock si la vente était confirmée/payée
        """
        for record in self:
            if record.statut == 'annule':
                raise UserError("Cette vente est déjà annulée")

            # Le stock sera automatiquement restitué car get_current_stocks()
            # n'inclut que les ventes avec statut 'confirme' ou 'paye'
            record.write({'statut': 'annule'})

        return True

    def action_remettre_en_brouillon(self):
        """Remet la vente en brouillon"""
        for record in self:
            record.write({'statut': 'brouillon'})
        return True


