from django.apps import AppConfig


# Registers the accounts app that owns users, login views, and access middleware.
class AccountsConfig(AppConfig):
    name = 'accounts'
