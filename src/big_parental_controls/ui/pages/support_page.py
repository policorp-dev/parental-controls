"""Support page — links to help channels and reporting services (Art. 17, IX)."""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from big_parental_controls.utils.i18n import setup_i18n

_ = setup_i18n()

SUPPORT_LINKS = [
    {
        "title": "CVV 188",
        "subtitle": _("Centro de Valorização da Vida — apoio emocional gratuito"),
        "icon": "call-start-symbolic",
        "url": "https://www.cvv.org.br",
    },
    {
        "title": "SaferNet Brasil",
        "subtitle": _("Ajuda e denúncias sobre crimes e segurança na internet"),
        "icon": "security-high-symbolic",
        "url": "https://new.safernet.org.br",
    },
    {
        "title": _("Disque 100"),
        "subtitle": _("Relatar violações de direitos de crianças e adolescentes"),
        "icon": "dialog-warning-symbolic",
        "url": "https://www.gov.br/mdh/pt-br/acesso-a-informacao/disque-100",
    },
    {
        "title": "CERT.br",
        "subtitle": _("Guias de segurança e boas práticas na rede"),
        "icon": "network-server-symbolic",
        "url": "https://cartilha.cert.br",
    },
]

LEGAL_LINKS = [
    {
        "title": _("ECA Digital (Lei nº 15.211/2025)"),
        "subtitle": _("Dispõe sobre a obrigatoriedade de ferramentas de supervisão parental"),
        "icon": "document-properties-symbolic",
        "url": "https://www.planalto.gov.br/ccivil_03/leis/l8069.htm", # ECA Geral como referência principal
    },
    {
        "title": _("LGPD (Lei nº 13.709/2018)"),
        "subtitle": _("Proteção de dados pessoais de menores (Art. 14)"),
        "icon": "security-medium-symbolic",
        "url": "https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm",
    },
    {
        "title": _("Marco Civil (Lei nº 12.965/2014)"),
        "subtitle": _("Direitos e garantias dos usuários da rede no Brasil"),
        "icon": "network-workgroup-symbolic",
        "url": "https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2014/lei/l12965.htm",
    },
]


class SupportPage(Gtk.Box):
    """Page displaying support links and legal framework."""

    def __init__(self, **kwargs: object) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0, **kwargs)
        self._build_ui()

    def _build_ui(self) -> None:
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        clamp = Adw.Clamp()
        clamp.set_maximum_size(600)

        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        inner.set_margin_top(18)
        inner.set_margin_bottom(24)
        inner.set_margin_start(24)
        inner.set_margin_end(24)

        desc = Gtk.Label(
            label=_(
                "Trabalhamos para garantir uma experiência digital segura e saudável. "
                "Aqui você encontra canais de ajuda e a base legal de proteção."
            )
        )
        desc.set_wrap(True)
        desc.set_halign(Gtk.Align.START)
        desc.add_css_class("dim-label")
        inner.append(desc)

        # Main List
        group = Adw.PreferencesGroup()

        # Support Expander
        support_expander = Adw.ExpanderRow()
        support_expander.set_title(_("Canais de Ajuda e Apoio"))
        support_expander.set_subtitle(_("Suporte emocional, segurança e denúncias"))
        support_expander.set_icon_name("help-browser-symbolic")
        
        for link in SUPPORT_LINKS:
            row = Adw.ActionRow()
            row.set_title(link["title"])
            row.set_subtitle(link["subtitle"])
            row.set_activatable(True)
            row.connect("activated", self._on_link_activated, link["url"])

            icon = Gtk.Image(icon_name=link["icon"])
            row.add_prefix(icon)
            
            arrow = Gtk.Image(icon_name="go-next-symbolic")
            row.add_suffix(arrow)
            
            support_expander.add_row(row)
        
        group.add(support_expander)

        # Legal Expander
        legal_expander = Adw.ExpanderRow()
        legal_expander.set_title(_("Marco Legal e Proteção"))
        legal_expander.set_subtitle(_("Legislação brasileira sobre proteção de menores"))
        legal_expander.set_icon_name("emblem-system-symbolic")

        for link in LEGAL_LINKS:
            row = Adw.ActionRow()
            row.set_title(link["title"])
            row.set_subtitle(link["subtitle"])
            row.set_activatable(True)
            row.connect("activated", self._on_link_activated, link["url"])

            icon = Gtk.Image(icon_name=link["icon"])
            row.add_prefix(icon)
            
            arrow = Gtk.Image(icon_name="go-next-symbolic")
            row.add_suffix(arrow)
            
            legal_expander.add_row(row)

        group.add(legal_expander)

        inner.append(group)

        # Emergency info
        emergency_group = Adw.PreferencesGroup()
        emergency_group.set_title(_("Emergência"))

        emergency_row = Adw.ActionRow()
        emergency_row.set_title(_("Em perigo imediato, ligue 190 (Polícia) ou 192 (SAMU)"))
        emergency_row.set_subtitle(_("Números gratuitos disponíveis 24/7 em todo o Brasil"))

        emergency_icon = Gtk.Image(
            icon_name="emblem-important-symbolic",
            pixel_size=32,
        )
        emergency_row.add_prefix(emergency_icon)

        emergency_group.add(emergency_row)
        inner.append(emergency_group)

        clamp.set_child(inner)
        scrolled.set_child(clamp)
        self.append(scrolled)

    def _on_link_activated(self, _row: Adw.ActionRow, url: str) -> None:
        """Open a URL in the default browser."""
        launcher = Gtk.UriLauncher.new(url)
        launcher.launch(self.get_root(), None, None)

    def refresh(self) -> None:
        """No-op — support links are static."""
