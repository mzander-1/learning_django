from django.http import JsonResponse
from django.shortcuts import render
from .models import *
import json


# Create your views here.

def shop(request):
    artikels = Artikel.objects.all()
    ctx = {'artikels': artikels}
    return render(request, "shop/shop.html", ctx)


def warenkorb(request):
    if request.user.is_authenticated:
        kunde = request.user.kunde
        bestellung, created = Bestellung.objects.get_or_create(kunde=kunde, erledigt=False)
        artikels = bestellung.bestellteartikel_set.all()
    else:
        artikels = []
        bestellung = []

    ctx = {'artikels': artikels, "bestellung": bestellung}
    return render(request, "shop/warenkorb.html", ctx)


def kasse(request):
    if request.user.is_authenticated:
        kunde = request.user.kunde
        bestellung, created = Bestellung.objects.get_or_create(kunde=kunde, erledigt=False)
        artikels = bestellung.bestellteartikel_set.all()
    else:
        artikels = []
        bestellung = []

    ctx = {'artikels': artikels, "bestellung": bestellung}
    return render(request, "shop/kasse.html", ctx)


def artikelBackend(request):
    daten = json.loads(request.body)
    artikelID = daten['artikelID']
    action = daten['action']
    kunde = request.user.kunde
    artikel = Artikel.objects.get(id=artikelID)
    bestellung, created = Bestellung.objects.get_or_create(kunde=kunde, erledigt=False)
    bestellteartikel, created = BestellteArtikel.objects.get_or_create(bestellung=bestellung, artikel=artikel)

    if action == 'bestellen':
        bestellteartikel.menge = (bestellteartikel.menge + 1)
    elif action == 'entfernen':
        bestellteartikel.menge = (bestellteartikel.menge - 1)

    bestellteartikel.save()

    if bestellteartikel.menge <= 0:
        bestellteartikel.delete()

    return JsonResponse("Artikel hinzugefügt", safe=False)
