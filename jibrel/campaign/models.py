from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from jibrel.campaign.enum import CampaignRoundStatus


class Company(models.Model):
    name = models.CharField(max_length=256)
    cms_id = models.CharField(max_length=32)

    class Meta:
        verbose_name = _('Company')
        verbose_name_plural = _('Companies')


class Offering(models.Model):
    STATUS_CHOICES = (
        (CampaignRoundStatus.PENDING, _('Pending')),
        (CampaignRoundStatus.ACTIVE, _('Active')),
        (CampaignRoundStatus.CLEARING, _('Clearing')),
        (CampaignRoundStatus.COMPLETED, _('Completed')),
        (CampaignRoundStatus.CANCELED, _('Canceled')),
    )

    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='offerings')

    limit_max_share = models.PositiveIntegerField(
        verbose_name=_('max investment amount per user'),
        blank=True, null=True
    )
    limit_min_share = models.PositiveIntegerField(
        default=1,
        verbose_name=_('min investment amount per user')
    )

    date_start = models.DateTimeField(verbose_name=_('campaign starts time'))
    date_end = models.DateTimeField(verbose_name=_('deadline'))

    # Fields is similar to the CMS one
    valuation = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name=_('valuation'),
        help_text=_('Valuation must be same across all campaign rounds')
    )
    goal = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name=_('Round size'),
        help_text=_('Cannot be grater then valuation')
    )
    round = models.CharField(max_length=32, verbose_name=_('Round name'))

    number_of_shares = models.PositiveIntegerField(verbose_name=_('Number of shares'))
    price_per_share = models.DecimalField(verbose_name=_('Single share price'))

    status = models.CharField(max_length=16, default=CampaignRoundStatus.PENDING)

    class Meta:
        verbose_name = _('Fundraising round')
        verbose_name_plural = _('Fundraising rounds')

    @cached_property
    def raised(self):
        """
        Amount of already raised funds
        """
        return 0

    @cached_property
    def participants(self):
        """
        Number of participants at this round
        """
        return 0

    @cached_property
    def equity(self):
        return self.goal / self.valuation
