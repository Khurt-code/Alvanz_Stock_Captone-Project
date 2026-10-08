from django.apps import AppConfig


# Registers the POS app that owns sale models, checkout/report views, routes, and templates.
class PosConfig(AppConfig):
    name = 'pos'
