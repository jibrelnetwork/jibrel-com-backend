from pycountry import countries

AVAILABLE_COUNTRIES_CHOICES = list(map(lambda country: (country.alpha_2, country.name), countries))
