from .models import Bestellung, BestellteArtikel


def warenkorb_anzahl(request):

    if request.user.is_authenticated:
        kunde = request.user.kunde
        bestellung, created = Bestellung.objects.get_or_create(kunde=kunde, erledigt=False)

        if bestellung:
            menge = bestellung.get_gesamtmenge
        else:
            menge = 0
    else:
        menge = 0

    return {'menge': menge}
