from email.policy import default

from Tools.scripts.dutree import store
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class cailleproduction(models.Model):

    _name = 'caille.production'
    _description ='production de caille'

    name = fields.Char(string="Numero de production", required=True, default="nouvelle production", copy=False)
    date_production = fields.Date(string="Date", default=fields.Date.context_today)
    type_production = fields.Selection([("ponte","Ponte"),("viande","Viande")])

    nbr_oeuf_pondus = fields.Integer(string='oeufs pondus', default=0)
    nbr_oeuf_eclors = fields.Integer(string='oeufs eclors',default=0)
    nbr_oeuf_casses = fields.Integer(string='oeufs cassés', default=0)

    nbr_cailles_abattu = fields.Integer(string="cailles abattue")
    mort = fields.Integer(string="cailles mort avant abattage")

    # Production nette (ce qui entre en stock)
    production_nette = fields.Integer(string="Production nette", compute="_compute_production_nette", store=True)

    # Stocks globaux (calculés en temps réel)
    stock_oeufs_global = fields.Integer(string="Stock d'œufs", compute='_compute_stocks_globaux')
    stock_viande_global = fields.Integer(string="Stock de viande", compute='_compute_stocks_globaux')

    @api.model
    def create(self, vals):
        if vals.get('name', 'Nouveau') == 'Nouveau':
            vals['name'] = self.env['ir.sequence'].next_by_code('caille.production') or 'Nouveau'
        return super(cailleproduction, self).create(vals)

    @api.depends('type_production', 'nbr_oeuf_pondus', 'nbr_oeuf_eclors',
                 'nbr_oeuf_casses', 'nbr_cailles_abattu', 'mort')
    def _compute_production_nette(self):
        """Calcule la production nette qui entre en stock"""
        for record in self:
            if record.type_production == 'ponte':
                # Œufs disponibles = pondus - éclos - cassés
                record.production_nette = (record.nbr_oeuf_pondus -
                                           record.nbr_oeuf_eclors -
                                           record.nbr_oeuf_casses)
            elif record.type_production == 'viande':
                # Viande disponible = abattus + morts (peuvent être vendus)
                record.production_nette = record.nbr_cailles_abattu + record.mort
            else:
                record.production_nette = 0

    def _compute_stocks_globaux(self):
        """Calcule les stocks globaux en temps réel"""
        stocks = self.get_current_stocks()
        for record in self:
            record.stock_oeufs_global = stocks['stock_oeufs']
            record.stock_viande_global = stocks['stock_viande']

    @api.model
    def get_current_stocks(self):
        """
        Calcule les stocks actuels: Production - Ventes confirmées/payées
        IMPORTANT: Le stock diminue dès la CONFIRMATION, pas au paiement
        """
        # Stock d'œufs
        productions_oeufs = self.search([('type_production', '=', 'ponte')])
        total_oeufs_produits = sum(productions_oeufs.mapped('production_nette'))

        # Soustraire UNIQUEMENT les ventes confirmées ou payées (pas les brouillons ni annulées)
        ventes_oeufs = self.env['caille.ventes'].search([
            ('produit_id', '=', 'oeuf'),
            ('statut', 'in', ['confirme', 'paye'])  # Confirme ET payé réduisent le stock
        ])
        total_oeufs_vendus = sum(ventes_oeufs.mapped('quantite_vendus'))
        stock_oeufs = total_oeufs_produits - total_oeufs_vendus

        # Stock de viande
        productions_viande = self.search([('type_production', '=', 'viande')])
        total_viande_produite = sum(productions_viande.mapped('production_nette'))

        # Soustraire UNIQUEMENT les ventes confirmées ou payées
        ventes_viande = self.env['caille.ventes'].search([
            ('produit_id', '=', 'viande'),
            ('statut', 'in', ['confirme', 'paye'])  # Confirme ET payé réduisent le stock
        ])
        total_viande_vendue = sum(ventes_viande.mapped('quantite_vendus'))
        stock_viande = total_viande_produite - total_viande_vendue

        return {
            'stock_oeufs': stock_oeufs,
            'stock_viande': stock_viande
        }






    @api.onchange('type_production')
    def _onchange_type_productions(self):
        if self.type_production == 'ponte':
            self.mort=0
            self.nbr_cailles_abattu=0
        elif self.type_production == 'viande':
            self.nbr_oeuf_eclors=0
            self.nbr_oeuf_pondus=0
            self.nbr_oeuf_casses = 0


