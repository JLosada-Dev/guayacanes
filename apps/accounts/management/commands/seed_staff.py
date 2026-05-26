"""Seed staff users for the alcaldía portal.

Idempotent: re-running the command does not duplicate users. Use
``--reset-passwords`` to force passwords back to the seeded defaults.
Intended for development and demos — passwords MUST be rotated in production.
"""

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.roles import ROLE_COORDINADOR, ROLE_VEEDOR

STAFF_SEED = [
    {
        'username': 'veedor1',
        'password': 'veedor123',
        'first_name': 'Carolina',
        'last_name': 'Rivera',
        'email': 'veedor1@alcaldia.local',
        'role': ROLE_VEEDOR,
    },
    {
        'username': 'veedor2',
        'password': 'veedor123',
        'first_name': 'Andrés',
        'last_name': 'Mosquera',
        'email': 'veedor2@alcaldia.local',
        'role': ROLE_VEEDOR,
    },
    {
        'username': 'veedor3',
        'password': 'veedor123',
        'first_name': 'Sara',
        'last_name': 'Caicedo',
        'email': 'veedor3@alcaldia.local',
        'role': ROLE_VEEDOR,
    },
    {
        'username': 'coord1',
        'password': 'coord123',
        'first_name': 'Mauricio',
        'last_name': 'Vásquez',
        'email': 'coord1@alcaldia.local',
        'role': ROLE_COORDINADOR,
    },
    {
        'username': 'coord2',
        'password': 'coord123',
        'first_name': 'Diana',
        'last_name': 'Quintero',
        'email': 'coord2@alcaldia.local',
        'role': ROLE_COORDINADOR,
    },
]


class Command(BaseCommand):
    help = 'Seed alcaldía staff users (veedores y coordinadores) for development.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset-passwords',
            action='store_true',
            help='Force seeded passwords on existing users.',
        )
        parser.add_argument(
            '--quiet',
            action='store_true',
            help='Suppress per-user output.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        reset_passwords = options['reset_passwords']
        quiet = options['quiet']

        groups = {
            ROLE_VEEDOR: Group.objects.get_or_create(name=ROLE_VEEDOR)[0],
            ROLE_COORDINADOR: Group.objects.get_or_create(name=ROLE_COORDINADOR)[0],
        }

        created = updated = skipped = 0
        for spec in STAFF_SEED:
            user, was_created = User.objects.get_or_create(
                username=spec['username'],
                defaults={
                    'email': spec['email'],
                    'first_name': spec['first_name'],
                    'last_name': spec['last_name'],
                    'is_staff': False,
                    'is_active': True,
                },
            )

            if was_created:
                user.set_password(spec['password'])
                user.save()
                created += 1
                status = 'creado'
            else:
                changed = False
                if reset_passwords:
                    user.set_password(spec['password'])
                    changed = True
                if user.email != spec['email']:
                    user.email = spec['email']
                    changed = True
                if user.first_name != spec['first_name']:
                    user.first_name = spec['first_name']
                    changed = True
                if user.last_name != spec['last_name']:
                    user.last_name = spec['last_name']
                    changed = True
                if changed:
                    user.save()
                    updated += 1
                    status = 'actualizado'
                else:
                    skipped += 1
                    status = 'sin cambios'

            user.groups.add(groups[spec['role']])

            if not quiet:
                self.stdout.write(
                    f"  {spec['username']:<10} ({spec['role']:<12}) {status}"
                )

        summary = (
            f'Seed staff completo — creados: {created}, '
            f'actualizados: {updated}, sin cambios: {skipped}.'
        )
        self.stdout.write(self.style.SUCCESS(summary))
