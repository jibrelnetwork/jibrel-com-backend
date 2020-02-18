from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Create verified user account'

    def handle(self, *args, **options):
        from tests.factories import VerifiedUser
        user = VerifiedUser.create()
        user.set_password('1234')
        user.save()

        self.stdout.write(self.style.SUCCESS(f"Email: {user.email} Password: 1234"))
