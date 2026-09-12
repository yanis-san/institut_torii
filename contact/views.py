from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django_ratelimit.decorators import ratelimit

from marketing.notifications import notify_contact_received, notify_admin_new_prospect
from .forms import ProspectForm, COUNTRY_CODES


@ratelimit(key='ip', rate='5/m', method='POST', block=True)
def contact(request):
    """Formulaire de contact prospect."""
    if request.method == 'POST':
        form = ProspectForm(request.POST)
        if form.is_valid():
            prospect = form.save()
            # Send acknowledgment email
            notify_contact_received(prospect)
            # Notify admin
            notify_admin_new_prospect(prospect)
            messages.success(request, _('Votre message a été envoyé avec succès !'))
            return redirect('contact:success')
    else:
        form = ProspectForm()

    return render(request, 'contact/contact.html', {
        'form': form,
        'country_codes': COUNTRY_CODES,
    })


def contact_success(request):
    """Page de confirmation après envoi du formulaire."""
    return render(request, 'contact/success.html')
