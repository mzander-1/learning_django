from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse

from .models import *
import json
from django.contrib.auth import authenticate, login, logout
from .forms import EigeneUserCreationForm
import uuid
from django.utils.safestring import mark_safe
from django.contrib.auth.decorators import login_required
from paypal.standard.forms import PayPalPaymentsForm
from .viewstools import gastCookie, gastBestellung


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
        cookieDaten = gastCookie(request)
        artikels = cookieDaten['artikels']
        bestellung = cookieDaten['bestellung']

    ctx = {'artikels': artikels, "bestellung": bestellung}
    return render(request, "shop/warenkorb.html", ctx)


def kasse(request):
    if request.user.is_authenticated:
        kunde = request.user.kunde
        bestellung, created = Bestellung.objects.get_or_create(kunde=kunde, erledigt=False)
        artikels = bestellung.bestellteartikel_set.all()
    else:
        cookieDaten = gastCookie(request)
        artikels = cookieDaten['artikels']
        bestellung = cookieDaten['bestellung']

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
        messages.success(request, "Artikel wurde zum Warenkorb hinzugefügt.")
    elif action == 'entfernen':
        bestellteartikel.menge = (bestellteartikel.menge - 1)
        messages.warning(request, "Artikel wurde aus dem Warenkorb entfernt.")

    bestellteartikel.save()

    if bestellteartikel.menge <= 0:
        bestellteartikel.delete()

    return JsonResponse("Artikel hinzugefügt", safe=False)


def loginSeite(request):
    seite = 'login'
    if request.method == 'POST':
        benutzername = request.POST['benutzername']
        passwort = request.POST['passwort']

        benutzer = authenticate(request, username=benutzername, password=passwort)

        if benutzer is not None:
            login(request, benutzer)
            return redirect('shop')
        else:
            messages.error(request, "Benutzername oder Passwort nicht korrekt.")

    return render(request, 'shop/login.html', {'seite': seite})


def logoutBenutzer(request):
    logout(request)
    return redirect('shop')


def regBenutzer(request):
    seite = 'reg'
    form = EigeneUserCreationForm
    if request.method == 'POST':
        form = EigeneUserCreationForm(request.POST)
        if form.is_valid():
            benutzer = form.save(commit=False)
            benutzer.save()

            kunde = Kunde(name=request.POST['username'], benutzer=benutzer)
            kunde.save()
            bestellung = Bestellung(kunde=kunde)
            bestellung.save()

            login(request, benutzer)
            return redirect('shop')
        else:
            messages.error(request, "Fehlerhafte Eingabe!")

    ctx = {'form': form, 'seite': seite}
    return render(request, 'shop/login.html', ctx)


def bestellen(request):
    auftrags_id = uuid.uuid4()
    daten = json.loads(request.body)

    if request.user.is_authenticated:
        kunde = request.user.kunde
        bestellung, created = Bestellung.objects.get_or_create(kunde=kunde, erledigt=False)

    else:
        kunde, bestellung = gastBestellung(request, daten)

    gesamtpreis = float(daten['benutzerDaten']['gesamtpreis'])
    bestellung.auftrags_id = auftrags_id
    bestellung.erledigt = True
    bestellung.save()
    Adresse.objects.create(
        kunde=kunde,
        bestellung=bestellung,
        adresse=daten['lieferadresse']['adresse'],
        plz=daten['lieferadresse']['plz'],
        stadt=daten['lieferadresse']['stadt'],
        land=daten['lieferadresse']['land'],
        )

    paypal_dict = {
        "business": "sb-u435zc26619663@business.example.com",
        "amount": gesamtpreis,
        #"item_name": "name of the item",
        "invoice": auftrags_id,
        "currency_code": "EUR",
        "notify_url": request.build_absolute_uri(reverse('paypal-ipn')),
        "return": request.build_absolute_uri(reverse('shop')),
        "cancel_return": request.build_absolute_uri(reverse('shop')),
    }

    paypalform = PayPalPaymentsForm(initial=paypal_dict)
    auftrags_url = str(auftrags_id)
    messages.success(request, mark_safe(
        "Vielen Dank für Ihre <a href=' /bestellung/" + auftrags_url + "'>Bestellung: " + auftrags_url + "</a></br> Jetzt bezahlen: "+paypalform.render()))
    response = HttpResponse('Bestellung erfolgreich')
    response.delete_cookie('warenkorb')
    return response


@login_required(login_url='login')
def bestellung(request, id):
    bestellung = Bestellung.objects.get(auftrags_id=id)

    if bestellung and str(request.user) == str(bestellung.kunde):
        bestellung = Bestellung.objects.get(auftrags_id=id)
        artikels = bestellung.bestellteartikel_set.all()
        ctx = {'artikels': artikels, 'bestellung': bestellung}
        return render(request, 'shop/bestellung.html', ctx)
    else:
        return redirect('shop')

def fehler404(request, exception):
    return render(request, 'shop/404.html')
